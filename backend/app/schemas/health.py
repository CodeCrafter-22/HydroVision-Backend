"""Health check schema definition."""

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    """Payload returned by the health check endpoint."""

    status: str = Field(..., example="healthy", description="Current service health state")
    service: str = Field(..., example="HydroVision Backend API", description="Service name")
    version: str = Field(..., example="0.1.0", description="API version")
    environment: str = Field(..., example="development", description="Runtime environment")
    database: str = Field(
        default="pending_phase_2",
        example="pending_phase_2",
        description="Database connection status",
    )
