"""Core data structures: towers, signal thresholds and the analysed geographic region."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

KM_PER_DEG_LAT = 110.574
KM_PER_DEG_LON_EQUATOR = 111.320

CLASS_NAMES = ("Dead zone", "Weak", "Usable", "Strong")
CLASS_COLORS = ("#e8808a", "#f5b383", "#f4e08c", "#6fc7b0")


@dataclass(frozen=True)
class Tower:
    name: str
    lat: float
    lon: float
    eirp_dbm: float
    freq_mhz: float
    path_loss_exp: float
    proposed: bool = False
    bw_mhz: float = 20.0   # LTE channel bandwidth; sets the per-subcarrier (RSRP) power


@dataclass(frozen=True)
class Thresholds:
    """Received-power thresholds (dBm). Below `weak_dbm` a location is a dead zone."""

    strong_dbm: float = -85.0
    usable_dbm: float = -100.0
    weak_dbm: float = -110.0

    def errors(self) -> list[str]:
        errs = []
        for label, v in (("Strong", self.strong_dbm), ("Usable", self.usable_dbm), ("Weak", self.weak_dbm)):
            if not math.isfinite(v) or not -140 <= v <= -40:
                errs.append(f"{label} threshold {v} dBm must be between -140 and -40 dBm.")
        if not errs and not (self.strong_dbm > self.usable_dbm > self.weak_dbm):
            errs.append("Thresholds must satisfy: Strong > Usable > Weak (in dBm).")
        return errs


@dataclass(frozen=True)
class Region:
    """Rectangular analysis region on a regular lat/lon grid (rows run north -> south)."""

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    nx: int
    ny: int

    @property
    def lat0(self) -> float:
        return (self.lat_min + self.lat_max) / 2

    @property
    def lon0(self) -> float:
        return (self.lon_min + self.lon_max) / 2

    @property
    def kx(self) -> float:
        return KM_PER_DEG_LON_EQUATOR * math.cos(math.radians(self.lat0))

    @property
    def ky(self) -> float:
        return KM_PER_DEG_LAT

    @property
    def width_km(self) -> float:
        return (self.lon_max - self.lon_min) * self.kx

    @property
    def height_km(self) -> float:
        return (self.lat_max - self.lat_min) * self.ky

    @property
    def area_km2(self) -> float:
        return self.width_km * self.height_km

    @property
    def cell_area_km2(self) -> float:
        return self.area_km2 / (self.nx * self.ny)

    @property
    def bounds(self) -> list[list[float]]:
        return [[self.lat_min, self.lon_min], [self.lat_max, self.lon_max]]

    def cell_centres(self) -> tuple[np.ndarray, np.ndarray]:
        dlat = (self.lat_max - self.lat_min) / self.ny
        dlon = (self.lon_max - self.lon_min) / self.nx
        lats = self.lat_max - (np.arange(self.ny) + 0.5) * dlat  # north first
        lons = self.lon_min + (np.arange(self.nx) + 0.5) * dlon
        return lats, lons

    def to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * self.ky

    def grid_xy_km(self) -> tuple[np.ndarray, np.ndarray]:
        lats, lons = self.cell_centres()
        LON, LAT = np.meshgrid(lons, lats)
        return (LON - self.lon0) * self.kx, (LAT - self.lat0) * self.ky

    @classmethod
    def from_towers(cls, towers: Sequence[Tower], padding_km: float, resolution: int) -> "Region":
        lats = [t.lat for t in towers]
        lons = [t.lon for t in towers]
        lat_mid = (min(lats) + max(lats)) / 2
        kx = KM_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat_mid))
        dlat = padding_km / KM_PER_DEG_LAT
        dlon = padding_km / kx
        lat_min, lat_max = max(min(lats) - dlat, -89.9), min(max(lats) + dlat, 89.9)
        lon_min, lon_max = min(lons) - dlon, max(lons) + dlon
        w = (lon_max - lon_min) * kx
        h = (lat_max - lat_min) * KM_PER_DEG_LAT
        if w >= h:
            nx, ny = resolution, max(20, round(resolution * h / w))
        else:
            ny, nx = resolution, max(20, round(resolution * w / h))
        return cls(lat_min, lat_max, lon_min, lon_max, int(nx), int(ny))
