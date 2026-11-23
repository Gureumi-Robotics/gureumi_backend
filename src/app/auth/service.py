import asyncio
import hashlib
import secrets

import bcrypt
from psycopg import AsyncConnection
from psycopg.rows import DictRow

from app.auth.config import SESSION_IDLE_MINUTES

_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _check_password(password: str, password_hash: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash)
    except ValueError:
        return False


async def authenticate(
    conn: AsyncConnection[DictRow], username: str, password: str
) -> DictRow | None:
    cur = await conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = %s",
        (username,),
    )
    user = await cur.fetchone()

    password_hash = user["password_hash"].encode() if user else _DUMMY_HASH
    is_valid = await asyncio.to_thread(_check_password, password, password_hash)

    return user if user and is_valid else None


async def create_session(conn: AsyncConnection[DictRow], user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    await conn.execute(
        """
        INSERT INTO sessions (token_hash, user_id, expires_at)
        VALUES (%s, %s, now() + make_interval(mins => %s))
        ON CONFLICT (user_id) DO UPDATE
        SET token_hash = EXCLUDED.token_hash,
            expires_at = EXCLUDED.expires_at,
            created_at = now()
        """,
        (hash_token(token), user_id, SESSION_IDLE_MINUTES),
    )
    return token


async def get_user_by_session(
    conn: AsyncConnection[DictRow], token: str
) -> DictRow | None:
    cur = await conn.execute(
        """
        UPDATE sessions
        SET expires_at = now() + make_interval(mins => %s)
        FROM users
        WHERE sessions.token_hash = %s
          AND sessions.expires_at > now()
          AND users.id = sessions.user_id
        RETURNING users.id, users.username
        """,
        (SESSION_IDLE_MINUTES, hash_token(token)),
    )
    return await cur.fetchone()


async def delete_session(conn: AsyncConnection[DictRow], token: str) -> None:
    await conn.execute(
        "DELETE FROM sessions WHERE token_hash = %s", (hash_token(token),)
    )
