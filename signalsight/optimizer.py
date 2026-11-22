"""Tower placement optimizer.

Problem: choose K new sites (from a candidate lattice) that maximise a coverage-utility objective.

Objective (sum over grid cells of the best-server signal):
    u(P) = class(P) + 0.3 * clip((P + 120) / 50, 0, 1)
where class(P) = 0 dead, 1 weak, 2 usable, 3 strong (dead -> weak -> usable -> strong are the big wins,
the continuous term breaks ties and keeps improving signal quality).
A candidate also pays `overlap_penalty` for every cell it would serve that already has a usable signal
(wasteful overlap).

Algorithm: greedy facility-location selection followed by swap-based local search that re-places each tower
given all others. The un-penalised coverage utility is monotone submodular, for which greedy has a (1 - 1/e)
guarantee; the overlap penalty breaks monotonicity, so this is a good heuristic with no formal guarantee.
A minimum inter-site distance is enforced (and relaxed only if needed to place exactly K towers).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np
import pandas as pd

from .coverage import Coverage, compute_coverage, summarize
from .models import Region, Thresholds, Tower
from .propagation import rx_power_dbm

Progress = Callable[[float, str], None]


@dataclass
class OptimizationResult:
    requested: int
    proposed: list[Tower]
    cov_before: Coverage
    cov_after: Coverage
    stats_before: dict
    stats_after: dict
    min_sep_km: float
    effective_sep_km: float
    n_candidates: int
    swaps: int
    greedy_gains: list[float] = field(default_factory=list)
    proposals: pd.DataFrame = field(default_factory=pd.DataFrame)


def _utility(p: np.ndarray, thr: Thresholds) -> np.ndarray:
    cls = (p >= thr.weak_dbm).astype(np.float32) + (p >= thr.usable_dbm) + (p >= thr.strong_dbm)
    return cls + 0.3 * np.clip((p + 120.0) / 50.0, 0.0, 1.0)


def _marginal(S: np.ndarray, base: np.ndarray, thr: Thresholds, lam: float, w: np.ndarray) -> np.ndarray:
    """Gain of each candidate row of S; w is 1 on land and 0 on sea, so only land cells are valued."""
    ub = _utility(base, thr)
    base_ok = (base >= thr.usable_dbm) & (w > 0)
    out = np.empty(S.shape[0], dtype=np.float64)
    for s in range(0, S.shape[0], 128):
        blk = S[s:s + 128]
        new = np.maximum(blk, base[None, :])
        gain = ((_utility(new, thr) - ub[None, :]) * w[None, :]).sum(axis=1)
        waste = ((blk >= thr.usable_dbm) & base_ok[None, :]).sum(axis=1)
        out[s:s + 128] = gain - lam * waste
    return out


def optimize(
    existing: Sequence[Tower],
    k: int,
    region: Region,
    thr: Thresholds,
    eirp_dbm: float,
    freq_mhz: float,
    path_loss_exp: float,
    bw_mhz: float = 20.0,
    min_sep_km: float = 0.5,
    overlap_penalty: float = 0.15,
    max_candidates: int = 500,
    refine_passes: int = 2,
    progress: Progress | None = None,
    land: np.ndarray | None = None,
) -> OptimizationResult:
    report = progress or (lambda f, m: None)
    cov_before = compute_coverage(existing, region, thr, land)
    ny, nx = region.ny, region.nx
    X, Y = region.grid_xy_km()
    gx, gy = X.ravel().astype(np.float32), Y.ravel().astype(np.float32)
    G = gx.size
    base = cov_before.best.ravel().astype(np.float32)
    w = cov_before.mask().ravel().astype(np.float32)   # 1 = land (counts), 0 = sea (ignored)

    # ---- candidate lattice (cell centres on a coarse stride) ----
    stride = max(1, int(math.ceil(math.sqrt(max(w.sum(), 1.0) / max_candidates))))
    R, C = np.meshgrid(np.arange(stride // 2, ny, stride), np.arange(stride // 2, nx, stride), indexing="ij")
    cand = (R * nx + C).ravel()
    land_ok = w[cand] > 0                      # towers are only ever proposed on land
    keep = land_ok.copy()
    ex_xy = [region.to_xy(t.lat, t.lon) for t in existing]
    for tx, ty in ex_xy:
        keep &= np.hypot(gx[cand] - tx, gy[cand] - ty) >= min_sep_km
    if keep.sum() < k:  # too restrictive -> only forbid sites practically on top of a tower
        keep = land_ok.copy()
        for tx, ty in ex_xy:
            keep &= np.hypot(gx[cand] - tx, gy[cand] - ty) >= 0.05
    cand = cand[keep]
    nc = cand.size
    if nc == 0:
        raise ValueError("No feasible candidate locations on land in the region.")
    cx, cy = gx[cand], gy[cand]

    # ---- predicted signal of a hypothetical tower at every candidate ----
    report(0.02, "Predicting signal for candidate sites…")
    S = np.empty((nc, G), dtype=np.float32)
    for s in range(0, nc, 128):
        d_km = np.hypot(cx[s:s + 128, None] - gx[None, :], cy[s:s + 128, None] - gy[None, :])
        S[s:s + 128] = rx_power_dbm(eirp_dbm, freq_mhz, path_loss_exp, d_km, bw_mhz).astype(np.float32)
    D = np.hypot(cx[:, None] - cx[None, :], cy[:, None] - cy[None, :])

    state = {"sep": float(min_sep_km)}

    def available(chosen: list[int]) -> np.ndarray:
        m = np.ones(nc, dtype=bool)
        if chosen:
            m &= D[:, chosen].min(axis=1) >= state["sep"]
            m[chosen] = False
        return m

    # ---- greedy selection ----
    chosen: list[int] = []
    gains: list[float] = []
    cur = base.copy()
    for step in range(k):
        av = available(chosen)
        while not av.any() and state["sep"] > 0.005:
            state["sep"] *= 0.5
            av = available(chosen)
        if not av.any():
            break
        idx = np.flatnonzero(av)
        sc = _marginal(S[idx], cur, thr, overlap_penalty, w)
        j = int(idx[int(np.argmax(sc))])
        chosen.append(j)
        gains.append(float(sc.max()))
        cur = np.maximum(cur, S[j])
        report(0.05 + 0.45 * (step + 1) / k,
               f"Greedy placement {step + 1}/{k}…")

    # ---- swap-based local search ----
    swaps = 0
    for p in range(max(refine_passes, 0)):
        changed = False
        for pos in range(len(chosen)):
            others = chosen[:pos] + chosen[pos + 1:]
            bi = base if not others else np.maximum(base, S[others].max(axis=0))
            av = available(others)
            idx = np.flatnonzero(av)
            if idx.size == 0:
                continue
            sc = _marginal(S[idx], bi, thr, overlap_penalty, w)
            where = np.flatnonzero(idx == chosen[pos])
            cur_sc = sc[where[0]] if where.size else -np.inf
            b = int(np.argmax(sc))
            if idx[b] != chosen[pos] and sc[b] > cur_sc + 1e-6:
                chosen[pos] = int(idx[b])
                swaps += 1
                changed = True
            report(0.5 + 0.45 * ((p * len(chosen)) + pos + 1) / max(refine_passes * len(chosen), 1),
                   f"Refining placement (pass {p + 1}/{refine_passes})…")
        if not changed:
            break

    # ---- build result ----
    lats, lons = region.cell_centres()
    proposed = []
    for n_i, j in enumerate(chosen, start=1):
        flat = int(cand[j])
        proposed.append(Tower(f"Proposed {n_i}", float(lats[flat // nx]), float(lons[flat % nx]),
                              eirp_dbm, freq_mhz, path_loss_exp, proposed=True, bw_mhz=bw_mhz))
    all_towers = list(existing) + proposed
    cov_after = compute_coverage(all_towers, region, thr, land)
    stats_after = summarize(cov_after, region)

    cell = region.cell_area_km2
    rows = []
    for n_i, t in enumerate(proposed):
        idx = len(existing) + n_i
        mine = (cov_after.best_idx == idx) & cov_after.mask()
        lifted = mine & (cov_before.classes < 2) & (cov_after.classes >= 2)
        dead_fixed = mine & (cov_before.classes == 0) & (cov_after.classes >= 1)
        rows.append({
            "Site": t.name,
            "Latitude": round(t.lat, 6),
            "Longitude": round(t.lon, 6),
            "EIRP (dBm)": t.eirp_dbm,
            "Frequency (MHz)": t.freq_mhz,
            "Weak/dead → usable (km²)": round(float(lifted.sum() * cell), 3),
            "Dead zone removed (km²)": round(float(dead_fixed.sum() * cell), 3),
            "Best-server area (km²)": round(float(mine.sum() * cell), 3),
        })
    report(1.0, "Done")
    return OptimizationResult(
        requested=k, proposed=proposed, cov_before=cov_before, cov_after=cov_after,
        stats_before=summarize(cov_before, region), stats_after=stats_after,
        min_sep_km=float(min_sep_km), effective_sep_km=state["sep"], n_candidates=int(nc),
        swaps=swaps, greedy_gains=gains, proposals=pd.DataFrame(rows),
    )
