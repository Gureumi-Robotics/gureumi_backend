# Gureumi Backend

로봇 상태신호를 수신하고 웹에 전달하기 위한 FastAPI 백엔드입니다.

## 프로젝트 구조

```text
gureumi_backend_new/
├── src/
│   └── app/
│       ├── auth/             # 로그인·로그아웃·세션
│       ├── robot/            # Jetson 신호 수신
│       ├── web/              # 웹에 로봇 상태 전달
│       ├── config.py         # 환경 변수와 공통 설정
│       ├── database.py       # DB 연결
│       └── main.py           # FastAPI 앱 생성
├── sql/
│   └── schema.sql            # 테이블 생성 SQL (DB 최초 실행 시 자동 적용)
├── scripts/
│   └── create_user.py        # 계정 생성 스크립트
├── tests/                    # pytest 테스트
├── docker-compose.yml        # 로컬 PostgreSQL
├── .env.example              # 환경 변수 견본
├── pyproject.toml            # 프로젝트 정보와 의존성 설정
├── uv.lock                   # 의존성 버전 잠금 파일
└── README.md
```

## 설치 및 실행

```bash
cp .env.example .env          # 최초 1회
docker compose up -d          # PostgreSQL 실행
uv sync --locked
uv run uvicorn app.main:app --app-dir src --reload
```

- 서버: http://localhost:8000
- API 문서(Swagger): http://localhost:8000/docs
- DB 최초 실행 시 `sql/schema.sql` 자동 적용
- `sql/schema.sql` 변경 시 `docker compose down -v && docker compose up -d`로 DB 재생성 (기존 데이터 삭제)

## 계정 생성

회원가입 기능 없으므로 스크립트로 계정 생성

```bash
PYTHONPATH=src uv run python scripts/create_user.py <아이디>
```

실행 후 비밀번호 입력 (화면에 표시되지 않음)

## 테스트

DB 실행 중인 상태에서 실행

```bash
uv run pytest
```
