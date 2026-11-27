from collections.abc import AsyncIterator

import psycopg
from psycopg.rows import DictRow, dict_row

from app.config import settings


async def get_db() -> AsyncIterator[psycopg.AsyncConnection[DictRow]]:
    async with await psycopg.AsyncConnection[DictRow].connect(
        settings.DATABASE_URL.get_secret_value(),
        row_factory=dict_row,
        autocommit=True,
    ) as conn:
        yield conn
