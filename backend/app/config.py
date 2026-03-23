from dotenv import load_dotenv
import os
from functools import lru_cache
from typing import List

# 🔥 LOAD .env
load_dotenv()


class Settings:
    DATABASE_URL: str = os.environ.get("DATABASE_URL")

    print("✅ DATABASE_URL =", DATABASE_URL)

    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY",
        "alumni-nexus-super-secret-key"
    )

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("TOKEN_EXPIRE_MINUTES", "1440")
    )

    APP_NAME: str = "Alumni Nexus"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

    _cors_raw: str = os.environ.get("CORS_ORIGINS", "*")

    @property
    def CORS_ORIGINS(self) -> List[str]:
        if self._cors_raw == "*":
            return ["*"]
        return [o.strip() for o in self._cors_raw.split(",") if o.strip()]

    DEFAULT_PAGE_SIZE: int = int(os.environ.get("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE: int = int(os.environ.get("MAX_PAGE_SIZE", "50"))

    MAX_RECOMMENDATIONS: int = int(os.environ.get("MAX_RECOMMENDATIONS", "10"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()