
"""Village status endpoints for HydroVision."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.core.supabase_client import (
    execute_read_with_retry,
    get_supabase_client,
)

router = APIRouter(prefix="/villages", tags=["Villages"])


@router.get("")
def list_villages(request: Request):
    """Return village records stored in Supabase."""

    client = get_supabase_client()

    result = (
        client.table("villages")
        .select("*")
        .order("name")
        .limit(500)
        .execute()
    )

    villages = result.data or []

    return {
        "data": {
            "villages": villages,
            "total": len(villages),
        },
        "meta": {
            "request_id": getattr(request.state, "request_id", None),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


@router.get("/{village_code}/status")
def get_village_status(village_code: str, request: Request):
    """Return a village's latest readings and ingestion-source health."""

    client = get_supabase_client()

    # Find the village using its unique code, e.g. HV-TEST-001.
    village_result = execute_read_with_retry(
        client.table("villages")
        .select("*")
        .eq("code", village_code)
        .limit(1)
    )

    if not village_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Village '{village_code}' was not found.",
        )

    village = village_result.data[0]
    village_id = str(village["id"])

    # Fetch the most recent gauge/river-discharge observation.
    gauge_result = (
        client.table("gauge_readings")
        .select("*")
        .eq("village_id", village_id)
        .order("observed_at", desc=True)
        .limit(1)
        .execute()
    )

    # Fetch the most recent rainfall observation.
    rain_result = (
        client.table("rain_readings")
        .select("*")
        .eq("village_id", village_id)
        .order("observed_at", desc=True)
        .limit(1)
        .execute()
    )

    # Return the latest health entry for each ingestion source.
    health_result = (
        client.table("source_health")
        .select("*")
        .order("last_checked_at", desc=True)
        .limit(20)
        .execute()
    )

    # Keep the newest health entry per source.
    latest_health_by_source = {}
    for item in health_result.data or []:
        source = item.get("source")
        if source and source not in latest_health_by_source:
            latest_health_by_source[source] = item

    return {
        "data": {
            "village": village,
            "latest_gauge_reading": (
                gauge_result.data[0] if gauge_result.data else None
            ),
            "latest_rain_reading": (
                rain_result.data[0] if rain_result.data else None
            ),
            "source_health": list(latest_health_by_source.values()),
        },
        "meta": {
            "request_id": getattr(request.state, "request_id", None),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
