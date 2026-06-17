from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass


FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class SpeakResult:
    attempted: bool
    played: bool
    reason: str = ""


class MacSaySpeaker:
    """Small wrapper around macOS `say` for local simulator speech."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        voice: str | None = None,
        rate: int | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.enabled = self._env_enabled() if enabled is None else enabled
        self.voice = voice if voice is not None else os.getenv("STACKCHAN_TTS_VOICE", "").strip()
        self.rate = rate if rate is not None else self._env_rate()
        self.timeout_seconds = timeout_seconds

    def speak(self, text: str) -> SpeakResult:
        line = text.strip()
        if not line:
            return SpeakResult(attempted=False, played=False, reason="empty text")

        if not self.enabled:
            return SpeakResult(attempted=False, played=False, reason="tts disabled")

        if platform.system() != "Darwin":
            return SpeakResult(attempted=False, played=False, reason="not macOS")

        say_path = shutil.which("say")
        if not say_path:
            return SpeakResult(attempted=True, played=False, reason="say command not found")

        command = [say_path]
        if self.voice:
            command.extend(["-v", self.voice])
        if self.rate is not None:
            command.extend(["-r", str(self.rate)])
        command.append(line)

        try:
            subprocess.run(command, check=True, timeout=self.timeout_seconds)
        except (OSError, subprocess.SubprocessError) as exc:
            return SpeakResult(attempted=True, played=False, reason=str(exc))

        return SpeakResult(attempted=True, played=True)

    @staticmethod
    def _env_enabled() -> bool:
        value = os.getenv("STACKCHAN_TTS", "1").strip().lower()
        return value not in FALSE_VALUES

    @staticmethod
    def _env_rate() -> int | None:
        value = os.getenv("STACKCHAN_TTS_RATE", "").strip()
        if not value:
            return None
        try:
            rate = int(value)
        except ValueError:
            return None
        return min(max(rate, 80), 360)
