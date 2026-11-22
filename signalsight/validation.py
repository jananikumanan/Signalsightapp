"""Input parsing and validation with human-readable error messages."""
from __future__ import annotations

import math
from typing import Any, Sequence

from .models import KM_PER_DEG_LAT, KM_PER_DEG_LON_EQUATOR, Tower

LIMITS = {"freq": (100.0, 40000.0), "eirp": (10.0, 90.0), "n": (1.5, 6.0), "bw": (5.0, 20.0)}
MAX_EXTENT_KM = 150.0


def _num(raw: Any, label: str, lo: float, hi: float, errors: list[str], unit: str = "") -> float | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        errors.append(f"{label}: value is missing.")
        return None
    try:
        v = float(str(raw).strip())
    except ValueError:
        errors.append(f"{label}: '{raw}' is not a valid number.")
        return None
    if not math.isfinite(v):
        errors.append(f"{label}: value must be a finite number.")
        return None
    if not lo <= v <= hi:
        errors.append(f"{label}: {v:g}{unit} is outside the allowed range ({lo:g} to {hi:g}{unit}).")
        return None
    return v


def build_towers(rows: Sequence[dict]) -> tuple[list[Tower], list[str]]:
    """rows: dicts with raw name/lat/lon/eirp/freq/n values. Returns (towers, errors)."""
    errors: list[str] = []
    towers: list[Tower] = []
    for i, r in enumerate(rows, start=1):
        tag = f"Tower {i}"
        lat = _num(r.get("lat"), f"{tag} latitude", -90, 90, errors, "°")
        lon = _num(r.get("lon"), f"{tag} longitude", -180, 180, errors, "°")
        eirp = _num(r.get("eirp"), f"{tag} EIRP", *LIMITS["eirp"], errors, " dBm")
        freq = _num(r.get("freq"), f"{tag} frequency", *LIMITS["freq"], errors, " MHz")
        n = _num(r.get("n"), f"{tag} path-loss exponent", *LIMITS["n"], errors)
        bw = _num(r.get("bw", 20.0), f"{tag} bandwidth", *LIMITS["bw"], errors, " MHz")
        if None in (lat, lon, eirp, freq, n, bw):
            continue
        name = (str(r.get("name") or "").strip()) or tag
        towers.append(Tower(name, lat, lon, eirp, freq, n, bw_mhz=bw))
    return towers, errors


def validate_setup(towers: Sequence[Tower], padding_km: float) -> list[str]:
    errors: list[str] = []
    if not towers:
        return ["At least one existing tower is required."]
    if not 0.5 <= padding_km <= 50:
        errors.append("Region padding must be between 0.5 and 50 km.")
    for i in range(len(towers)):
        for j in range(i + 1, len(towers)):
            a, b = towers[i], towers[j]
            dy = (a.lat - b.lat) * KM_PER_DEG_LAT
            dx = (a.lon - b.lon) * KM_PER_DEG_LON_EQUATOR * math.cos(math.radians((a.lat + b.lat) / 2))
            if math.hypot(dx, dy) < 0.01:
                errors.append(f"'{a.name}' and '{b.name}' are at (almost) the same location.")
    lats = [t.lat for t in towers]
    lons = [t.lon for t in towers]
    kx = KM_PER_DEG_LON_EQUATOR * math.cos(math.radians(sum(lats) / len(lats)))
    extent = max((max(lons) - min(lons)) * kx, (max(lats) - min(lats)) * KM_PER_DEG_LAT)
    if extent > MAX_EXTENT_KM:
        errors.append(
            f"Towers span {extent:.0f} km; the analysis region is limited to {MAX_EXTENT_KM:.0f} km. "
            "Check the coordinates (lat/lon swapped?) or analyse the towers in separate groups."
        )
    return errors


def coordinate_warnings(towers: Sequence[Tower]) -> list[str]:
    """Non-blocking hints for coordinates that look swapped (latitude and longitude the wrong way round)."""
    warns = []
    for t in towers:
        if abs(t.lat) > 60 and abs(t.lon) < 60:
            warns.append(f"'{t.name}' has latitude {t.lat:g}° and longitude {t.lon:g}°. Latitude above 60° is unusual - "
                         "check that latitude and longitude are not swapped.")
    return warns
