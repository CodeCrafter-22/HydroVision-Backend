"""PostGIS geometry utilities for parsing coordinates safely."""

import math
import struct
from typing import Any, Optional, Tuple


def parse_ewkb_point(geom: Any) -> Optional[Tuple[float, float]]:
    """Safely extracts (longitude, latitude) from a PostGIS Point geometry.

    Supports:
    1. PostGIS EWKB hexadecimal strings (standard PostgREST output).
    2. GeoJSON dictionary structures ({'type': 'Point', 'coordinates': [lon, lat]}).

    Validates:
    - Byte-order marker (endianness).
    - Geometry type is strictly Point (type code 1).
    - SRID when present is 4326 (WGS 84).
    - Coordinates are finite floating point numbers.
    - Longitude in [-180.0, 180.0] and Latitude in [-90.0, 90.0].

    Returns:
        (longitude, latitude) as a float tuple, or None if invalid/missing.
    """
    if geom is None:
        return None

    # Handle GeoJSON format if returned by client/database
    if isinstance(geom, dict):
        if geom.get("type") == "Point":
            coords = geom.get("coordinates")
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                try:
                    lon, lat = float(coords[0]), float(coords[1])
                    if math.isfinite(lon) and math.isfinite(lat):
                        if -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0:
                            return lon, lat
                except (ValueError, TypeError):
                    return None
        return None

    # Handle EWKB hexadecimal string
    if not isinstance(geom, str):
        return None

    hex_str = geom.strip()
    if not hex_str or len(hex_str) < 42:  # Minimum 21 bytes for a 2D Point
        return None

    try:
        raw = bytes.fromhex(hex_str)
    except ValueError:
        return None

    # 1. Byte-order marker
    endian = raw[0]
    if endian not in (0, 1):
        return None
    prefix = "<" if endian == 1 else ">"

    # 2. Geometry type and flags
    if len(raw) < 5:
        return None
    geom_type = struct.unpack(f"{prefix}I", raw[1:5])[0]
    type_code = geom_type & 0xFF
    if type_code != 1:  # Point = 1
        return None

    has_srid = bool(geom_type & 0x20000000)
    offset = 5

    # 3. SRID validation
    if has_srid:
        if len(raw) < 9:
            return None
        srid = struct.unpack(f"{prefix}I", raw[5:9])[0]
        if srid != 4326:
            return None
        offset = 9

    # 4. Coordinate extraction
    if len(raw) < offset + 16:
        return None

    lon, lat = struct.unpack(f"{prefix}dd", raw[offset : offset + 16])

    # 5. Finiteness & range validation
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None

    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        return None

    return lon, lat
