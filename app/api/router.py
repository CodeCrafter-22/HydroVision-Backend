"""Central API Router for HydroVision Backend.

Aggregates all API v1 endpoints under a unified router.
Teammates (such as Purvika for AI/Replay routes) can register their feature routers here.
"""

from fastapi import APIRouter
from app.api.v1 import health

api_router = APIRouter()

# Register core v1 routers
api_router.include_router(health.router, tags=["Health"])
