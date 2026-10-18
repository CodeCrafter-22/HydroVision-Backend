"""Health check router for HydroVision API."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request

from app.core.config import settings
from app.schemas.envelope import MetaInfo, ResponseEnvelope
from app.schemas.health import HealthData

router = APIRouter()


@router.get(
    "/health",
    response_model=ResponseEnvelope[HealthData],
    summary="Service Health Check",
    description="Returns current service status and metadata confirming the API is running.",
)
async def get_health(request: Request) -> ResponseEnvelope[HealthData]:
    """Return health status wrapped in the standard response envelope."""
    request_id = getattr(request.state, "request_id", f"req_{uuid.uuid4().hex[:12]}")
    return ResponseEnvelope[HealthData](
        data=HealthData(
            status="healthy",
            service=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.ENVIRONMENT,
            database="pending_phase_2",
        ),
        meta=MetaInfo(
            request_id=request_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        ),
    )
