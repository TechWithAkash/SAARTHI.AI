"""
PostgreSQL connection pool using asyncpg.
Replaces mongodb.py — same connect/close/get_db interface.
"""
import asyncpg
from pathlib import Path
from typing import Optional

from backend.config import settings

_pool: Optional[asyncpg.Pool] = None
_SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


async def connect_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=30,
        max_inactive_connection_lifetime=300,  # recycle idle connections every 5 min
    )
    async with _pool.acquire() as conn:
        await conn.execute(_SCHEMA)
    print("[postgres] Connected and schema applied.")


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        print("[postgres] Pool closed.")


def get_db() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialised — call connect_db() first.")
    return _pool
