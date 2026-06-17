from fastapi import APIRouter, Depends, Header, HTTPException

from ..config import Settings, get_settings
from ..llm import generate_turn
from ..memory import MemoryStore, extract_explicit_memories
from ..models import HealthResponse, MemoryItem, TurnRequest, TurnResponse
from ..tts import synthesize_turn_audio

router = APIRouter()


def get_store(settings: Settings = Depends(get_settings)) -> MemoryStore:
    return MemoryStore(settings.memory_db_path)


def verify_device_secret(
    x_device_secret: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.device_shared_secret and x_device_secret != settings.device_shared_secret:
        raise HTTPException(status_code=401, detail="invalid device secret")


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        ok=True,
        pet_name=settings.pet_name,
        memory_path=settings.memory_db_path,
        llm_configured=bool(settings.llm_base_url and settings.llm_api_key),
    )


@router.post("/api/v1/turn", response_model=TurnResponse, dependencies=[Depends(verify_device_secret)])
async def turn(
    request: TurnRequest,
    settings: Settings = Depends(get_settings),
    store: MemoryStore = Depends(get_store),
) -> TurnResponse:
    explicit_memories = store.add_memories(extract_explicit_memories(request.user_text))
    recalled = store.search(request.user_text, settings.memory_top_k)
    response = await generate_turn(settings, request, recalled)
    response.saved_memories = explicit_memories + store.add_memories(response.saved_memories)
    response.audio_url = synthesize_turn_audio(settings, response.say)
    store.save_episode(request.device_id, request.user_text, response)
    return response


@router.post("/api/v1/memories", response_model=MemoryItem)
def add_memory(
    item: MemoryItem,
    store: MemoryStore = Depends(get_store),
    _: None = Depends(verify_device_secret),
) -> MemoryItem:
    return store.add_memory(item)


@router.get("/api/v1/memories/search", response_model=list[MemoryItem])
def search_memories(
    q: str,
    limit: int = 10,
    store: MemoryStore = Depends(get_store),
) -> list[MemoryItem]:
    return store.search(q, min(max(limit, 1), 50))


@router.get("/api/v1/episodes")
def recent_episodes(
    limit: int = 8,
    store: MemoryStore = Depends(get_store),
) -> list[dict[str, str]]:
    return store.recent_episodes(min(max(limit, 1), 50))
