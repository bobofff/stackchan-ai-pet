from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Settings
from .logging_config import get_app_logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_tts_audio_dir(settings: Settings) -> Path:
    path = Path(settings.tts_audio_dir_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def synthesize_turn_audio(settings: Settings, text: str) -> str | None:
    line = text.strip()
    if not settings.tts_enabled or not line:
        return None

    if settings.tts_provider != "macos_say":
        logger = get_app_logger(settings.log_dir_path)
        logger.warning("Unsupported TTS provider: %s", settings.tts_provider)
        return None

    if platform.system() != "Darwin":
        logger = get_app_logger(settings.log_dir_path)
        logger.warning("macos_say TTS is only available on macOS")
        return None

    say_path = shutil.which("say")
    afconvert_path = shutil.which("afconvert")
    if not say_path or not afconvert_path:
        logger = get_app_logger(settings.log_dir_path)
        logger.warning("TTS command missing. say=%s afconvert=%s", bool(say_path), bool(afconvert_path))
        return None

    audio_dir = resolve_tts_audio_dir(settings)
    audio_dir.mkdir(parents=True, exist_ok=True)
    file_name = _audio_file_name(settings, line)
    wav_path = audio_dir / file_name
    if wav_path.exists():
        return _public_audio_url(settings, file_name)

    try:
        with tempfile.TemporaryDirectory(prefix="stackchan-tts-", dir=audio_dir) as tmpdir:
            tmp_path = Path(tmpdir)
            text_path = tmp_path / "speech.txt"
            aiff_path = tmp_path / "speech.aiff"
            temp_wav_path = tmp_path / "speech.wav"
            text_path.write_text(line, encoding="utf-8")

            say_command = [say_path]
            if settings.tts_voice:
                say_command.extend(["-v", settings.tts_voice])
            if settings.tts_rate > 0:
                say_command.extend(["-r", str(settings.tts_rate)])
            say_command.extend(["-o", str(aiff_path), "-f", str(text_path)])

            subprocess.run(
                say_command,
                check=True,
                timeout=settings.tts_timeout_seconds,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                [
                    afconvert_path,
                    "-f",
                    "WAVE",
                    "-d",
                    f"LEI16@{settings.tts_sample_rate}",
                    str(aiff_path),
                    str(temp_wav_path),
                ],
                check=True,
                timeout=settings.tts_timeout_seconds,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            temp_wav_path.replace(wav_path)
    except (OSError, subprocess.SubprocessError) as exc:
        logger = get_app_logger(settings.log_dir_path)
        logger.exception("TTS synthesis failed: %s", type(exc).__name__)
        return None

    return _public_audio_url(settings, file_name)


def _audio_file_name(settings: Settings, text: str) -> str:
    key = "\0".join(
        [
            settings.tts_provider,
            settings.tts_voice,
            str(settings.tts_rate),
            str(settings.tts_sample_rate),
            text,
        ]
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return f"{digest}.wav"


def _public_audio_url(settings: Settings, file_name: str) -> str:
    base_url = settings.tts_public_base_url.strip().rstrip("/")
    if base_url:
        return f"{base_url}/audio/{file_name}"
    return f"/audio/{file_name}"
