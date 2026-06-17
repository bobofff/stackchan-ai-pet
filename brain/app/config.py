from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    pet_name: str = Field(default="小栈", alias="PET_NAME")
    user_name: str = Field(default="主人", alias="USER_NAME")
    memory_db_path: str = Field(default="brain/data/pet_memory.db", alias="MEMORY_DB_PATH")
    memory_top_k: int = Field(default=6, alias="MEMORY_TOP_K")
    log_dir_path: str = Field(default="brain/logs", alias="LOG_DIR_PATH")

    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")

    tts_enabled: bool = Field(default=False, alias="TTS_ENABLED")
    tts_provider: str = Field(default="macos_say", alias="TTS_PROVIDER")
    tts_voice: str = Field(default="", alias="TTS_VOICE")
    tts_rate: int = Field(default=180, alias="TTS_RATE")
    tts_sample_rate: int = Field(default=22050, alias="TTS_SAMPLE_RATE")
    tts_timeout_seconds: float = Field(default=20.0, alias="TTS_TIMEOUT_SECONDS")
    tts_audio_dir_path: str = Field(default="brain/data/tts", alias="TTS_AUDIO_DIR_PATH")
    tts_public_base_url: str = Field(default="", alias="TTS_PUBLIC_BASE_URL")

    device_shared_secret: str = Field(default="", alias="DEVICE_SHARED_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
