import json
import urllib.request

from tts import MacSaySpeaker


SERVER_URL = "http://127.0.0.1:8787/api/v1/turn"


def post_turn(text: str) -> dict:
    payload = {
        "device_id": "simulator",
        "user_text": text,
        "context": {"wake_reason": "keyboard", "touch": None, "extra": {"source": "simulator"}},
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        SERVER_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    speaker = MacSaySpeaker()
    print("Stack-chan simulator. Type 'exit' to quit.")
    while True:
        text = input("你: ").strip()
        if text in {"exit", "quit"}:
            break
        if not text:
            continue
        response = post_turn(text)
        print(f"宠物: {response['say']}")
        speech = speaker.speak(response["say"])
        if speech.attempted and not speech.played:
            print(f"语音: 未播放 ({speech.reason})")
        print(f"动作: {response['expression']} / {response['motion']} / {response['duration_ms']}ms")


if __name__ == "__main__":
    main()
