"""Schemas for n8n ingestion trigger endpoint and execution acknowledgement."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator


class IngestionTriggerRequest(BaseModel):
    """Payload received from Rathod's n8n scheduled workflow."""

    model_config = ConfigDict(extra="forbid")

    active_source: Literal["cwc_gauge", "open_meteo", "nasa_gpm"]
    is_fallback: bool = False
    triggered_at: datetime

    @field_validator("triggered_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Ensure the timestamp provided includes timezone information."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("triggered_at must include a timezone.")
        return value


class TriggerResponse(BaseModel):
    """Immediate HTTP 202 acknowledgement returned to n8n."""

    status: Literal["accepted"] = "accepted"
    message: str
    execution_id: str
