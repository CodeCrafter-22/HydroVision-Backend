
"""HydroVision historical gauge readings API."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.supabase_client import get_supabase_client


router = APIRouter(prefix="/readings", tags=["Readings"])


@router.get("/gauges")
def get_gauge_readings(
    request: Request,
    village_code: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    Retrieve historical gauge readings.

    Supports filtering by village and observation time,
    plus pagination using limit and offset.
    """

    if start_at and end_at and start_at > end_at:
        raise HTTPException(
            status_code=422,
            detail="start_at must be earlier than or equal to end_at.",
        )

    client = get_supabase_client()

    query = client.table("gauge_readings").select("*")

    # Optional village filter.
    if village_code:
        village_result = (
            client.table("villages")
            .select("id, code")
            .eq("code", village_code)
            .limit(1)
            .execute()
        )

        if not village_result.data:
            raise HTTPException(
                status_code=404,
                detail="Village not found.",
            )

        query = query.eq(
            "village_id",
            village_result.data[0]["id"],
        )

    # Optional observation-time filters.
    if start_at:
        query = query.gte(
            "observed_at",
            start_at.isoformat(),
        )

    if end_at:
        query = query.lte(
            "observed_at",
            end_at.isoformat(),
        )

    # Fetch one page of results, newest first.
    result = (
        query
        .order("observed_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    readings = result.data or []

    return {
        "data": readings,
        "meta": {
            "request_id": getattr(
                request.state,
                "request_id",
                None,
            ),
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "count": len(readings),
            "limit": limit,
            "offset": offset,
            "has_more": len(readings) == limit,
            "filters": {
                "village_code": village_code,
                "start_at": (
                    start_at.isoformat() if start_at else None
                ),
                "end_at": (
                    end_at.isoformat() if end_at else None
                ),
            },
        },
    }