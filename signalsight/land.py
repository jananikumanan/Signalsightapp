"""Land mask: keeps proposed towers off the sea and keeps sea cells out of the coverage statistics.

The mask is built with a plain NumPy point-in-polygon test (even-odd rule), so no GIS library is needed.
A bundled, simplified India boundary is used by default; any GeoJSON Polygon/MultiPolygon can be supplied instead.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from .models import Region

BUNDLED = Path(__file__).with_name("data") / "india_land.geojson"
Polygon = tuple  # (bbox (xmin, ymin, xmax, ymax), [ring arrays of shape (m, 2) in lon, lat])


def _geoms(obj):
    t = obj.get("type")
    if t == "FeatureCollection":
        for f in obj.get("features", []):
            yield from _geoms(f)
    elif t == "Feature":
        yield from _geoms(obj.get("geometry") or {})
    elif t == "GeometryCollection":
        for g in obj.get("geometries", []):
            yield from _geoms(g)
    elif t == "Polygon":
        yield [obj["coordinates"]]
    elif t == "MultiPolygon":
        yield obj["coordinates"]


def parse_geojson(obj) -> list[Polygon]:
    """GeoJSON dict -> list of (bbox, rings). Raises ValueError if it holds no polygons."""
    polys: list[Polygon] = []
    for part_list in _geoms(obj):
        for poly in part_list:
            rings = [np.asarray(r, dtype=np.float64)[:, :2] for r in poly if len(r) >= 4]
            if rings:
                outer = rings[0]
                polys.append(((outer[:, 0].min(), outer[:, 1].min(), outer[:, 0].max(), outer[:, 1].max()), rings))
    if not polys:
        raise ValueError("The GeoJSON file has no Polygon or MultiPolygon shapes.")
    return polys


@lru_cache(maxsize=1)
def bundled() -> list[Polygon]:
    return parse_geojson(json.loads(BUNDLED.read_text(encoding="utf-8")))


def _inside(px: np.ndarray, py: np.ndarray, rings) -> np.ndarray:
    """Even-odd ray casting of points against all rings of one polygon (holes are handled by the parity)."""
    crossings = np.zeros(px.shape, dtype=np.int32)
    for ring in rings:
        ax, ay, bx, by = ring[:-1, 0], ring[:-1, 1], ring[1:, 0], ring[1:, 1]
        for s in range(0, ax.size, 256):
            x1, y1, x2, y2 = ax[s:s + 256], ay[s:s + 256], bx[s:s + 256], by[s:s + 256]
            straddle = (y1[None, :] > py[:, None]) != (y2[None, :] > py[:, None])
            dy = np.where(y2 == y1, 1.0, y2 - y1)
            xint = x1[None, :] + (py[:, None] - y1[None, :]) * ((x2 - x1) / dy)[None, :]
            crossings += (straddle & (px[:, None] < xint)).sum(axis=1)
    return (crossings % 2) == 1


def land_mask(region: Region, polygons: list[Polygon]) -> np.ndarray:
    """Boolean (ny, nx) array, True where the cell centre is on land."""
    lats, lons = region.cell_centres()
    LON, LAT = np.meshgrid(lons, lats)
    px, py = LON.ravel(), LAT.ravel()
    out = np.zeros(px.shape, dtype=bool)
    for (x0, y0, x1, y1), rings in polygons:
        sel = np.flatnonzero((px >= x0) & (px <= x1) & (py >= y0) & (py <= y1) & ~out)
        if sel.size:
            out[sel] |= _inside(px[sel], py[sel], rings)
    return out.reshape(region.ny, region.nx)
