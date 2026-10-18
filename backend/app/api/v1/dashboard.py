"""HydroVision dashboard summary API."""

import logging

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.core.supabase_client import (
    execute_read_with_retry,
    get_supabase_client,
)


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

logger = logging.getLogger(__name__)

def response_meta(request: Request) -> dict:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def calculate_risk(discharge_m3s) -> str:
    """Preliminary demo estimate, not an official flood forecast."""

    if discharge_m3s is None:
        return "unknown"

    try:
        discharge = float(discharge_m3s)
    except (TypeError, ValueError):
        return "unknown"

    if discharge >= 10:
        return "high"
    if discharge >= 5:
        return "moderate"
    return "low"


@router.get("/summary")
def get_dashboard_summary(request: Request):
    """Return a consolidated summary for the HydroVision dashboard."""

    client = get_supabase_client()

    try:
        # 1. Fetch villages
        villages_result = (
            client.table("villages")
            .select("id, code")
            .limit(1000)
            .execute()
        )
        villages = villages_result.data or []

        village_codes = {
            village["id"]: village["code"]
            for village in villages
        }

        # 2. Fetch recent gauge readings
        readings_result = (
            client.table("gauge_readings")
            .select("*")
            .order("observed_at", desc=True)
            .limit(1000)
            .execute()
        )
        readings = readings_result.data or []

        # Keep the newest reading for each village.
        latest_by_village = {}

        for reading in readings:
            village_id = reading.get("village_id")

            if village_id and village_id not in latest_by_village:
                latest_by_village[village_id] = reading

        latest_readings = []

        for village_id, reading in latest_by_village.items():
            latest_readings.append({
                "village_id": village_id,
                "village_code": village_codes.get(village_id),
                "source": reading.get("source"),
                "gauge_id": reading.get("gauge_id"),
                "observed_at": reading.get("observed_at"),
                "level_m": reading.get("level_m"),
                "discharge_m3s": reading.get("discharge_m3s"),
                "quality": reading.get("quality"),
                "is_simulated": reading.get("is_simulated", False),
                "risk_level": calculate_risk(
                    reading.get("discharge_m3s")
                ),
            })

        # 3. Calculate preliminary risk counts.
        risk_counts = {
            "low": 0,
            "moderate": 0,
            "high": 0,
            "unknown": 0,
        }

        for village in villages:
            reading = latest_by_village.get(village["id"])

            if not reading:
                risk_level = "unknown"
            else:
                risk_level = calculate_risk(
                    reading.get("discharge_m3s")
                )

            risk_counts[risk_level] += 1

        # 4. Fetch approved alerts only.
        alerts_result = (
            client.table("alerts")
            .select("*")
            .eq("status", "approved")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        alerts = alerts_result.data or []

        alert_status_counts = {}
        alert_tier_counts = {}

        for alert in alerts:
            status = alert.get("status") or "unknown"
            tier = alert.get("tier") or "unknown"

            alert_status_counts[status] = (
                alert_status_counts.get(status, 0) + 1
            )
            alert_tier_counts[tier] = (
                alert_tier_counts.get(tier, 0) + 1
            )

        recent_alerts = alerts[:10]

        # 5. Fetch data-source health.
        health_result = (
            client.table("source_health")
            .select("*")
            .order("last_checked_at", desc=True)
            .limit(500)
            .execute()
        )
        health_records = health_result.data or []

        # Keep only the latest health record per source.
        latest_health_by_source = {}

        for record in health_records:
            source = record.get("source")

            if source and source not in latest_health_by_source:
                latest_health_by_source[source] = record

        source_health = list(latest_health_by_source.values())

        # 6. Build the dashboard response.
        return {
            "data": {
                "overview": {
                    "total_villages": len(villages),
                    "villages_with_readings": len(latest_by_village),
                    "villages_without_readings": (
                        len(villages) - len(latest_by_village)
                    ),
                    "total_alerts": len(alerts),
                    "draft_alerts": alert_status_counts.get("draft", 0),
                    "approved_alerts": alert_status_counts.get(
                        "approved", 0
                    ),
                    "rejected_alerts": alert_status_counts.get(
                        "rejected", 0
                    ),
                },
                "risk_summary": risk_counts,
                "alert_status_counts": alert_status_counts,
                "alert_tier_counts": alert_tier_counts,
                "latest_readings": latest_readings[:50],
                "recent_alerts": recent_alerts,
                "source_health": source_health,
                "risk_method": {
                    "type": "preliminary_demo_estimate",
                    "description": (
                        "Risk categories are based on discharge thresholds "
                        "only. They are not validated flood predictions."
                    ),
                    "thresholds_m3s": {
                        "moderate": 5,
                        "high": 10,
                    },
                },
            },
            "meta": response_meta(request),
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Dashboard summary failed; request_id=%s",
            getattr(request.state, "request_id", None),
        )
        raise