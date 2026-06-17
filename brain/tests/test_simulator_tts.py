import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulator.tts import MacSaySpeaker


class MacSaySpeakerTest(unittest.TestCase):
    @patch("simulator.tts.subprocess.run")
    @patch("simulator.tts.shutil.which", return_value="/usr/bin/say")
    @patch("simulator.tts.platform.system", return_value="Darwin")
    def test_speak_uses_macos_say(self, _system, _which, run):
        speaker = MacSaySpeaker(enabled=True, voice="Tingting", rate=180)

        result = speaker.speak("你好，小栈")

        self.assertTrue(result.attempted)
        self.assertTrue(result.played)
        run.assert_called_once_with(
            ["/usr/bin/say", "-v", "Tingting", "-r", "180", "你好，小栈"],
            check=True,
            timeout=30.0,
        )

    @patch("simulator.tts.shutil.which", return_value=None)
    @patch("simulator.tts.platform.system", return_value="Darwin")
    def test_speak_reports_missing_say(self, _system, _which):
        speaker = MacSaySpeaker(enabled=True)

        result = speaker.speak("你好")

        self.assertTrue(result.attempted)
        self.assertFalse(result.played)
        self.assertEqual(result.reason, "say command not found")

    @patch("simulator.tts.platform.system", return_value="Linux")
    def test_speak_noops_outside_macos(self, _system):
        speaker = MacSaySpeaker(enabled=True)

        result = speaker.speak("你好")

        self.assertFalse(result.attempted)
        self.assertFalse(result.played)
        self.assertEqual(result.reason, "not macOS")


if __name__ == "__main__":
    unittest.main()
