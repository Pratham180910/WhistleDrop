import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# Path resolution: find .env in backend directory or workspace root
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
ROOT_DIR = BACKEND_DIR.parent

# Attempt loading from backend/.env first, then root .env
if (BACKEND_DIR / ".env").is_file():
    load_dotenv(dotenv_path=BACKEND_DIR / ".env")
elif (ROOT_DIR / ".env").is_file():
    load_dotenv(dotenv_path=ROOT_DIR / ".env")
else:
    load_dotenv()


class Settings:
    """Application settings read from environment variables."""

    PROJECT_NAME: str = "WhistleDrop — Speak Without Being Seen"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database configuration read strictly from environment variable
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT & Authentication Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "whistledrop-dev-secret-key-change-in-prod")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    @property
    def sync_database_url(self) -> str:
        """Returns standard PostgreSQL URL compatible with SQLAlchemy.
        
        Fixes legacy 'postgres://' URLs (often provided by Supabase/Heroku)
        to 'postgresql://' as required by SQLAlchemy 2.0+.
        """
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    def is_database_configured(self) -> bool:
        """Checks if a non-empty DATABASE_URL is present."""
        return bool(self.DATABASE_URL.strip())

    def get_masked_database_url(self) -> str:
        """Returns the DATABASE_URL with password redacted for safe verification."""
        url = self.sync_database_url
        if not url:
            return "NOT_CONFIGURED"
        try:
            parsed = urlparse(url)
            netloc = ""
            if parsed.username:
                netloc += parsed.username
                if parsed.password:
                    netloc += ":****"
                netloc += "@"
            if parsed.hostname:
                netloc += parsed.hostname
            if parsed.port:
                netloc += f":{parsed.port}"
            return f"{parsed.scheme}://{netloc}{parsed.path}"
        except Exception:
            return "CONFIGURED (URL format unparseable)"


settings = Settings()
