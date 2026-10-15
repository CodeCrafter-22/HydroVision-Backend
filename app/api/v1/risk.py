
"""Preliminary rule-based flood risk assessment for HydroVision."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.core.supabase_client import get_supabase_client

router = APIRouter(prefix="/villages", tags=["Flood Risk"])

# DEMO thresholds only. Replace with locally validated thresholds
# before using this API for real flood-warning decisions.
HIGH_DISCHARGE_M3S = 10.0
MODERATE_DISCHARGE_M3S = 5.0
HIGH_RAINFALL_MM = 50.0
MODERATE_RAINFALL_MM = 25.0

STALE_AFTER_HOURS = 6


def parse_timestamp(value):
    """Parse an ISO timestamp and ensure it is timezone-aware."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError, AttributeError):
        return None


def reading_is_stale(observation, now):
    """Return True if the reading is missing its time or is too old."""
    if not observation:
        return True

    observed_at = parse_timestamp(observation.get("observed_at"))

    if observed_at is None:
        return True

    age_hours = (now - observed_at).total_seconds() / 3600

    # Future-dated observations should not be trusted either.
    return age_hours < 0 or age_hours > STALE_AFTER_HOURS


@router.get("/{village_code}/risk")
def assess_village_risk(village_code: str, request: Request):
    """Return a preliminary risk category from the latest available readings."""

    client = get_supabase_client()

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
            detail=f"Village '{village_code}' was not found.",
        )

    village = village_result.data[0]
    village_id = str(village["id"])

    gauge_result = (
        client.table("gauge_readings")
        .select("source, observed_at, level_m, discharge_m3s, quality, is_simulated")
        .eq("village_id", village_id)
        .order("observed_at", desc=True)
        .limit(1)
        .execute()
    )

    rain_result = (
        client.table("rain_readings")
        .select("observed_at, rain_mm, grid_id")
        .eq("village_id", village_id)
        .order("observed_at", desc=True)
        .limit(1)
        .execute()
    )

    gauge = gauge_result.data[0] if gauge_result.data else None
    rain = rain_result.data[0] if rain_result.data else None
    now = datetime.now(timezone.utc)

    warnings = []

    if gauge is None:
        warnings.append("No river-discharge reading is available.")
    elif reading_is_stale(gauge, now):
        warnings.append("The latest river-discharge reading is missing a valid timestamp or is stale.")

    if rain is None:
        warnings.append("No rainfall reading is available for this village.")
    elif reading_is_stale(rain, now):
        warnings.append("The latest rainfall reading is missing a valid timestamp or is stale.")

    # Calculate a preliminary category from available readings.
    # These are demonstration thresholds, not validated warning levels.
    signals = []

    discharge = gauge.get("discharge_m3s") if gauge else None
    rainfall = rain.get("rain_mm") if rain else None

    if discharge is not None:
        if float(discharge) >= HIGH_DISCHARGE_M3S:
            signals.append("high")
        elif float(discharge) >= MODERATE_DISCHARGE_M3S:
            signals.append("moderate")
        else:
            signals.append("low")

    if rainfall is not None:
        if float(rainfall) >= HIGH_RAINFALL_MM:
            signals.append("high")
        elif float(rainfall) >= MODERATE_RAINFALL_MM:
            signals.append("moderate")
        else:
            signals.append("low")

    if not signals:
        risk_level = "unknown"
        assessment_status = "insufficient_data"
    elif "high" in signals or signals.count("moderate") >= 2:
        risk_level = "high"
        assessment_status = "preliminary"
    elif "moderate" in signals:
        risk_level = "moderate"
        assessment_status = "preliminary"
    else:
        risk_level = "low"
        assessment_status = "preliminary"

    # Missing or stale observations mean the category needs extra caution.
    if warnings and assessment_status == "preliminary":
        assessment_status = "limited_data"

    return {
        "data": {
            "village_code": village["code"],
            "risk_level": risk_level,
            "assessment_status": assessment_status,
            "observations": {
                "river_discharge_m3s": discharge,
                "river_level_m": gauge.get("level_m") if gauge else None,
                "rainfall_mm": rainfall,
                "gauge_observed_at": gauge.get("observed_at") if gauge else None,
                "rain_observed_at": rain.get("observed_at") if rain else None,
                "gauge_source": gauge.get("source") if gauge else None,
                "gauge_quality": gauge.get("quality") if gauge else None,
                "gauge_is_simulated": gauge.get("is_simulated") if gauge else None,
            },
            "warnings": warnings,
            "thresholds_used": {
                "moderate_discharge_m3s": MODERATE_DISCHARGE_M3S,
                "high_discharge_m3s": HIGH_DISCHARGE_M3S,
                "moderate_rainfall_mm": MODERATE_RAINFALL_MM,
                "high_rainfall_mm": HIGH_RAINFALL_MM,
                "stale_after_hours": STALE_AFTER_HOURS,
            },
            "method": "rule_based_demo",
            "safety_note": (
                "This preliminary result is for development and demonstration "
                "only. It is not an official flood warning or a validated prediction."
            ),
        },
        "meta": {
            "request_id": getattr(request.state, "request_id", None),
            "generated_at": now.isoformat(),
        },
    }
