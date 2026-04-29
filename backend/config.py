from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://virtuagym:virtuagym@localhost:5432/virtuagym"
    cors_origins: str = "http://localhost:5173"
    uploads_dir: str = "uploads"

    # Set Secure flag on the session cookie. Toggle on for HTTPS prod.
    cookie_secure: bool = False

    emails_enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_from: str = "Virtuagym <noreply@virtuagym.local>"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
