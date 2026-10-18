
"""Central API Router for HydroVision Backend."""

from fastapi import APIRouter

from app.api.v1 import (
    health,
    ingestion,
    villages,
    risk,
    alerts,
    dashboard,
    readings,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ingestion.router)
api_router.include_router(villages.router)
api_router.include_router(risk.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)
api_router.include_router(readings.router)