from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROBOT_SIGNAL_TIMEOUT_SECONDS = 5.0
STATUS_SEND_INTERVAL_SECONDS = 0.5


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: SecretStr
    COOKIE_SECURE: bool = False
    CORS_ORIGINS: list[str] = []


settings = Settings()  # pyright: ignore[reportCallIssue]
