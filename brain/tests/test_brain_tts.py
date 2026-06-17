import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRAIN_ROOT = PROJECT_ROOT / "brain"
if str(BRAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(BRAIN_ROOT))

from app.config import Settings
from app.tts import synthesize_turn_audio


class BrainTtsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _settings(self, **overrides):
        tmp_path = Path(self.tmpdir.name)
        values = {
            "TTS_ENABLED": True,
            "TTS_PROVIDER": "macos_say",
            "TTS_VOICE": "Tingting",
            "TTS_RATE": 180,
            "TTS_SAMPLE_RATE": 22050,
            "TTS_AUDIO_DIR_PATH": str(tmp_path / "tts"),
            "LOG_DIR_PATH": str(tmp_path / "logs"),
        }
        values.update(overrides)
        return Settings(**values)

    @patch("app.tts.platform.system", return_value="Darwin")
    @patch("app.tts.shutil.which")
    @patch("app.tts.subprocess.run")
    def test_synthesize_turn_audio_returns_cached_audio_url(self, run, which, _system):
        def which_command(command):
            return f"/usr/bin/{command}"

        def fake_run(command, **_kwargs):
            if command[0].endswith("say"):
                Path(command[command.index("-o") + 1]).write_bytes(b"aiff")
            if command[0].endswith("afconvert"):
                Path(command[-1]).write_bytes(b"wav")

        which.side_effect = which_command
        run.side_effect = fake_run
        settings = self._settings()

        first_url = synthesize_turn_audio(settings, "你好，小栈")
        second_url = synthesize_turn_audio(settings, "你好，小栈")

        self.assertEqual(first_url, second_url)
        self.assertTrue(first_url.startswith("/audio/"))
        self.assertTrue(first_url.endswith(".wav"))
        self.assertEqual(run.call_count, 2)
        audio_path = Path(settings.tts_audio_dir_path) / first_url.removeprefix("/audio/")
        self.assertEqual(audio_path.read_bytes(), b"wav")

    @patch("app.tts.subprocess.run")
    def test_synthesize_turn_audio_noops_when_disabled(self, run):
        result = synthesize_turn_audio(self._settings(TTS_ENABLED=False), "你好")

        self.assertIsNone(result)
        run.assert_not_called()

    @patch("app.tts.platform.system", return_value="Darwin")
    @patch("app.tts.shutil.which", return_value="/usr/bin/tool")
    @patch("app.tts.subprocess.run")
    def test_synthesize_turn_audio_uses_public_base_url(self, run, _which, _system):
        def fake_run(command, **_kwargs):
            if command[0].endswith("say") or "-o" in command:
                Path(command[command.index("-o") + 1]).write_bytes(b"aiff")
            else:
                Path(command[-1]).write_bytes(b"wav")

        run.side_effect = fake_run
        settings = self._settings(TTS_PUBLIC_BASE_URL="http://brain.local")

        result = synthesize_turn_audio(settings, "我在这儿")

        self.assertTrue(result.startswith("http://brain.local/audio/"))


if __name__ == "__main__":
    unittest.main()
