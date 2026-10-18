
"""Main entry point for the HydroVision Backend FastAPI application."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from app.workers.ingestion_queue import ingestion_queue_loop


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start the persistent ingestion queue runner."""
    queue_task = asyncio.create_task(ingestion_queue_loop())

    try:
        yield
    finally:
        queue_task.cancel()
        try:
            await queue_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "HydroVision Backend API — Flood detection, baseline risk scoring, "
        "and early-warning platform."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Ensure every HTTP request has a unique request_id for tracing."""
    request_id = request.headers.get(
        "X-Request-ID", f"req_{uuid.uuid4().hex[:12]}"
    )
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(
    RequestValidationError, validation_exception_handler
)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(health_router, tags=["Health"])
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
