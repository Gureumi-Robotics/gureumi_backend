import secrets

import bcrypt
import psycopg
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

PASSWORD = "test-password"


def run_sql(query: str, params: tuple = ()) -> tuple | None:
    with psycopg.connect(settings.DATABASE_URL.get_secret_value()) as conn:
        cur = conn.execute(query, params)
        return cur.fetchone() if cur.description else None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def username():
    name = f"test_{secrets.token_hex(4)}"
    password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
    run_sql(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (name, password_hash),
    )
    yield name
    run_sql("DELETE FROM users WHERE username = %s", (name,))


def new_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def login(client: AsyncClient, username: str, password: str = PASSWORD):
    return await client.post(
        "/auth/login", json={"username": username, "password": password}
    )


def set_session_expiry(username: str, interval: str) -> None:
    run_sql(
        """
        UPDATE sessions SET expires_at = now() + %s::interval
        FROM users WHERE users.id = sessions.user_id AND users.username = %s
        """,
        (interval, username),
    )


@pytest.mark.anyio
async def test_login_fails(username):
    async with new_client() as client:
        wrong_password = await login(client, username, "wrong")
        unknown_user = await login(client, "no_such_user", PASSWORD)
        empty_username = await login(client, "", PASSWORD)

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()
    assert empty_username.status_code == 422


@pytest.mark.anyio
async def test_login_me_logout(username):
    async with new_client() as client:
        assert (await client.get("/auth/me")).status_code == 401

        response = await login(client, username)
        assert response.status_code == 200
        assert response.json()["username"] == username
        assert "password_hash" not in response.json()
        assert "httponly" in response.headers["set-cookie"].lower()

        me = await client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["username"] == username

        assert (await client.post("/auth/logout")).status_code == 204
        assert (await client.get("/auth/me")).status_code == 401


@pytest.mark.anyio
async def test_logout_invalidates_copied_token(username):
    async with new_client() as client:
        await login(client, username)
        copied_token = client.cookies["session"]
        await client.post("/auth/logout")

    async with new_client() as other:
        other.cookies.set("session", copied_token)
        assert (await other.get("/auth/me")).status_code == 401


@pytest.mark.anyio
async def test_expired_session_is_logged_out(username):
    async with new_client() as client:
        await login(client, username)
        set_session_expiry(username, "-1 second")

        assert (await client.get("/auth/me")).status_code == 401


@pytest.mark.anyio
async def test_request_extends_session(username):
    async with new_client() as client:
        await login(client, username)
        set_session_expiry(username, "1 minute")

        await client.get("/auth/me")

    row = run_sql(
        """
        SELECT expires_at - now() > interval '29 minutes'
        FROM sessions JOIN users ON users.id = sessions.user_id
        WHERE users.username = %s
        """,
        (username,),
    )
    assert row == (True,)


@pytest.mark.anyio
async def test_new_login_ends_previous_session(username):
    async with new_client() as first, new_client() as second:
        await login(first, username)
        await login(second, username)

        assert (await first.get("/auth/me")).status_code == 401
        assert (await second.get("/auth/me")).status_code == 200
