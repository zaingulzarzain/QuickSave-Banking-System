"""Application configuration — 12-factor, environment driven."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "QuickSave Banking System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # SQLite by default = zero-setup demo. Swap for Postgres in production:
    # postgresql+psycopg://user:password@host:5432/quicksave  (driver included)
    DATABASE_URL: str = "sqlite:///./quicksave.db"

    # --- Auth ---
    SECRET_KEY: str = "dev-secret-key-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h — convenient for demos

    # --- CORS ("*" for demos, comma-separated origins in prod) ---
    CORS_ORIGINS: str = "*"

    # --- Demo data ---
    SEED_DEMO_DATA: bool = True

    # --- AI / LLM (OpenAI-compatible, optional) ---
    # Leave OPENAI_API_KEY empty to use the built-in offline AI fallback.
    # OPENAI_BASE_URL can point at OpenAI, Azure OpenAI, Ollama, LM Studio, vLLM...
    AI_ENABLED: bool = True
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
