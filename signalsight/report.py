"""Markdown report generator for download."""
from __future__ import annotations

import pandas as pd

from .models import CLASS_NAMES


def _row(name, b, a=None, fmt="{:.2f}"):
    if a is None:
        return f"| {name} | {fmt.format(b)} |"
    return f"| {name} | {fmt.format(b)} | {fmt.format(a)} | {fmt.format(a - b)} |"


def _md_table(df: pd.DataFrame) -> str:
    """Pipe table without extra dependencies (so the report is real Markdown everywhere)."""
    cols = [str(c).replace("|", "/") for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for rec in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in rec) + " |")
    return "\n".join(lines)


def build_markdown_report(cfg: dict, sb: dict, sa: dict | None, res, under_before: pd.DataFrame,
                          under_after: pd.DataFrame | None) -> str:
    towers, thr, region = cfg["towers"], cfg["thr"], cfg["region"]
    L = ["# SignalSight – Coverage Analysis Report", "",
         "> **Predicted, not measured.** Results come from a log-distance path-loss model "
         "(P_rx = EIRP − 10·log10(N_sc) − PL(d), PL referenced to 100 m). Terrain, buildings, antenna patterns and "
         "real traffic are not modelled. Validate with drive tests before deployment.", "",
         "## Scope",
         f"- Area analysed: {sb['area_km2']:.2f} km²{' (land only, sea excluded)' if sb.get('land_only') else ''} in a "
         f"{region.width_km:.2f} × {region.height_km:.2f} km box, "
         f"grid {region.nx} × {region.ny} cells",
         f"- Existing towers: {len(towers)}",
         f"- Proposed towers: {len(res.proposed) if res else 0}",
         f"- Thresholds: strong ≥ {thr.strong_dbm:g} dBm, usable ≥ {thr.usable_dbm:g} dBm, "
         f"weak ≥ {thr.weak_dbm:g} dBm, dead below", ""]
    L += ["## Coverage (% of area)", ""]
    if sa:
        L += ["| Class | Before | After | Change (pp) |", "|---|---|---|---|"]
        for c in reversed(CLASS_NAMES):
            L.append(_row(c, sb["pct"][c], sa["pct"][c]))
        L.append(_row("Covered (usable+)", sb["covered_pct"], sa["covered_pct"]))
        L.append(_row("Overlap ≥2 towers", sb["overlap2_pct"], sa["overlap2_pct"]))
        L.append(_row("Mean best-server signal (dBm)", sb["mean_rsrp"], sa["mean_rsrp"]))
        d0, d1 = sb["km2"]["Dead zone"], sa["km2"]["Dead zone"]
        rel = (1 - d1 / d0) * 100 if d0 > 0 else 0.0
        L += ["", f"**Dead-zone area:** {d0:.2f} km² → {d1:.2f} km² ({rel:.1f}% reduction).", ""]
    else:
        L += ["| Class | Current |", "|---|---|"]
        for c in reversed(CLASS_NAMES):
            L.append(_row(c, sb["pct"][c]))
        L.append("")
    L += ["## Existing towers", "", "| Name | Lat | Lon | EIRP dBm | Freq MHz | BW MHz | n |", "|---|---|---|---|---|---|---|"]
    for t in towers:
        L.append(f"| {t.name} | {t.lat:.6f} | {t.lon:.6f} | {t.eirp_dbm:g} | {t.freq_mhz:g} | {t.bw_mhz:g} | {t.path_loss_exp:g} |")
    if res:
        L += ["", "## Recommended new tower locations", "", _md_table(res.proposals)]
    L += ["", "## Areas requiring improvement (before optimization)", ""]
    L.append(_md_table(under_before) if not under_before.empty else "None – no weak or dead cells.")
    if under_after is not None:
        L += ["", "## Remaining weak/dead areas (after optimization)", ""]
        L.append(_md_table(under_after) if not under_after.empty else "None – no weak or dead cells remain.")
    return "\n".join(L)
