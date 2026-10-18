"""Application configuration module using Pydantic Settings.

Reads settings from environment variables and an optional local '.env' file.
"""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for HydroVision Backend."""

    # Application settings
    APP_NAME: str = "HydroVision Backend"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    API_V1_PREFIX: str = "/api/v1"

    DEFAULT_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://hydrovision-frontend-l6qep861m-hydro-vision2.vercel.app",
    ]

    # CORS settings (allowed origins for frontend access)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://hydrovision-frontend-l6qep861m-hydro-vision2.vercel.app",
    ]

    # Supabase credentials (populated in local .env)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = ""

    # Simulation & safety guardrails
    ALLOW_SIM_DELIVERY: bool = False
    INGESTION_WORKER_TOKEN: str = ""

    # WF-03 n8n failure callback webhook URL
    WF03_CALLBACK_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Convert a comma-separated string or list into a deduplicated list of origins."""
        origins: List[str] = []
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    origins = json.loads(v)
                except Exception:
                    origins = [o.strip() for o in v.strip("[]").split(",") if o.strip()]
            else:
                origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple, set)):
            origins = [str(origin).strip() for origin in v if str(origin).strip()]

        # Ensure base production frontend and localhost defaults are always retained
        base_defaults = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://hydrovision-frontend-l6qep861m-hydro-vision2.vercel.app",
        ]
        combined = list(dict.fromkeys(base_defaults + origins))
        return combined



# Global singleton instance
settings = Settings()
