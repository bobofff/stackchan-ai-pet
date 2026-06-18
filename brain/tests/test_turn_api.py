import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRAIN_ROOT = PROJECT_ROOT / "brain"
if str(BRAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(BRAIN_ROOT))

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


class FailingAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, *args, **kwargs):
        raise RuntimeError("LLM unavailable during test")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class SuccessfulAsyncClient:
    payload = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, *args, **kwargs):
        return FakeResponse(self.payload)


class TurnApiCorePathsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        app.dependency_overrides.clear()
        self.addCleanup(app.dependency_overrides.clear)

    def _settings(self, **overrides):
        tmp_path = Path(self.tmpdir.name)
        values = {
            "MEMORY_DB_PATH": str(tmp_path / "memory.db"),
            "LOG_DIR_PATH": str(tmp_path / "logs"),
            "MEMORY_TOP_K": 3,
            "LLM_BASE_URL": "",
            "LLM_API_KEY": "",
            "DEVICE_SHARED_SECRET": "test-secret",
        }
        values.update(overrides)
        return Settings(**values)

    def _client(self, settings):
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    @staticmethod
    def _turn_payload(user_text, device_id="test-device"):
        return {
            "device_id": device_id,
            "user_text": user_text,
            "context": {
                "battery_percent": 88,
                "touch": "button_a",
                "face_detected": True,
                "wake_reason": "button",
                "extra": {"source": "test"},
            },
        }

    def test_turn_saves_explicit_memory_requires_secret_and_recalls_memory(self):
        settings = self._settings()
        headers = {"X-Device-Secret": "test-secret"}

        with self._client(settings) as client:
            rejected = client.post(
                "/api/v1/turn",
                json=self._turn_payload("你好"),
            )
            self.assertEqual(rejected.status_code, 401)
            self.assertEqual(rejected.json()["detail"], "invalid device secret")

            wrong_secret = client.post(
                "/api/v1/turn",
                json=self._turn_payload("你好"),
                headers={"X-Device-Secret": "wrong-secret"},
            )
            self.assertEqual(wrong_secret.status_code, 401)

            saved = client.post(
                "/api/v1/turn",
                json=self._turn_payload("请记住 我喜欢抹茶拿铁"),
                headers=headers,
            )
            self.assertEqual(saved.status_code, 200)
            saved_body = saved.json()
            self.assertEqual(saved_body["thought"], "local fallback response")
            self.assertEqual(saved_body["expression"], "happy")
            self.assertEqual(saved_body["motion"], "bounce")
            self.assertEqual(saved_body["saved_memories"][0]["key"], "user_explicit_memory")
            self.assertEqual(saved_body["saved_memories"][0]["value"], "我喜欢抹茶拿铁")
            self.assertEqual(saved_body["saved_memories"][0]["tags"], ["explicit", "user"])

            search = client.get("/api/v1/memories/search", params={"q": "抹茶", "limit": 5})
            self.assertEqual(search.status_code, 200)
            self.assertEqual(search.json()[0]["value"], "我喜欢抹茶拿铁")

            recalled = client.post(
                "/api/v1/turn",
                json=self._turn_payload("抹茶"),
                headers=headers,
            )
            self.assertEqual(recalled.status_code, 200)
            recalled_body = recalled.json()
            self.assertEqual(recalled_body["say"], "我记得这件事：我喜欢抹茶拿铁。")
            self.assertEqual(recalled_body["expression"], "curious")
            self.assertEqual(recalled_body["motion"], "nod")
            self.assertEqual(recalled_body["recalled_memories"][0]["value"], "我喜欢抹茶拿铁")

            episodes = client.get("/api/v1/episodes", params={"limit": 5})
            self.assertEqual(episodes.status_code, 200)
            self.assertEqual(episodes.json()[0]["user_text"], "抹茶")
            self.assertEqual(episodes.json()[1]["user_text"], "请记住 我喜欢抹茶拿铁")

    def test_turn_uses_local_fallback_when_configured_llm_fails(self):
        settings = self._settings(
            LLM_BASE_URL="https://llm.example.test",
            LLM_API_KEY="test-key",
            LLM_TIMEOUT_SECONDS=0.01,
        )
        headers = {"X-Device-Secret": "test-secret"}

        with patch("app.llm.httpx.AsyncClient", FailingAsyncClient):
            with self._client(settings) as client:
                response = client.post(
                    "/api/v1/turn",
                    json=self._turn_payload("这个问题怎么想？", device_id="llm-fallback-device"),
                    headers=headers,
                )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["say"], "我想想，这个可以慢慢拆开看。")
        self.assertEqual(body["expression"], "thinking")
        self.assertEqual(body["motion"], "look_up")
        self.assertTrue(body["thought"].startswith("LLM failed, used fallback: RuntimeError"))

    def test_turn_normalizes_llm_payload_before_validation(self):
        settings = self._settings(
            LLM_BASE_URL="https://llm.example.test",
            LLM_API_KEY="test-key",
        )
        headers = {"X-Device-Secret": "test-secret"}
        content = {
            "say": "我把这条记好了。",
            "expression": "excited",
            "motion": "spin",
            "duration_ms": 999999,
            "thought": 123,
            "saved_memories": [
                {
                    "key": "favorite_drink",
                    "value": "姜楠喜欢抹茶拿铁",
                    "tags": "preference",
                    "importance": 10,
                },
                {
                    "key": "",
                    "value": "姜楠最近在做 Stack-chan 桌宠",
                    "tags": [None, "project"],
                    "importance": -2,
                },
                {"key": "empty_value", "importance": 5},
                "not-a-memory",
            ],
        }
        SuccessfulAsyncClient.payload = {
            "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]
        }

        with patch("app.llm.httpx.AsyncClient", SuccessfulAsyncClient):
            with self._client(settings) as client:
                response = client.post(
                    "/api/v1/turn",
                    json=self._turn_payload("记一下我的饮料偏好", device_id="normalizing-device"),
                    headers=headers,
                )

                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["say"], "我把这条记好了。")
                self.assertEqual(body["expression"], "neutral")
                self.assertEqual(body["motion"], "idle")
                self.assertEqual(body["duration_ms"], 30000)
                self.assertEqual(body["thought"], "123")
                self.assertEqual(len(body["saved_memories"]), 2)
                self.assertEqual(body["saved_memories"][0]["key"], "favorite_drink")
                self.assertEqual(body["saved_memories"][0]["tags"], ["preference"])
                self.assertEqual(body["saved_memories"][0]["importance"], 5)
                self.assertEqual(body["saved_memories"][1]["key"], "llm_memory")
                self.assertEqual(body["saved_memories"][1]["tags"], ["project"])
                self.assertEqual(body["saved_memories"][1]["importance"], 1)

                search = client.get("/api/v1/memories/search", params={"q": "Stack-chan", "limit": 5})
                self.assertEqual(search.status_code, 200)
                self.assertEqual(search.json()[0]["value"], "姜楠最近在做 Stack-chan 桌宠")

    def test_turn_includes_tts_audio_url_when_synthesized(self):
        settings = self._settings(TTS_ENABLED=True)
        headers = {"X-Device-Secret": "test-secret"}

        with patch("app.routers.turns.synthesize_turn_audio", return_value="/audio/test.wav") as synthesize:
            with self._client(settings) as client:
                response = client.post(
                    "/api/v1/turn",
                    json=self._turn_payload("你好", device_id="tts-device"),
                    headers=headers,
                )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["audio_url"], "/audio/test.wav")
        synthesize.assert_called_once_with(settings, body["say"])

    def test_web_simulator_static_assets_are_served(self):
        settings = self._settings()

        with self._client(settings) as client:
            page = client.get("/simulator/")
            script = client.get("/simulator/app.js")

        self.assertEqual(page.status_code, 200)
        self.assertIn("Web 虚拟设备", page.text)
        self.assertIn("语音输出", page.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("submitTurn", script.text)
        self.assertIn("speechSynthesis", script.text)


if __name__ == "__main__":
    unittest.main()
