from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "AI PR Intelligence Platform"
    debug: bool = False
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "codebase_memory"

    # ─── Multi-LLM Keys ──────────────────────────────────────────────────────
    groq_api_key: str                             # PRIMARY — required
    openai_api_key: Optional[str] = None          # optional consensus model
    google_api_key: Optional[str] = None          # optional consensus model

    # ─── GitHub ──────────────────────────────────────────────────────────────
    github_webhook_secret: str
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None

    # ─── Notifications ────────────────────────────────────────────────────────
    slack_bot_token: Optional[str] = None         # xoxb-...
    slack_channel_id: Optional[str] = None        # C0XXXXXXX
    discord_webhook_url: Optional[str] = None     # https://discord.com/api/webhooks/...

    # ─── AWS S3 (PDF reports) ─────────────────────────────────────────────────
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_s3_bucket: Optional[str] = None
    aws_region: str = "us-east-1"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
