from fastapi import APIRouter, Depends, HTTPException, Response, status
from psycopg import AsyncConnection
from psycopg.rows import DictRow

from app.auth import service
from app.auth.config import SESSION_COOKIE_NAME
from app.auth.schemas import LoginRequest, UserResponse
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=UserResponse,
    responses={401: {"description": "아이디 또는 비밀번호 불일치"}},
)
async def login(
    body: LoginRequest,
    response: Response,
    conn: AsyncConnection[DictRow] = Depends(get_db),
):
    user = await service.authenticate(conn, body.username, body.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "아이디 또는 비밀번호가 맞지 않습니다."
        )

    token = await service.create_session(conn, user["id"])
    await conn.commit()

    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    return user
