from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Expression = Literal["neutral", "happy", "curious", "sleepy", "surprised", "sad", "thinking"]
Motion = Literal["idle", "nod", "shake", "look_left", "look_right", "look_up", "bounce", "sleep"]


class DeviceContext(BaseModel):
    battery_percent: int | None = Field(default=None, ge=0, le=100)
    touch: str | None = None
    face_detected: bool | None = None
    ambient_light: int | None = None
    wake_reason: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class TurnRequest(BaseModel):
    device_id: str = "dev-kit"
    user_text: str
    context: DeviceContext = Field(default_factory=DeviceContext)
    local_time: datetime | None = None


class MemoryItem(BaseModel):
    id: int | None = None
    key: str
    value: str
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(default=3, ge=1, le=5)


class TurnResponse(BaseModel):
    say: str
    expression: Expression = "neutral"
    motion: Motion = "idle"
    duration_ms: int = Field(default=3000, ge=500, le=30000)
    audio_url: str | None = None
    thought: str = ""
    saved_memories: list[MemoryItem] = Field(default_factory=list)
    recalled_memories: list[MemoryItem] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool
    pet_name: str
    memory_path: str
    llm_configured: bool
