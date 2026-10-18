"""Persistent Supabase queue runner for ingestion jobs."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.supabase_client import get_supabase_client
from app.schemas.ingestion_trigger import IngestionTriggerRequest
from app.workers.ingestion_worker import run_ingestion_job

logger = logging.getLogger("hydrovision.ingestion_queue")

POLL_INTERVAL_SECONDS = 2
MAX_ATTEMPTS = 3


def _claim_job() -> dict[str, Any] | None:
    """Atomically claim one available job from Supabase."""
    response = (
        get_supabase_client()
        .rpc("claim_ingestion_job")
        .execute()
    )
    jobs = response.data or []
    return jobs[0] if jobs else None


def _update_job(execution_id: str, values: dict[str, Any]) -> None:
    """Persist a job state transition."""
    values["updated_at"] = datetime.now(timezone.utc).isoformat()
    (
        get_supabase_client()
        .table("ingestion_jobs")
        .update(values)
        .eq("execution_id", execution_id)
        .execute()
    )


def _retry_time(attempts: int) -> str:
    """Apply exponential backoff before retrying."""
    delay_seconds = min(60, 2 ** attempts)
    return (
        datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
    ).isoformat()


async def _execute_job(job: dict[str, Any]) -> None:
    execution_id = job["execution_id"]
    attempts = int(job["attempts"])

    request = IngestionTriggerRequest(
        active_source=job["active_source"],
        is_fallback=job["is_fallback"],
        triggered_at=job["triggered_at"],
    )

    try:
        def run_sync() -> dict[str, Any]:
            return asyncio.run(run_ingestion_job(execution_id, request))

        result = await asyncio.to_thread(run_sync)

        result_status = result.get("status", "down")
        error_message = (
            result.get("error")
            or "; ".join(
                item.get("error", "Village ingestion error")
                for item in result.get("village_errors", [])
            )
            or "Ingestion did not complete successfully."
        )

        now = datetime.now(timezone.utc).isoformat()

        if result_status == "down":
            unsupported_sources = {"cwc_gauge", "nasa_gpm"}

            if job["active_source"] in unsupported_sources:
                _update_job(
                    execution_id,
                    {
                        "status": "failed",
                        "result": result,
                        "last_error": error_message[:2000],
                        "locked_at": None,
                        "finished_at": now,
                    },
                )
                logger.warning(
                    "Job %s failed because source %s is not operational. "
                    "Automatic retries skipped.",
                    execution_id,
                    job["active_source"],
                )

            elif attempts < MAX_ATTEMPTS:
                _update_job(
                    execution_id,
                    {
                        "status": "pending",
                        "result": result,
                        "last_error": error_message[:2000],
                        "locked_at": None,
                        "available_at": _retry_time(attempts),
                        "finished_at": None,
                    },
                )
                logger.warning(
                    "Job %s failed on attempt %s/%s; retry queued.",
                    execution_id,
                    attempts,
                    MAX_ATTEMPTS,
                )

            else:
                _update_job(
                    execution_id,
                    {
                        "status": "failed",
                        "result": result,
                        "last_error": error_message[:2000],
                        "locked_at": None,
                        "finished_at": now,
                    },
                )
                logger.error(
                    "Job %s exhausted all attempts.", execution_id
                )


        elif result_status == "degraded":
            _update_job(
                execution_id,
                {
                    "status": "degraded",
                    "result": result,
                    "last_error": error_message[:2000],
                    "locked_at": None,
                    "finished_at": now,
                },
            )

        else:
            _update_job(
                execution_id,
                {
                    "status": "succeeded",
                    "result": result,
                    "last_error": None,
                    "locked_at": None,
                    "finished_at": now,
                },
            )

    except Exception as exc:
        logger.exception("Queue processing failed for job %s", execution_id)

        now = datetime.now(timezone.utc).isoformat()
        if attempts < MAX_ATTEMPTS:
            _update_job(
                execution_id,
                {
                    "status": "pending",
                    "last_error": str(exc)[:2000],
                    "locked_at": None,
                    "available_at": _retry_time(attempts),
                    "finished_at": None,
                },
            )
        else:
            _update_job(
                execution_id,
                {
                    "status": "failed",
                    "last_error": str(exc)[:2000],
                    "locked_at": None,
                    "finished_at": now,
                },
            )


async def ingestion_queue_loop() -> None:
    """Continuously claim and process queued ingestion jobs."""
    logger.info("Persistent ingestion queue runner started.")

    while True:
        try:
            job = await asyncio.to_thread(_claim_job)

            if job is None:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            await _execute_job(job)

        except asyncio.CancelledError:
            logger.info("Ingestion queue runner stopping.")
            raise

        except Exception:
            logger.exception("Ingestion queue polling failed.")
            await asyncio.sleep(5)
