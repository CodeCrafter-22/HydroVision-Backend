
"""Protected ingestion endpoints for HydroVision data providers."""

import secrets
import uuid
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.core.supabase_client import get_supabase_client
from app.schemas.ingestion_trigger import IngestionTriggerRequest, TriggerResponse
from app.workers.ingestion_worker import run_ingestion_job

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion"])


async def verify_worker_token(
    x_worker_token: str | None = Header(default=None),
) -> None:
    """Authenticate trusted ingestion clients."""
    expected = settings.INGESTION_WORKER_TOKEN

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion authentication is not configured.",
        )

    if not x_worker_token or not secrets.compare_digest(
        x_worker_token, expected
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing worker token.",
        )


class IngestionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    village_id: UUID
    source: str = Field(min_length=1, max_length=100)
    observed_at: datetime
    quality: Literal["good", "suspect", "bad", "unknown"] = "unknown"
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone.")
        return value


class GaugeReading(IngestionBase):
    gauge_id: str = Field(min_length=1, max_length=100)
    level_m: float | None = Field(default=None, ge=0)
    discharge_m3s: float | None = Field(default=None, ge=0)


class RainReading(IngestionBase):
    rain_mm: float = Field(ge=0)
    accumulation_minutes: int | None = Field(default=None, gt=0)
    grid_id: str | None = Field(default=None, max_length=100)


class SourceHealthReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=100)
    status: Literal["healthy", "degraded", "down", "unknown"]
    last_success_at: datetime | None = None
    last_checked_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)
    is_backup_active: bool = False

    @field_validator("last_success_at", "last_checked_at")
    @classmethod
    def require_timezone_if_present(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Timestamps must include a timezone.")
        return value


def save_record(table: str, record: dict[str, Any]) -> dict[str, Any]:
    """Insert one validated record and handle database errors safely."""
    client = get_supabase_client()

    try:
        response = client.table(table).insert(record).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Database did not confirm the inserted record.",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception:
        # Keep database credentials and internal errors out of API responses.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not save data to {table}. Check server logs.",
        )


@router.post(
    "/gauge-readings",
    dependencies=[Depends(verify_worker_token)],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_gauge_reading(payload: GaugeReading) -> dict[str, Any]:
    record = payload.model_dump(mode="json")
    record["is_simulated"] = False
    return save_record("gauge_readings", record)


@router.post(
    "/rain-readings",
    dependencies=[Depends(verify_worker_token)],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_rain_reading(payload: RainReading) -> dict[str, Any]:
    record = payload.model_dump(mode="json")
    record["is_simulated"] = False
    return save_record("rain_readings", record)


@router.post(
    "/source-health",
    dependencies=[Depends(verify_worker_token)],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_source_health(
    payload: SourceHealthReading,
) -> dict[str, Any]:
    record = payload.model_dump(mode="json")
    return save_record("source_health", record)


@router.post(
    "/trigger",
    dependencies=[Depends(verify_worker_token)],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TriggerResponse,
    summary="Trigger Ingestion Workflow",
    description="Asynchronously queues an ingestion run for the specified source.",
)
async def trigger_ingestion(
    payload: IngestionTriggerRequest,
    background_tasks: BackgroundTasks,
) -> TriggerResponse:
    """Acknowledge ingestion job and queue background worker task."""
    execution_id = f"job_{uuid.uuid4().hex}"
    background_tasks.add_task(
        run_ingestion_job,
        execution_id=execution_id,
        request=payload,
    )
    return TriggerResponse(
        status="accepted",
        message=f"Ingestion job queued successfully for source: {payload.active_source}",
        execution_id=execution_id,
    )