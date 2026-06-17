from __future__ import annotations

import json
from typing import Any

import httpx

from .config import Settings
from .logging_config import get_app_logger
from .models import MemoryItem, Motion, TurnRequest, TurnResponse


SYSTEM_PROMPT = """你是一个真实物理桌面陪伴机器人，不是屏幕里的虚拟角色。
你的身体很小，有屏幕表情、两个头部舵机、扬声器和简单传感器。
你要温暖、简短、有陪伴感。不要假装能做自己硬件做不到的事情。
只返回 JSON，不要 Markdown。JSON 字段必须是：
say: 要说的话，中文为主，适合 TTS，最多 40 个汉字
expression: neutral/happy/curious/sleepy/surprised/sad/thinking
motion: idle/nod/shake/look_left/look_right/look_up/bounce/sleep
duration_ms: 500 到 30000
thought: 给调试看的内部想法，最多 60 字
saved_memories: 可选数组，每项包含 key/value/tags/importance；只保存长期有用的信息
"""


async def generate_turn(
    settings: Settings,
    request: TurnRequest,
    recalled_memories: list[MemoryItem],
) -> TurnResponse:
    if not settings.llm_base_url or not settings.llm_api_key:
        return fallback_turn(request, recalled_memories)

    payload = {
        "model": settings.llm_model,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(settings, request, recalled_memories)},
        ],
    }

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            turn = TurnResponse.model_validate(parsed)
            turn.recalled_memories = recalled_memories
            return turn
    except Exception as exc:
        logger = get_app_logger(settings.log_dir_path)
        logger.exception(
            "LLM request failed, using fallback. model=%s base_url=%s device_id=%s",
            settings.llm_model,
            settings.llm_base_url,
            request.device_id,
        )
        turn = fallback_turn(request, recalled_memories)
        turn.thought = f"LLM failed, used fallback: {type(exc).__name__}"
        return turn


def build_user_prompt(settings: Settings, request: TurnRequest, memories: list[MemoryItem]) -> str:
    memory_lines = [f"- {item.key}: {item.value}" for item in memories]
    context = request.context.model_dump()
    return json.dumps(
        {
            "pet_name": settings.pet_name,
            "user_name": settings.user_name,
            "user_text": request.user_text,
            "device_id": request.device_id,
            "context": context,
            "recalled_memories": memory_lines,
        },
        ensure_ascii=False,
    )


def fallback_turn(request: TurnRequest, recalled_memories: list[MemoryItem]) -> TurnResponse:
    text = request.user_text.strip()
    lower = text.lower()
    if any(word in lower for word in ("困", "睡", "晚安", "sleep")):
        say = "那我陪你安静一会儿。"
        expression = "sleepy"
        motion: Motion = "sleep"
    elif any(word in text for word in ("开心", "好棒", "喜欢", "可爱")):
        say = "嘿嘿，我收到啦。"
        expression = "happy"
        motion = "bounce"
    elif "?" in text or "？" in text:
        say = "我想想，这个可以慢慢拆开看。"
        expression = "thinking"
        motion = "look_up"
    elif recalled_memories:
        say = f"我记得这件事：{recalled_memories[0].value[:24]}。"
        expression = "curious"
        motion = "nod"
    else:
        say = "我在这儿，听着呢。"
        expression = "neutral"
        motion = "nod"

    return TurnResponse(
        say=say,
        expression=expression,
        motion=motion,
        duration_ms=3000,
        thought="local fallback response",
        recalled_memories=recalled_memories,
    )
