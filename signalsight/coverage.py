"""Coverage computation, statistics and underserved-area detection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import ndimage

from .models import CLASS_NAMES, Region, Thresholds, Tower
from .propagation import rx_power_dbm, tower_radius_km


@dataclass
class Coverage:
    per_tower: np.ndarray   # (T, ny, nx) predicted RSRP-like power in dBm
    best: np.ndarray        # (ny, nx) best-server power
    best_idx: np.ndarray    # (ny, nx) index of best-server tower
    n_serving: np.ndarray   # (ny, nx) number of towers at/above the usable threshold
    classes: np.ndarray     # (ny, nx) 0 dead, 1 weak, 2 usable, 3 strong
    thr: Thresholds
    land: np.ndarray | None = None  # (ny, nx) True on land; None = every cell counts

    def mask(self) -> np.ndarray:
        return np.ones(self.classes.shape, dtype=bool) if self.land is None else self.land


def classify(power: np.ndarray, thr: Thresholds) -> np.ndarray:
    return ((power >= thr.weak_dbm).astype(np.int8)
            + (power >= thr.usable_dbm) + (power >= thr.strong_dbm)).astype(np.int8)


def compute_coverage(towers: Sequence[Tower], region: Region, thr: Thresholds, land: np.ndarray | None = None) -> Coverage:
    X, Y = region.grid_xy_km()
    layers = []
    for t in towers:
        tx, ty = region.to_xy(t.lat, t.lon)
        dist = np.hypot(X - tx, Y - ty)
        layers.append(rx_power_dbm(t.eirp_dbm, t.freq_mhz, t.path_loss_exp, dist, t.bw_mhz).astype(np.float32))
    per = np.stack(layers)
    best = per.max(axis=0)
    return Coverage(
        per_tower=per,
        best=best,
        best_idx=per.argmax(axis=0),
        n_serving=(per >= thr.usable_dbm).sum(axis=0).astype(np.int16),
        classes=classify(best, thr),
        thr=thr,
        land=land,
    )


def summarize(cov: Coverage, region: Region) -> dict:
    m = cov.mask()                       # only land cells are analysed (all cells when no land mask is set)
    n = max(int(m.sum()), 1)
    area = region.area_km2 * n / m.size
    counts = np.bincount(cov.classes[m], minlength=4)
    pct = counts / n * 100
    km2 = counts / n * area
    ns = cov.n_serving[m]
    covered = float((ns >= 1).mean() * 100)
    ov2 = float((ns >= 2).mean() * 100)
    hist = {
        "0 towers": float((ns == 0).mean() * 100),
        "1 tower": float((ns == 1).mean() * 100),
        "2 towers": float((ns == 2).mean() * 100),
        "3 towers": float((ns == 3).mean() * 100),
        "4+ towers": float((ns >= 4).mean() * 100),
    }
    return {
        "area_km2": area,
        "region_km2": region.area_km2,
        "land_only": cov.land is not None,
        "n_towers": int(cov.per_tower.shape[0]),
        "pct": {CLASS_NAMES[i]: float(pct[i]) for i in range(4)},
        "km2": {CLASS_NAMES[i]: float(km2[i]) for i in range(4)},
        "covered_pct": float(pct[2] + pct[3]),
        "underserved_pct": float(pct[0] + pct[1]),
        "mean_rsrp": float(cov.best[m].mean()),
        "overlap2_pct": ov2,
        "overlap3_pct": float((ns >= 3).mean() * 100),
        "overlap2_km2": ov2 / 100 * area,
        "redundancy_of_covered_pct": (ov2 / covered * 100) if covered > 0 else 0.0,
        "avg_serving_in_covered": float(ns[ns >= 1].mean()) if (ns >= 1).any() else 0.0,
        "serving_hist": hist,
    }


def per_tower_table(towers: Sequence[Tower], cov: Coverage, region: Region) -> pd.DataFrame:
    cell = region.cell_area_km2
    m = cov.mask()
    usable = (cov.per_tower >= cov.thr.usable_dbm) & m[None, :, :]
    multi = (cov.n_serving >= 2) & m
    rows = []
    for i, t in enumerate(towers):
        rows.append({
            "Tower": t.name,
            "Type": "Proposed" if t.proposed else "Existing",
            "Lat": round(t.lat, 6),
            "Lon": round(t.lon, 6),
            "EIRP (dBm)": t.eirp_dbm,
            "Freq (MHz)": t.freq_mhz,
            "Path-loss n": t.path_loss_exp,
            "Strong radius (km)": round(tower_radius_km(t, cov.thr.strong_dbm), 3),
            "Usable radius (km)": round(tower_radius_km(t, cov.thr.usable_dbm), 3),
            "Weak radius (km)": round(tower_radius_km(t, cov.thr.weak_dbm), 3),
            "Best-server area (km²)": round(float(((cov.best_idx == i) & m).sum() * cell), 3),
            "Usable footprint in region (km²)": round(float(usable[i].sum() * cell), 3),
            "Overlapped footprint (km²)": round(float((usable[i] & multi).sum() * cell), 3),
        })
    return pd.DataFrame(rows)


def find_underserved_regions(cov: Coverage, region: Region, top_n: int = 8) -> pd.DataFrame:
    """Connected clusters of weak/dead cells, ranked by area."""
    mask = (cov.classes <= 1) & cov.mask()
    labels, count = ndimage.label(mask)
    if count == 0:
        return pd.DataFrame(columns=["Rank", "Centre lat", "Centre lon", "Area (km²)",
                                     "% of region", "Dead share (%)", "Worst signal (dBm)", "Mean signal (dBm)"])
    lats, lons = region.cell_centres()
    rr, cc = np.indices(mask.shape)
    cell = region.cell_area_km2
    rows = []
    for lab in range(1, count + 1):
        sel = labels == lab
        size = int(sel.sum())
        pw = cov.best[sel]
        rows.append({
            "Centre lat": round(float(lats[rr[sel].mean().round().astype(int)]), 5),
            "Centre lon": round(float(lons[cc[sel].mean().round().astype(int)]), 5),
            "Area (km²)": round(size * cell, 3),
            "% of region": round(size / mask.size * 100, 2),
            "Dead share (%)": round(float((cov.classes[sel] == 0).mean() * 100), 1),
            "Worst signal (dBm)": round(float(pw.min()), 1),
            "Mean signal (dBm)": round(float(pw.mean()), 1),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df.assign(Rank=[])
    df = df.sort_values("Area (km²)", ascending=False).head(top_n).reset_index(drop=True)
    df.insert(0, "Rank", np.arange(1, len(df) + 1))
    return df
