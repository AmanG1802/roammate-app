from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Roammate"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    DATABASE_URL: Optional[str] = None  # Railway injects this automatically
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "roammate"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            # Railway provides postgresql:// — asyncpg needs postgresql+asyncpg://
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    SECRET_KEY: str = "dev-secret-key-change-in-production"

    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Google Maps
    # GOOGLE_MAPS_MOCK=True forces MockGoogleMapsService everywhere; the real
    # API key is only used when GOOGLE_MAPS_MOCK is False.
    GOOGLE_MAPS_MOCK: bool = True
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    GOOGLE_MAPS_API_VERSION: str = "v1"   # "v1" (legacy) | "v2" (new)
    GOOGLE_MAPS_FETCH_PHOTOS: bool = True
    GOOGLE_MAPS_FETCH_RATING: bool = True
    GOOGLE_MAPS_USE_NEARBY_API: bool = False  # True = Nearby Search API, False = Text Search with locationBias

    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = "openai"       # "openai" | "claude" | "gemini"
    LLM_MODEL: str = "gpt-4o-mini"     # model name within the chosen provider

    # Per-operation output token caps. The chat path falls back to
    # BaseLLMModel.DEFAULT_MAX_TOKENS when no override is provided.
    LLM_MAX_TOKENS_EXTRACT: int = 3000
    LLM_MAX_TOKENS_PLAN: int = 4000

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "password@123"
    ADMIN_TOKEN_EXPIRE_HOURS: int = 4

    REDIS_URL: str = "redis://redis:6379/0"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
