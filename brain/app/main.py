from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers.turns import router as turns_router
from .tts import resolve_tts_audio_dir


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIMULATOR_WEB_DIR = PROJECT_ROOT / "simulator" / "web"
TTS_AUDIO_DIR = resolve_tts_audio_dir(get_settings())
TTS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Stack-chan AI Pet Brain",
    version="0.1.0",
    description="AI brain and memory service for a physical desktop companion robot.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(turns_router)
app.mount("/audio", StaticFiles(directory=TTS_AUDIO_DIR), name="audio")

if SIMULATOR_WEB_DIR.exists():
    app.mount("/simulator", StaticFiles(directory=SIMULATOR_WEB_DIR, html=True), name="simulator")
