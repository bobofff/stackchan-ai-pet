from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .migrations import apply_migrations
from .models import MemoryItem, TurnResponse


class MemoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        apply_migrations(self.db_path)

    def add_memory(self, item: MemoryItem) -> MemoryItem:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                insert into memories (key, value, tags, importance)
                values (?, ?, ?, ?)
                """,
                (item.key, item.value, json.dumps(item.tags, ensure_ascii=False), item.importance),
            )
            item.id = int(cursor.lastrowid)
        return item

    def add_memories(self, items: Iterable[MemoryItem]) -> list[MemoryItem]:
        return [self.add_memory(item) for item in items]

    def search(self, query: str, limit: int) -> list[MemoryItem]:
        tokens = [part.strip() for part in query.split() if part.strip()]
        if not tokens:
            tokens = [query.strip()] if query.strip() else []

        clauses = []
        params: list[str | int] = []
        for token in tokens[:4]:
            like = f"%{token}%"
            clauses.append("(key like ? or value like ? or tags like ?)")
            params.extend([like, like, like])

        where = " or ".join(clauses) if clauses else "1 = 1"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select id, key, value, tags, importance
                from memories
                where {where}
                order by importance desc, updated_at desc
                limit ?
                """,
                params,
            ).fetchall()

        return [self._row_to_memory(row) for row in rows]

    def save_episode(self, device_id: str, user_text: str, response: TurnResponse) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into episodes (device_id, user_text, assistant_text, expression, motion)
                values (?, ?, ?, ?, ?)
                """,
                (device_id, user_text, response.say, response.expression, response.motion),
            )

    def recent_episodes(self, limit: int = 8) -> list[dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select user_text, assistant_text, expression, motion, created_at
                from episodes
                order by id desc
                limit ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=row["id"],
            key=row["key"],
            value=row["value"],
            tags=json.loads(row["tags"] or "[]"),
            importance=row["importance"],
        )


def extract_explicit_memories(user_text: str) -> list[MemoryItem]:
    markers = ("记住", "请记住", "你要记住", "帮我记住")
    text = user_text.strip()
    for marker in markers:
        if text.startswith(marker):
            value = text.removeprefix(marker).strip(" ：:，,。")
            if value:
                return [
                    MemoryItem(
                        key="user_explicit_memory",
                        value=value,
                        tags=["explicit", "user"],
                        importance=5,
                    )
                ]
    return []
