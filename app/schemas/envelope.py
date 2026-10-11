"""Common response and error envelopes matching the Integration Contract."""

from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class MetaInfo(BaseModel):
    """Metadata included with every successful response."""

    request_id: str = Field(..., description="Unique request identifier for tracing")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp when the response was generated (ISO 8601)",
    )


class ResponseEnvelope(BaseModel, Generic[T]):
    """Standard success envelope wrapping response data."""

    data: T
    meta: MetaInfo


class ErrorDetail(BaseModel):
    """Detailed error object matching the Integration Contract."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of the error")
    request_id: str = Field(..., description="Request identifier for tracing")


class ErrorEnvelope(BaseModel):
    """Standard error envelope returned when a request fails."""

    error: ErrorDetail
