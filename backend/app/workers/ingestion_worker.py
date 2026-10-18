
"""Background ingestion worker pipeline and failure callback handlers."""

import logging
from datetime import datetime, timezone
from typing import Any

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
    """Notify the WF-03 webhook when an ingestion job completely fails."""
    url = settings.WF03_CALLBACK_URL

    if not url:
        logger.warning(
            "WF03_CALLBACK_URL is not configured; skipping WF-03 callback."
        )
        return False

    payload = {
        "is_fallback": is_fallback,
        "status": "failed",
        "message": error_message[:250],
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload)

        if response.is_success:
            logger.info("Successfully delivered WF-03 failure callback.")
            return True

        logger.warning(
            "WF-03 callback returned non-2xx status: %s; response: %s",
            response.status_code,
            response.text[:300],
        )
    except Exception:
        logger.exception("Failed to deliver WF-03 failure callback.")

    return False


def _normalise_timestamp(value: Any) -> str:
    """Return a timezone-aware ISO timestamp or raise a clear error."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Provider returned an invalid timestamp.") from exc
    else:
        raise ValueError("Provider reading has no valid timestamp.")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Provider timestamp must include a timezone.")

    return parsed.isoformat()


def _is_duplicate_insert_error(exc: Exception) -> bool:
    """Recognise PostgreSQL unique-constraint violations."""
    message = str(exc).lower()
    return "23505" in message or "duplicate key" in message


async def run_ingestion_job(
    execution_id: str,
    request: IngestionTriggerRequest,
) -> dict[str, Any]:
    """Fetch provider data, persist readings, and record source health.

    FastAPI BackgroundTasks is an in-memory mechanism, not a durable queue.
    A server restart can interrupt or lose a running job.
    """
    logger.info(
        "Starting ingestion job [%s] for source %s (is_fallback=%s)",
        execution_id,
        request.active_source,
        request.is_fallback,
    )

    records_fetched = 0
    records_inserted = 0
    records_deduplicated = 0
    village_errors: list[dict[str, Any]] = []
    original_error: Exception | None = None
    status = "down"

    try:
        if request.active_source == "cwc_gauge":
            raise RuntimeError(
                "CWC ingestion is explicitly non-operational: provider endpoints "
                "and station mapping are not configured."
            )
        if request.active_source == "nasa_gpm":
            raise RuntimeError(
                "NASA GPM ingestion is explicitly deferred; the operational pipeline "
                "has not been implemented."
            )

        if request.active_source != "open_meteo":
            raise RuntimeError(
                f"Unsupported ingestion source: {request.active_source}"
            )

        client = get_supabase_client()

        villages_response = (
            client.table("villages")
            .select("id, code, name, geom")
            .execute()
        )
        villages = villages_response.data or []

        if not villages:
            village_errors.append(
                {"error": "No villages found in database."}
            )
        else:
            for village in villages:
                village_id = village.get("id")
                village_code = village.get("code")

                try:
                    coords = parse_ewkb_point(village.get("geom"))
                    if coords is None:
                        raise ValueError(
                            "Missing or unparseable village coordinates."
                        )

                    longitude, latitude = coords

                    readings = await fetch_open_meteo_flood(
                        latitude=latitude,
                        longitude=longitude,
                    )

                    records_fetched += len(readings)

                    if not readings:
                        village_errors.append(
                            {
                                "village_id": str(village_id),
                                "code": village_code,
                                "error": (
                                    "Provider returned no readings "
                                    "for this village."
                                ),
                            }
                        )
                        continue

                    for reading in readings:
                        observed_iso = _normalise_timestamp(
                            reading.get("observed_at")
                        )

                        discharge_value = reading.get("discharge_m3s")
                        if discharge_value is None:
                            raise ValueError(
                                "Provider reading has no discharge value."
                            )

                        try:
                            discharge = float(discharge_value)
                        except (TypeError, ValueError) as exc:
                            raise ValueError(
                                "Provider returned an invalid discharge value."
                            ) from exc

                        if discharge < 0:
                            raise ValueError(
                                "Provider returned a negative discharge value."
                            )

                        raw_payload = dict(reading.get("raw_payload") or {})
                        raw_payload.setdefault("provider", "open_meteo")
                        raw_payload.setdefault("model", "GloFAS")
                        raw_payload.setdefault(
                            "data_type",
                            "modelled_daily_river_discharge",
                        )

                        record = {
                            "village_id": str(village_id),
                            "source": "open_meteo",
                            "gauge_id": None,
                            "observed_at": observed_iso,
                            "level_m": None,
                            "discharge_m3s": discharge,
                            "quality": reading.get("quality", "unknown"),
                            "raw_payload": raw_payload,
                            "is_simulated": False,
                        }

                        # Fast path: avoid an insert when the reading exists.
                        # The unique database index remains the final safeguard
                        # if another worker inserts it at the same time.
                        existing_response = (
                            client.table("gauge_readings")
                            .select("id")
                            .eq("village_id", str(village_id))
                            .eq("source", "open_meteo")
                            .eq("observed_at", observed_iso)
                            .limit(1)
                            .execute()
                        )

                        if existing_response.data:
                            records_deduplicated += 1
                            continue

                        try:
                            client.table("gauge_readings").insert(
                                record
                            ).execute()
                            records_inserted += 1
                        except Exception as exc:
                            if _is_duplicate_insert_error(exc):
                                # Another worker inserted the same reading.
                                records_deduplicated += 1
                                continue
                            raise

                except Exception as exc:
                    logger.exception(
                        "Ingestion failed for village %s (%s)",
                        village_code,
                        village_id,
                    )
                    village_errors.append(
                        {
                            "village_id": str(village_id),
                            "code": village_code,
                            "error": str(exc)[:250],
                        }
                    )

        # Determine the outcome after processing all villages.
        successful_records = records_inserted + records_deduplicated

        if village_errors:
            if successful_records > 0:
                status = "degraded"
            else:
                # Invalid village coordinates are a data-quality problem,
                # not necessarily a provider outage.
                coordinate_only_errors = all(
                    "Missing or unparseable village coordinates."
                    in item.get("error", "")
                    for item in village_errors
                    if "error" in item
                ) and any("error" in item for item in village_errors)

                if coordinate_only_errors:
                    status = "degraded"
                else:
                    status = "down"
                    original_error = RuntimeError(
                        "Ingestion failed for all villages or no usable "
                        "readings were processed."
                    )

        elif records_fetched == 0:
            status = "degraded"
            village_errors.append(
                {"error": "Provider returned no readings."}
            )

        else:
            # Existing valid readings count as a successful no-op.
            status = "healthy"

    except Exception as exc:
        original_error = exc
        status = "down"
        logger.exception(
            "Ingestion job [%s] failed for source %s",
            execution_id,
            request.active_source,
        )

    # Record source health without masking the ingestion outcome.
    try:
        checked_at = datetime.now(timezone.utc).isoformat()

        health_record = {
            "source": request.active_source,
            "status": status,
            "last_checked_at": checked_at,
            "details": {
                "execution_id": execution_id,
                "records_fetched": records_fetched,
                "records_inserted": records_inserted,
                "records_deduplicated": records_deduplicated,
                "error": str(original_error)[:250] if original_error else None,
                "village_errors": village_errors,
            },
            "is_backup_active": request.is_fallback,
        }

        if status == "healthy":
            health_record["last_success_at"] = checked_at

        get_supabase_client().table("source_health").insert(
            health_record
        ).execute()

    except Exception:
        logger.exception(
            "Failed to append source_health record for job [%s]",
            execution_id,
        )

    # Notify WF-03 only for complete ingestion failures.
    # Partial village failures remain visible in source health and the result.
    if original_error is not None:
        await send_wf03_failure_callback(
            is_fallback=request.is_fallback,
            error_message=str(original_error)[:200],
        )

    return {
        "execution_id": execution_id,
        "source": request.active_source,
        "status": status,
        "records_fetched": records_fetched,
        "records_inserted": records_inserted,
        "records_deduplicated": records_deduplicated,
        "village_errors": village_errors,
        "error": str(original_error)[:250] if original_error else None,
    }
