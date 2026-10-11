"""Open-Meteo Flood API adapter for modelled river discharge."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

OPEN_METEO_FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"


async def fetch_open_meteo_flood(
    latitude: float,
    longitude: float,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """Fetch daily modelled river discharge from Open-Meteo Flood API.

    Semantics:
    - GloFAS hydrological model output (m³/s).
    - level_m is None (GloFAS does not measure physical river stage in meters).
    - gauge_id is None (GloFAS does not correspond to a physical sensor station).
    - quality is 'unknown' or 'good' (strictly conforming to schema Literal).
    - raw_payload stores original provider payload with GloFAS metadata.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "river_discharge",
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close = True

    try:
        response = await client.get(OPEN_METEO_FLOOD_URL, params=params)
        response.raise_for_status()
        data = response.json()
    finally:
        if should_close:
            await client.aclose()

    daily = data.get("daily", {})
    times = daily.get("time", [])
    discharges = daily.get("river_discharge", [])

    if not times or not discharges:
        return []

    readings: List[Dict[str, Any]] = []
    # Extract available daily modelled reading
    for time_str, discharge_val in zip(times[:1], discharges[:1]):
        if discharge_val is None:
            continue
        try:
            val = float(discharge_val)
            if val < 0:
                continue
        except (ValueError, TypeError):
            continue

        # Parse date and normalize to UTC timestamp
        try:
            obs_dt = datetime.fromisoformat(f"{time_str}T00:00:00+00:00")
        except ValueError:
            obs_dt = datetime.now(timezone.utc)

        readings.append(
            {
                "gauge_id": None,
                "observed_at": obs_dt,
                "level_m": None,
                "discharge_m3s": val,
                "quality": "good",
                "raw_payload": {
                    "provider": "open_meteo",
                    "model": "GloFAS",
                    "data_type": "modelled_daily_river_discharge",
                    "daily_units": data.get("daily_units", {}),
                    "raw_discharge": discharge_val,
                },
            }
        )

    return readings
