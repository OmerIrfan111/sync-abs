import os
from decimal import Decimal
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "سync Dropshipping Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "dev_secret_key_change_in_production_9f834a81b2c"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "sync_db"
    DATABASE_URL: Optional[str] = None

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: Optional[str] = None

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_URL: Optional[str] = None

    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    CREDENTIAL_ENCRYPTION_KEY: str = "dGhpcy1pcy1hLTMyLWJ5dGUtc2VjcmV0LWtleS1mb3ItZGV2IQ=="

    FRONTEND_URL: Optional[str] = None

    FIRST_SUPERUSER_EMAIL: str = "admin@syncplatform.io"
    FIRST_SUPERUSER_PASSWORD: str = "adminpassword123"

    INGRAM_MICRO_CLIENT_ID: Optional[str] = None
    INGRAM_MICRO_CLIENT_SECRET: Optional[str] = None
    INGRAM_MICRO_CUSTOMER_NUMBER: Optional[str] = None
    INGRAM_MICRO_ENVIRONMENT: str = "production"

    # This business's own identity, required by Ingram Micro's real Order
    # Create v7 API as the "resellerInfo" object on every order (confirmed
    # against Ingram's official API reference). Never fabricated — if any of
    # these are missing, IngramMicroAdapter.submit_order() raises rather than
    # guessing or omitting the field.
    RESELLER_COMPANY_NAME: Optional[str] = None
    RESELLER_CONTACT_NAME: Optional[str] = None
    RESELLER_ADDRESS_LINE1: Optional[str] = None
    RESELLER_ADDRESS_LINE2: Optional[str] = None
    RESELLER_CITY: Optional[str] = None
    RESELLER_STATE: Optional[str] = None
    RESELLER_POSTAL_CODE: Optional[str] = None
    RESELLER_COUNTRY_CODE: str = "US"
    RESELLER_PHONE: Optional[str] = None
    RESELLER_EMAIL: Optional[str] = None

    DANDH_CLIENT_ID: Optional[str] = None
    DANDH_CLIENT_SECRET: Optional[str] = None
    DANDH_ACCOUNT_NUMBER: Optional[str] = "3302610000"
    DANDH_BEARER_TOKEN: Optional[str] = None
    DANDH_TENANT: str = "dhus"
    DANDH_ENVIRONMENT: str = "test"

    TDSYNNEX_CLIENT_ID: Optional[str] = None
    TDSYNNEX_CLIENT_SECRET: Optional[str] = None
    TDSYNNEX_ACCOUNT_NUMBER: Optional[str] = None
    TDSYNNEX_ENVIRONMENT: str = "production"

    WALMART_CLIENT_ID: Optional[str] = None
    WALMART_CLIENT_SECRET: Optional[str] = None
    WALMART_ENVIRONMENT: str = "production"

    # Ma Labs Web Service (MWS) — HTTP Basic Auth (account email + password),
    # confirmed from Ma Labs' own MWS reference and a real captured catalog
    # response. Catalog/stock/pricing only, no order-submission endpoint
    # documented. MALABS_PASSWORD not set yet — needs the real account
    # password from the user before MaLabsAdapter.is_live() returns True.
    MALABS_USERNAME: Optional[str] = None
    MALABS_PASSWORD: Optional[str] = None

    # Global Sandbox / Dry Run Flag (Feature 5)
    # Default is True in development/testing. Production requires explicit DRY_RUN=False.
    DRY_RUN: bool = True

    # Automatic fulfillment: route -> purchase order -> place with the supplier,
    # with no clicks, for new marketplace orders. Off by default in code so a
    # developer machine holding real credentials can never spend real money by
    # accident; production turns it on explicitly. Orders failing any check
    # are held for a person, never ordered.
    AUTO_ORDER_ENABLED: bool = False
    AUTO_ORDER_MAX_ORDER_VALUE: Decimal = Decimal("1000.00")   # supplier cost cap per order
    AUTO_ORDER_MIN_PROFIT: Decimal = Decimal("0.00")           # revenue - fees - supplier cost - shipping

    # UPC & Product Matching Configuration (Features 3 & 4)
    UPC_SIMILARITY_THRESHOLD: float = 0.60

    # Icecat manufacturer-verified product photos, looked up by exact GTIN or
    # Brand+MPN (no search quota). Free Open Icecat works with the shared
    # username below and covers sponsor brands; a full Icecat account
    # (set both values) widens coverage without any code change.
    ICECAT_USERNAME: Optional[str] = None
    ICECAT_PASSWORD: Optional[str] = None
    # Full Icecat "app_key" (My Profile page). Open Icecat refuses brands that
    # are not sponsors with HTTP 403 "an app_key is required"; those products
    # are recorded as requires_full_icecat and re-checked once this is set.
    ICECAT_APP_KEY: Optional[str] = None

    # Image Search Provider Configuration (Feature 4)
    # "bing" = free scraped Bing HTML, no key needed, but confirmed
    # (2026-10-10, live-tested: the identical query sent 3 times returned 3
    # different, unrelated results each time) to serve randomized decoy
    # content instead of real results for exactly the kind of narrow B2B SKU
    # query this app needs most — an anti-scraping countermeasure, not
    # something fixable by better queries. "bing_api" = the real, official
    # Bing Image Search API (Azure Cognitive Services) — same underlying
    # Bing index a real browser sees, no scraping, requires a real
    # subscription key (BING_IMAGE_SEARCH_API_KEY). Prefer "bing_api" once
    # a key is available.
    IMAGE_SEARCH_PROVIDER: str = "bing"  # "bing", "bing_api", "mock", "google"
    IMAGE_SEARCH_API_KEY: Optional[str] = None
    BING_IMAGE_SEARCH_API_KEY: Optional[str] = None
    BING_IMAGE_SEARCH_ENDPOINT: str = "https://api.bing.microsoft.com/v7.0/images/search"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    def get_redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    def get_cors_origins(self) -> list:
        """Production only accepts browser calls from its own frontend; any
        other environment stays open so local development keeps working."""
        if (self.ENVIRONMENT or "").lower() == "production" and self.FRONTEND_URL:
            return [self.FRONTEND_URL.rstrip("/")]
        return ["*"]

    def get_rabbitmq_url(self) -> str:
        # The Celery broker. Azure Container Apps run Celery on Redis and
        # supply it as CELERY_BROKER_URL, which this used to ignore, leaving
        # worker/beat pointed at a non-existent amqp://rabbitmq host.
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        if self.RABBITMQ_URL:
            return self.RABBITMQ_URL
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

_DEV_SECRET_KEY = "dev_secret_key_change_in_production_9f834a81b2c"
_DEV_ADMIN_PASSWORD = "adminpassword123"


def find_insecure_production_settings(s: "Settings") -> list:
    """Problems that must block a production (ENVIRONMENT=production) start:
    the repo-default token-signing key lets anyone forge a login, and the
    default admin password is public."""
    if (s.ENVIRONMENT or "").lower() != "production":
        return []
    problems = []
    if s.SECRET_KEY == _DEV_SECRET_KEY or len(s.SECRET_KEY) < 32:
        problems.append("SECRET_KEY is the dev default or too short (need 32+ random characters)")
    if s.FIRST_SUPERUSER_PASSWORD == _DEV_ADMIN_PASSWORD:
        problems.append("FIRST_SUPERUSER_PASSWORD is the public default")
    return problems


settings = Settings()
