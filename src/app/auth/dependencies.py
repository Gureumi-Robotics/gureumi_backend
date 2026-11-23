from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from psycopg import AsyncConnection
from psycopg.rows import DictRow

from app.auth import service
from app.auth.config import SESSION_COOKIE_NAME
from app.auth.schemas import UserResponse
from app.database import get_db


async def get_current_user(
    conn: AsyncConnection[DictRow] = Depends(get_db),
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> UserResponse:
    user = await service.get_user_by_session(conn, token) if token else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다.")

    return UserResponse.model_validate(user)
