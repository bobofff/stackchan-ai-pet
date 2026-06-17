from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .config import get_settings


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
MIGRATION_FILE_PATTERN = re.compile(r"^(\d{4})_.+\.sql$")


def apply_migrations(db_path: str | Path) -> list[str]:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    applied: list[str] = []
    with sqlite3.connect(path) as conn:
        current_version = _get_user_version(conn)
        for version, migration_path in _migration_files():
            if version <= current_version:
                continue
            sql = migration_path.read_text(encoding="utf-8")
            conn.executescript(
                f"""
                begin;
                {sql}
                pragma user_version = {version};
                commit;
                """
            )
            applied.append(migration_path.name)
            current_version = version

    return applied


def _get_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("pragma user_version").fetchone()
    return int(row[0])


def _migration_files() -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []
    for path in MIGRATIONS_DIR.glob("*.sql"):
        match = MIGRATION_FILE_PATTERN.match(path.name)
        if not match:
            continue
        migrations.append((int(match.group(1)), path))
    return sorted(migrations)


def main() -> None:
    settings = get_settings()
    applied = apply_migrations(settings.memory_db_path)
    if applied:
        print(f"数据库迁移完成：{settings.memory_db_path}")
        for name in applied:
            print(f"- {name}")
    else:
        print(f"数据库已是最新：{settings.memory_db_path}")


if __name__ == "__main__":
    main()
