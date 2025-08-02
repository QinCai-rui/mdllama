from collections.abc import Awaitable, Callable
from pathlib import Path

import aiosqlite


async def add_template_system_to_chat(db_path: Path) -> None:
    async with aiosqlite.connect(db_path) as connection:
        # Check if system column exists (it should already exist in new schema)
        cursor = await connection.execute("PRAGMA table_info(chat)")
        columns = await cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "system" not in column_names:
            await connection.execute("ALTER TABLE chat ADD COLUMN system TEXT")


upgrades: list[tuple[str, list[Callable[[Path], Awaitable[None]]]]] = [
    ("0.1.6", [add_template_system_to_chat])
]
