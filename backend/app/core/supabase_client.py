
"""Server-side Supabase client and safe read retries."""

import logging
import time
from functools import lru_cache

import httpx
from fastapi import HTTPException, status
from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Create and reuse the server-side Supabase client."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database configuration is incomplete.",
        )

    try:
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    except Exception:
        logger.exception("Supabase client initialization failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database client could not be initialized.",
        ) from None


def execute_read_with_retry(query, attempts: int = 3):
    """Retry a read query after temporary HTTP transport failures."""
    for attempt in range(attempts):
        try:
            return query.execute()
        except httpx.TransportError:
            if attempt == attempts - 1:
                logger.exception(
                    "Supabase read failed after %s attempts.",
                    attempts,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database temporarily unavailable. Please retry.",
                ) from None

            delay = 0.25 * (2 ** attempt)
            logger.warning(
                "Temporary Supabase transport failure; retry %s/%s in %.2fs.",
                attempt + 1,
                attempts - 1,
                delay,
            )
            time.sleep(delay)

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database temporarily unavailable. Please retry.",
    )
