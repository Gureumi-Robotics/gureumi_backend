"""테스트·운영 계정 생성 (회원가입 없음, 관리자가 직접 생성)

사용법: PYTHONPATH=src uv run python scripts/create_user.py <아이디>
"""

import sys
from getpass import getpass

import bcrypt
import psycopg

from app.config import settings


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("사용법: PYTHONPATH=src uv run python scripts/create_user.py <아이디>")

    username = sys.argv[1]
    password = getpass("비밀번호: ")
    if not password:
        sys.exit("비밀번호를 입력해 주세요.")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        with psycopg.connect(settings.DATABASE_URL.get_secret_value()) as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
    except psycopg.errors.UniqueViolation:
        sys.exit(f"이미 있는 아이디예요: {username}")

    print(f"계정을 만들었어요: {username}")


if __name__ == "__main__":
    main()
