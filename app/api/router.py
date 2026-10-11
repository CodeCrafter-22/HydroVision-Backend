
"""Central API Router for HydroVision Backend."""

from fastapi import APIRouter
from app.api.v1 import health, ingestion

api_router = APIRouter()

# Core API v1 routes
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(ingestion.router)