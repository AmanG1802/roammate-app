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

    # ── Auth (access + refresh tokens, cookies) ──────────────────────────────
    ACCESS_TOKEN_TTL_MIN: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30
    COOKIE_DOMAIN: Optional[str] = None              # ".roammate.xyz" in prod, None locally
    COOKIE_SECURE: bool = False                       # True in prod (HTTPS-only)
    PUBLIC_WEB_URL: str = "http://localhost:3000"     # used to build verify/reset links

    # ── Transactional email (Resend) ─────────────────────────────────────────
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "Roammate <auth@roammate.xyz>"

    # ── OAuth providers ──────────────────────────────────────────────────────
    GOOGLE_OAUTH_CLIENT_ID_WEB: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_ID_IOS: Optional[str] = None
    APPLE_SIGNIN_BUNDLE_ID: Optional[str] = None      # e.g. app.roammate.ios
    APPLE_SIGNIN_SERVICE_ID: Optional[str] = None     # e.g. app.roammate.web
    APPLE_SIGNIN_TEAM_ID: Optional[str] = None
    # Key used to sign SIWA client-secret JWTs (token exchange + revocation).
    # Create at: Apple Developer → Keys → + → Sign in with Apple.
    APPLE_SIGNIN_KEY_ID: Optional[str] = None
    APPLE_SIGNIN_PRIVATE_KEY_PATH: Optional[str] = None  # path to .p8 file

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
    # When True, Place Details enrichment also requests regularOpeningHours and
    # stores it on place-bearing rows (Brainstorm / Idea Bin / Timeline). Drives
    # the Concierge + Ripple opening/closing-hours feasibility warnings. Off ⇒ no
    # hours enrichment and no hours logic anywhere.
    GOOGLE_MAPS_FETCH_OPENING_HOURS: bool = True
    GOOGLE_MAPS_USE_NEARBY_API: bool = False  # True = Nearby Search API, False = Text Search with locationBias

    # Apple Maps Server API (used for iOS enrichment when enabled)
    APPLE_MAPS_ENABLED: bool = False
    APPLE_MAPS_TEAM_ID: Optional[str] = None
    APPLE_MAPS_KEY_ID: Optional[str] = None
    APPLE_MAPS_PRIVATE_KEY_PATH: Optional[str] = None  # path to .p8 file

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

    # ── DB connection pool (per-process) ─────────────────────────────────────
    # Sizing formula for horizontal scaling:
    #   replicas × workers × (DB_POOL_SIZE + DB_MAX_OVERFLOW) ≤ 0.7 × pg_max_conn
    # Single replica today; tune DB_POOL_SIZE down (or add PgBouncer) before
    # scaling past a few replicas on Railway.
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 10        # seconds to wait for a free connection
    DB_POOL_RECYCLE: int = 1800      # recycle connections every 30 min

    # ── LLM safety ───────────────────────────────────────────────────────────
    # Hard ceiling on a single provider call so a black-holed TCP connection
    # can't pin a worker until OS keep-alive fires (~10 min).
    LLM_TIMEOUT_S: int = 60

    # ── Subscription / billing ───────────────────────────────────────────────
    # Razorpay (India web/Android)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    RAZORPAY_PLAN_ID_MONTHLY: Optional[str] = None  # e.g. plan_NXXXXXXXXXXXX

    # Apple IAP (iOS) — bundle + product IDs must be supplied via environment
    # (no hardcoded defaults; values come from .env / Railway / docker-compose).
    APPLE_BUNDLE_ID: Optional[str] = None
    APPLE_IAP_PRODUCT_ID_MONTHLY: Optional[str] = None
    APPLE_IAP_PRODUCT_ID_ONETIME: Optional[str] = None
    APPLE_ISSUER_ID: Optional[str] = None
    APPLE_KEY_ID: Optional[str] = None
    APPLE_PRIVATE_KEY_PATH: Optional[str] = None  # .p8 file for App Store Server API
    APPLE_PRIVATE_KEY_B64: Optional[str] = None   # base64-encoded .p8 (Railway / env alternative)
    # Apple Root CA (G3) for verifying JWS/JWE signatures from StoreKit + SSN V2.
    # Download once from https://www.apple.com/certificateauthority/AppleRootCA-G3.cer
    APPLE_ROOT_CA_PATH: Optional[str] = None
    APPLE_ROOT_CA_B64: Optional[str] = None        # base64-encoded DER cert (Railway / env alternative)
    APPLE_USE_SANDBOX: bool = True
    # Dedicated key for signing Subscription Promotional Offers (separate from API key)
    APPLE_PROMO_OFFER_KEY_ID: Optional[str] = None
    APPLE_PROMO_OFFER_P8_KEY: Optional[str] = None  # PEM text with \n escapes

    # Roammate Plus tier limits (free-tier caps; Plus is unlimited)
    FREE_ACTIVE_TRIPS_CAP: int = 2
    FREE_BRAINSTORM_MONTHLY_CAP: int = 15
    PLUS_MONTHLY_PRICE_INR: int = 149
    PLUS_ONETIME_PRICE_INR: int = 200
    PLUS_ONETIME_DURATION_DAYS: int = 30

    # ── API spec validation (dev/staging only) ───────────────────────────────
    # Set VALIDATE_SPEC=true to validate all incoming requests against docs/api/openapi.yaml.
    # Never enable in production — adds latency.
    VALIDATE_SPEC: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
