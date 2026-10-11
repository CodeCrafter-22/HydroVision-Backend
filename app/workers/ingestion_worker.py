"""Background ingestion worker pipeline and failure callback handlers."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
import httpx

from app.core.config import settings
from app.core.supabase_client import get_supabase_client
from app.schemas.ingestion_trigger import IngestionTriggerRequest
from app.workers.adapters.open_meteo import fetch_open_meteo_flood
from app.workers.geo_utils import parse_ewkb_point

logger = logging.getLogger("hydrovision.ingestion")


async def send_wf03_failure_callback(
    is_fallback: bool,
    error_message: str,
) -> bool:
    """Send a failure notification callback to Rathod's n8n WF-03 webhook.

    Preserves is_fallback as received in the trigger request.
    Handles timeouts and missing configuration safely without crashing.
    """
    url = settings.WF03_CALLBACK_URL
    if not url:
        logger.warning(
            "WF03_CALLBACK_URL is not configured; skipping WF-03 failure callback."
        )
        return False

    payload = {
        "is_fallback": is_fallback,
        "status": "failed",
        "message": error_message[:250],  # sanitized and bounded
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.is_success:
                logger.info("Successfully delivered WF-03 failure callback to %s", url)
                return True
            logger.warning("WF-03 callback returned non-2xx status: %s", resp.status_code)
            return False
    except Exception as exc:
        logger.warning("Failed to deliver WF-03 failure callback: %s", exc)
        return False


async def run_ingestion_job(
    execution_id: str,
    request: IngestionTriggerRequest,
) -> Dict[str, Any]:
    """Execute the asynchronous background ingestion pipeline.

    Architecture Note:
    This function runs via FastAPI's in-memory BackgroundTasks.
    It is a lightweight development execution mechanism and is NOT a durable
    queue (such as Celery/Redis). If the server restarts during execution,
    the job is dropped.
    """
    logger.info(
        "Starting ingestion job [%s] for source: %s (is_fallback=%s)",
        execution_id,
        request.active_source,
        request.is_fallback,
    )

    records_fetched = 0
    records_inserted = 0
    records_deduplicated = 0
    village_errors: List[Dict[str, Any]] = []
    original_error: Exception | None = None
    status = "healthy"

    try:
        # 1. Source routing
        if request.active_source == "cwc_gauge":
            raise RuntimeError(
                "Provider 'cwc_gauge' is explicitly non-operational: "
                "official live endpoints and station mapping are not configured."
            )
        elif request.active_source == "nasa_gpm":
            raise RuntimeError(
                "Provider 'nasa_gpm' is explicitly deferred: "
                "operational real-time pipeline is not yet implemented."
            )
        elif request.active_source == "open_meteo":
            # 2. Fetch target villages from database
            client = get_supabase_client()
            villages_resp = (
                client.table("villages").select("id, code, name, geom").execute()
            )
            villages = villages_resp.data or []

            if not villages:
                status = "degraded"
                village_errors.append({"error": "No villages found in database."})
            else:
                for v in villages:
                    v_id = v.get("id")
                    geom_raw = v.get("geom")
                    coords = parse_ewkb_point(geom_raw)

                    if coords is None:
                        village_errors.append(
                            {
                                "village_id": str(v_id),
                                "code": v.get("code"),
                                "error": "Missing or unparseable coordinates in geom",
                            }
                        )
                        continue

                    lon, lat = coords
                    # Fetch from Open-Meteo Flood adapter
                    readings = await fetch_open_meteo_flood(latitude=lat, longitude=lon)
                    records_fetched += len(readings)

                    for r in readings:
                        obs_dt = r["observed_at"]
                        obs_iso = (
                            obs_dt.isoformat()
                            if hasattr(obs_dt, "isoformat")
                            else str(obs_dt)
                        )

                        # Deduplication check: query existing record
                        existing = (
                            client.table("gauge_readings")
                            .select("id")
                            .eq("village_id", str(v_id))
                            .eq("source", "open_meteo")
                            .eq("observed_at", obs_iso)
                            .execute()
                        )

                        if existing.data:
                            records_deduplicated += 1
                        else:
                            # Insert novel reading
                            record = {
                                "village_id": str(v_id),
                                "source": "open_meteo",
                                "gauge_id": None,
                                "observed_at": obs_iso,
                                "level_m": None,
                                "discharge_m3s": r.get("discharge_m3s"),
                                "quality": r.get("quality", "unknown"),
                                "raw_payload": r.get("raw_payload", {}),
                                "is_simulated": False,
                            }
                            client.table("gauge_readings").insert(record).execute()
                            records_inserted += 1

                # Classify run outcome
                if records_fetched == 0:
                    status = "degraded"  # No usable data returned
                elif village_errors:
                    status = "degraded"  # Partial success
                else:
                    status = "healthy"  # Full success

    except Exception as exc:
        original_error = exc
        status = "down"
        logger.error(
            "Ingestion job [%s] failed for %s: %s",
            execution_id,
            request.active_source,
            exc,
        )

    # 3. Isolated append-only source_health logging
    try:
        health_client = get_supabase_client()
        health_record = {
            "source": request.active_source,
            "status": status,
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "details": {
                "execution_id": execution_id,
                "records_fetched": records_fetched,
                "records_inserted": records_inserted,
                "records_deduplicated": records_deduplicated,
                "error": str(original_error) if original_error else None,
                "village_errors": village_errors,
            },
            "is_backup_active": request.is_fallback,
        }
        if status == "healthy":
            health_record["last_success_at"] = datetime.now(timezone.utc).isoformat()

        health_client.table("source_health").insert(health_record).execute()
    except Exception as health_exc:
        # Crucial invariant: never let health logging failure hide original ingestion failure
        logger.error(
            "Failed to append source_health audit record for [%s]: %s",
            execution_id,
            health_exc,
        )

    # 4. Trigger WF-03 callback if job failed
    if original_error is not None:
        sanitized_msg = str(original_error)[:200]
        await send_wf03_failure_callback(
            is_fallback=request.is_fallback,
            error_message=sanitized_msg,
        )

    return {
        "execution_id": execution_id,
        "source": request.active_source,
        "status": status,
        "records_fetched": records_fetched,
        "records_inserted": records_inserted,
        "records_deduplicated": records_deduplicated,
        "village_errors": village_errors,
        "error": str(original_error) if original_error else None,
    }
