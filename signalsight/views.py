"""Streamlit pages. Every page reads from / writes to st.session_state so all views stay connected."""
from __future__ import annotations


import math
import re

import numpy as np
import pandas as pd
import streamlit as st

from . import land as land_mod
from . import ui
from .coverage import compute_coverage, find_underserved_regions, per_tower_table, summarize
from .mapping import build_map
from .models import CLASS_COLORS, CLASS_NAMES, Region, Thresholds
from .optimizer import optimize
from .propagation import tower_radius_km
from .report import build_markdown_report
from .validation import LIMITS, build_towers, coordinate_warnings, validate_setup

PAGE_WELCOME = "🏠 Welcome"
PAGE_CONFIG = "⚙️ Tower Configuration"
PAGE_MAP = "🗺️ Coverage Map"
PAGE_OPT = "🎯 Placement Optimizer"
PAGE_REPORT = "📊 Analysis & Report"
PAGES = [PAGE_WELCOME, PAGE_CONFIG, PAGE_MAP, PAGE_OPT, PAGE_REPORT]

CENTRE = (13.0827, 80.2707)  # default demo centre; fully editable
DEFAULTS = {
    "nav": PAGE_WELCOME, "land_on": True, "n_towers": 4, "g_freq": 1800.0, "g_bw": 20.0, "g_eirp": 61.0, "g_n": 3.8,
    "padding_km": 2.5, "resolution": 100, "thr_strong": -85.0, "thr_usable": -100.0, "thr_weak": -110.0,
    "opt_k": 3, "opt_eirp": 61.0, "opt_freq": 1800.0, "opt_n": 3.8, "opt_sep": 0.5, "opt_pen": 0.15, "opt_cand": 500,
}


# ----------------------------------------------------------------------------- state helpers
_TOWER_KEY = re.compile(r"^t\d+_(name|lat|lon|eirp|freq|n)$")


def init_state() -> None:
    s = st.session_state
    for k, v in DEFAULTS.items():
        s.setdefault(k, v)
    # Streamlit forgets the value of any widget that is not drawn on the current page. Re-assigning the value at
    # the top of every run keeps the Configuration and Optimizer inputs when the user moves between pages.
    for k in list(s.keys()):
        if k != "nav" and (k in DEFAULTS or _TOWER_KEY.match(k)):
            s[k] = s[k]


def goto(page: str) -> None:
    st.session_state["nav"] = page


def _spiral(i: int, spacing_km: float = 2.2) -> tuple[float, float]:
    r, a = spacing_km * math.sqrt(i), i * 2.399963
    return (CENTRE[0] + r * math.sin(a) / 110.574,
            CENTRE[1] + r * math.cos(a) / (111.32 * math.cos(math.radians(CENTRE[0]))))


def _ensure_tower_keys(n: int) -> None:
    s = st.session_state
    for i in range(n):
        lat, lon = _spiral(i)
        s.setdefault(f"t{i}_name", f"Tower {i + 1}")
        s.setdefault(f"t{i}_lat", f"{lat:.5f}")
        s.setdefault(f"t{i}_lon", f"{lon:.5f}")
        s.setdefault(f"t{i}_eirp", float(s["g_eirp"]))
        s.setdefault(f"t{i}_freq", float(s["g_freq"]))
        s.setdefault(f"t{i}_n", float(s["g_n"]))


def load_sample() -> None:
    s = st.session_state
    s["n_towers"] = 5
    eirps = [62.0, 60.0, 61.0, 59.0, 63.0]
    for i in range(5):
        lat, lon = _spiral(i)
        s[f"t{i}_name"] = f"Tower {i + 1}"
        s[f"t{i}_lat"], s[f"t{i}_lon"] = f"{lat:.5f}", f"{lon:.5f}"
        s[f"t{i}_eirp"], s[f"t{i}_freq"], s[f"t{i}_n"] = eirps[i], 1800.0, 3.8
    s["cfg_errors"] = []


def clear_custom_land() -> None:
    st.session_state.pop("land_custom", None)


def apply_globals() -> None:
    s = st.session_state
    for i in range(int(s["n_towers"])):
        s[f"t{i}_eirp"], s[f"t{i}_freq"], s[f"t{i}_n"] = float(s["g_eirp"]), float(s["g_freq"]), float(s["g_n"])


def run_analysis() -> None:
    """Callback for the 'Validate & analyse' button: validate -> compute -> store -> jump to the map."""
    s = st.session_state
    try:
        n = int(s["n_towers"])
        rows = [{"name": s.get(f"t{i}_name"), "lat": s.get(f"t{i}_lat"), "lon": s.get(f"t{i}_lon"),
                 "eirp": s.get(f"t{i}_eirp"), "freq": s.get(f"t{i}_freq"), "n": s.get(f"t{i}_n"), "bw": s.get("g_bw")} for i in range(n)]
        towers, errors = build_towers(rows)
        thr = Thresholds(float(s["thr_strong"]), float(s["thr_usable"]), float(s["thr_weak"]))
        errors += thr.errors()
        if not errors:
            errors += validate_setup(towers, float(s["padding_km"]))
        s["cfg_errors"] = errors
        s["cfg_warnings"] = [] if errors else coordinate_warnings(towers)
        if errors:
            return
        region = Region.from_towers(towers, float(s["padding_km"]), int(s["resolution"]))
        land, s["land_info"] = None, ""
        if s["land_on"]:
            mask = land_mod.land_mask(region, s.get("land_custom") or land_mod.bundled())
            if mask.any():
                land = mask
            else:
                s["land_info"] = ("The analysed area is outside the land boundary, so every cell is analysed. "
                                  "Upload a boundary for this area to keep towers off the water.")
        cov = compute_coverage(towers, region, thr, land)
        s["cfg"] = {"towers": towers, "thr": thr, "region": region, "land": land,
                    "padding_km": float(s["padding_km"]), "resolution": int(s["resolution"])}
        s["cov_before"], s["stats_before"], s["opt"] = cov, summarize(cov, region), None
        s["opt_eirp"] = round(float(np.mean([t.eirp_dbm for t in towers])), 1)
        s["opt_freq"] = round(float(np.mean([t.freq_mhz for t in towers])), 1)
        s["opt_n"] = round(float(np.mean([t.path_loss_exp for t in towers])), 2)
        med = float(np.median([tower_radius_km(t, thr.usable_dbm) for t in towers]))
        s["opt_sep"] = float(min(max(round(0.5 * med, 2), 0.05), 5.0))
        s["nav"] = PAGE_MAP
    except Exception as exc:  # defensive: surface any unexpected failure to the user
        s["cfg_errors"] = [f"Unexpected error while analysing: {exc}"]


def _need_analysis():
    cfg = st.session_state.get("cfg")
    if cfg is None:
        st.warning("No analysis yet – configure your towers first.")
        st.button("Go to Tower Configuration →", on_click=goto, args=(PAGE_CONFIG,), type="primary")
    return cfg


def _pct(x: float) -> str:
    return f"{x:.1f}%"


def _render_map(map_obj, height: int = 680) -> None:
    ui.embed_html(map_obj.get_root().render(), height)


# ----------------------------------------------------------------------------- pages
def page_welcome() -> None:
    ui.embed_html(ui.HERO, 560)
    c1, c2, c3 = st.columns([1.4, 1, 1.4])
    c2.button("🚀  Enter SignalSight", type="primary", width="stretch", on_click=goto, args=(PAGE_CONFIG,))
    st.write("")
    cols = st.columns(4)
    cards = [("1 · Configure", "Choose how many towers you have, enter coordinates, frequency, EIRP and path-loss exponent."),
             ("2 · Visualise", "See per-tower footprints, a combined heatmap, overlaps and dead zones on OpenStreetMap."),
             ("3 · Optimise", "Tell us how many new towers you can build; greedy + local-search optimisation sites them."),
             ("4 · Compare", "Quantified before/after coverage, dead-zone reduction and downloadable report.")]
    for col, (h, t) in zip(cols, cards):
        col.markdown(f'<div class="card"><h4>{h}</h4><p>{t}</p></div>', unsafe_allow_html=True)


def page_configure() -> None:
    s = st.session_state
    st.title("⚙️ Tower configuration")
    st.caption("Define the existing network. Every value here drives the maps, optimiser and report.")

    c1, c2, c3, c4, c5 = st.columns(5)
    n = int(c1.number_input("Number of existing towers", 1, 25, step=1, key="n_towers"))
    c2.number_input("Default frequency (MHz)", *LIMITS["freq"], step=50.0, key="g_freq")
    c3.number_input("Default EIRP (dBm)", *LIMITS["eirp"], step=1.0, key="g_eirp")
    c4.number_input("Default path-loss exponent (n)", *LIMITS["n"], step=0.1, key="g_n",
                    help="2 = free space, ~3–3.5 suburban/urban, 3.5–5 dense urban.")
    c5.select_slider("Channel bandwidth (MHz)", options=[5.0, 10.0, 15.0, 20.0], key="g_bw", format_func=lambda v: f"{v:g}",
                     help="LTE carrier width. Signal strength (RSRP) is power per subcarrier, so total EIRP is shared over the carrier's subcarriers.")
    b1, b2, _ = st.columns([1.3, 1.6, 4])
    b1.button("Apply defaults to all", on_click=apply_globals)
    b2.button("Load 5-tower sample", on_click=load_sample)

    _ensure_tower_keys(n)
    st.subheader("Tower locations & transmission parameters")
    hdr = st.columns([1.3, 1.5, 1.5, 1, 1, 0.8])
    for h, t in zip(hdr, ["Name", "Latitude (°)", "Longitude (°)", "EIRP (dBm)", "Freq (MHz)", "Exponent n"]):
        h.markdown(f"**{t}**")
    for i in range(n):
        c = st.columns([1.3, 1.5, 1.5, 1, 1, 0.8])
        c[0].text_input("name", key=f"t{i}_name", label_visibility="collapsed")
        c[1].text_input("lat", key=f"t{i}_lat", label_visibility="collapsed", placeholder="e.g. 13.0827")
        c[2].text_input("lon", key=f"t{i}_lon", label_visibility="collapsed", placeholder="e.g. 80.2707")
        c[3].number_input("eirp", *LIMITS["eirp"], step=1.0, key=f"t{i}_eirp", label_visibility="collapsed")
        c[4].number_input("freq", *LIMITS["freq"], step=50.0, key=f"t{i}_freq", label_visibility="collapsed")
        c[5].number_input("n", *LIMITS["n"], step=0.1, key=f"t{i}_n", label_visibility="collapsed")

    st.subheader("Analysis region & signal classes")
    r1, r2 = st.columns(2)
    r1.slider("Region padding around the towers (km)", 0.5, 20.0, step=0.5, key="padding_km",
              help="The analysed rectangle is the towers' bounding box plus this margin.")
    r2.select_slider("Grid resolution (cells on the longer side)", options=[60, 80, 100, 120, 150], key="resolution",
                     help="Higher = finer maps, slower optimisation.")
    with st.expander("Signal thresholds (dBm)"):
        t1, t2, t3 = st.columns(3)
        t1.number_input("Strong ≥", -140.0, -40.0, step=1.0, key="thr_strong")
        t2.number_input("Usable ≥", -140.0, -40.0, step=1.0, key="thr_usable")
        t3.number_input("Weak ≥ (below = dead zone)", -140.0, -40.0, step=1.0, key="thr_weak")

    with st.expander("Land boundary (keeps towers off the sea)", expanded=True):
        st.checkbox("Analyse land only and place new towers on land", key="land_on",
                    help="Sea cells are left out of the coverage statistics and never receive a proposed tower. "
                         "The bundled India boundary is used unless you upload another one.")
        
    st.button("✅ Validate & run coverage analysis", type="primary", on_click=run_analysis)
    errs = s.get("cfg_errors") or []
    if errs:
        st.error(f"Please fix {len(errs)} problem(s) before continuing:")
        for e in errs:
            st.markdown(f"- ❌ {e}")
    elif "cfg" in s:
        st.success("Configuration valid – analysis stored. Open the Coverage Map from the sidebar.")
    for w in s.get("cfg_warnings") or []:
        st.warning(w)
    if s.get("land_info"):
        st.info(s["land_info"])


def page_map() -> None:
    cfg = _need_analysis()
    if cfg is None:
        return
    s = st.session_state
    sb, region, thr, towers = s["stats_before"], cfg["region"], cfg["thr"], cfg["towers"]
    st.title("🗺️ Interactive coverage map")
    ui.kpi_row([
        ui.kpi("Strong", _pct(sb["pct"]["Strong"]), f'{sb["km2"]["Strong"]:.2f} km²', CLASS_COLORS[3]),
        ui.kpi("Usable", _pct(sb["pct"]["Usable"]), f'{sb["km2"]["Usable"]:.2f} km²', CLASS_COLORS[2]),
        ui.kpi("Weak", _pct(sb["pct"]["Weak"]), f'{sb["km2"]["Weak"]:.2f} km²', CLASS_COLORS[1]),
        ui.kpi("Dead zone", _pct(sb["pct"]["Dead zone"]), f'{sb["km2"]["Dead zone"]:.2f} km²', CLASS_COLORS[0]),
        ui.kpi("Overlap ≥2 towers", _pct(sb["overlap2_pct"]), f'{sb["overlap2_km2"]:.2f} km²', "#FDB78F"),
    ])
    o1, o2 = st.columns([2, 1])
    opacity = o1.slider("Overlay opacity", 0.2, 1.0, 0.65, 0.05)
    foot = o2.checkbox("Show tower footprints", True)
    table = per_tower_table(towers, s["cov_before"], region)
    _render_map(build_map(towers, [], region, s["cov_before"], thr, table, opacity, foot))
    st.caption("Use the layer panel (top-right) to switch between the heatmap, class map, overlap map and problem areas. "
               "Click a tower for details, or anywhere for coordinates. Solid / dashed / dotted rings = strong / usable / weak radius.")
    ui.note("⚠️ <b>Prediction, not measurement.</b> Colours come from a log-distance path-loss model "
            "using your EIRP, frequency and exponent. Real coverage also depends on terrain, buildings, antennas and load.")
    with st.expander("Per-tower details", expanded=False):
        st.dataframe(table, width="stretch", hide_index=True)
    st.subheader("Areas requiring improvement")
    under = find_underserved_regions(s["cov_before"], region)
    if under.empty:
        st.success("No weak or dead-zone clusters found in this region.")
    else:
        st.dataframe(under, width="stretch", hide_index=True)
    st.button("Next: optimise tower placement →", type="primary", on_click=goto, args=(PAGE_OPT,))


def page_optimizer() -> None:
    cfg = _need_analysis()
    if cfg is None:
        return
    s = st.session_state
    region, thr, towers = cfg["region"], cfg["thr"], cfg["towers"]
    st.title("🎯 Intelligent placement optimizer")
    st.caption("Greedy facility-location selection over a candidate lattice, followed by swap-based local search.")

    c1, c2, c3, c4 = st.columns(4)
    k = int(c1.number_input("Additional towers available", 1, 30, step=1, key="opt_k"))
    c2.number_input("New-tower EIRP (dBm)", *LIMITS["eirp"], step=1.0, key="opt_eirp")
    c3.number_input("New-tower frequency (MHz)", *LIMITS["freq"], step=50.0, key="opt_freq")
    c4.number_input("New-tower exponent n", *LIMITS["n"], step=0.1, key="opt_n")
    d1, d2, d3 = st.columns(3)
    d1.number_input("Minimum site spacing (km)", 0.0, 20.0, step=0.05, key="opt_sep",
                    help="Keeps proposals apart from each other and from existing towers (relaxed automatically only if needed to place all K).")
    d2.slider("Overlap penalty", 0.0, 0.5, step=0.01, key="opt_pen",
              help="Penalises placing a tower where usable signal already exists.")
    d3.select_slider("Search density (candidate sites)", options=[250, 500, 800], key="opt_cand")

    if st.button("🎯 Run optimization", type="primary"):
        bar = st.progress(0.0, text="Starting…")
        try:
            res = optimize(towers, k, region, thr, float(s["opt_eirp"]), float(s["opt_freq"]), float(s["opt_n"]),
                           bw_mhz=towers[0].bw_mhz, land=cfg.get("land"), min_sep_km=float(s["opt_sep"]), overlap_penalty=float(s["opt_pen"]),
                           max_candidates=int(s["opt_cand"]),
                           progress=lambda f, m: bar.progress(min(max(f, 0.0), 1.0), text=m))
            s["opt"] = res
        except Exception as exc:
            st.error(f"Optimization failed: {exc}")
        finally:
            bar.empty()

    res = s.get("opt")
    if res is None:
        st.info("Set the number of new towers and run the optimizer to see recommended sites and predicted improvement.")
        return
    if len(res.proposed) < res.requested:
        st.warning(f"Only {len(res.proposed)} of {res.requested} towers could be placed – the region has no more feasible sites.")
    elif res.effective_sep_km < res.min_sep_km:
        st.info(f"Minimum spacing was relaxed from {res.min_sep_km:g} km to {res.effective_sep_km:.3f} km to place all {res.requested} towers.")

    sb, sa = res.stats_before, res.stats_after
    d0, d1 = sb["km2"]["Dead zone"], sa["km2"]["Dead zone"]
    m = st.columns(4)
    m[0].metric("Dead zone", _pct(sa["pct"]["Dead zone"]), f'{sa["pct"]["Dead zone"] - sb["pct"]["Dead zone"]:+.1f} pp', delta_color="inverse")
    m[1].metric("Covered (usable+)", _pct(sa["covered_pct"]), f'{sa["covered_pct"] - sb["covered_pct"]:+.1f} pp')
    m[2].metric("Strong", _pct(sa["pct"]["Strong"]), f'{sa["pct"]["Strong"] - sb["pct"]["Strong"]:+.1f} pp')
    m[3].metric("Dead-zone area removed", f"{d0 - d1:.2f} km²", f'{(1 - d1 / d0) * 100 if d0 > 0 else 0:.0f}% of dead area')

    all_t = towers + res.proposed
    tab_after = per_tower_table(all_t, res.cov_after, region)
    t1, t2, t3 = st.tabs(["Predicted coverage AFTER", "Current coverage BEFORE", "Before vs after"])
    with t1:
        _render_map(build_map(towers, res.proposed, region, res.cov_after, thr, tab_after))
        st.caption("★ orange stars = proposed towers; dark blue circles = existing towers. Predicted by the same propagation model.")
    with t2:
        _render_map(build_map(towers, [], region, res.cov_before, thr, per_tower_table(towers, res.cov_before, region)))
    with t3:
        _compare_block(sb, sa)
    st.subheader("Recommended tower coordinates")
    st.dataframe(res.proposals, width="stretch", hide_index=True)
    st.button("Next: full analysis report →", type="primary", on_click=goto, args=(PAGE_REPORT,))


def _compare_block(sb: dict, sa: dict) -> None:
    df = pd.DataFrame({"Before (%)": [sb["pct"][c] for c in reversed(CLASS_NAMES)],
                       "After (%)": [sa["pct"][c] for c in reversed(CLASS_NAMES)]}, index=list(reversed(CLASS_NAMES)))
    st.bar_chart(df, color=["#605D5B", "#FA5F05"])
    rows = [("Strong (%)", sb["pct"]["Strong"], sa["pct"]["Strong"]), ("Usable (%)", sb["pct"]["Usable"], sa["pct"]["Usable"]),
            ("Weak (%)", sb["pct"]["Weak"], sa["pct"]["Weak"]), ("Dead zone (%)", sb["pct"]["Dead zone"], sa["pct"]["Dead zone"]),
            ("Covered, usable+ (%)", sb["covered_pct"], sa["covered_pct"]),
            ("Dead-zone area (km²)", sb["km2"]["Dead zone"], sa["km2"]["Dead zone"]),
            ("Overlap ≥2 towers (%)", sb["overlap2_pct"], sa["overlap2_pct"]),
            ("Overlap ≥3 towers (%)", sb["overlap3_pct"], sa["overlap3_pct"]),
            ("Mean best-server signal (dBm)", sb["mean_rsrp"], sa["mean_rsrp"])]
    st.dataframe(pd.DataFrame([{"Metric": n, "Before": round(b, 2), "After": round(a, 2), "Change": round(a - b, 2)}
                               for n, b, a in rows]), width="stretch", hide_index=True)


def page_report() -> None:
    cfg = _need_analysis()
    if cfg is None:
        return
    s = st.session_state
    region, thr, towers = cfg["region"], cfg["thr"], cfg["towers"]
    sb, res = s["stats_before"], s.get("opt")
    sa = res.stats_after if res else None
    st.title("📊 Analysis & results")
    ui.note("⚠️ <b>Mathematical prediction vs measured coverage:</b> every figure below is computed from a log-distance "
            "propagation model and your inputs. It is a planning estimate – verify with drive tests / operator data.")

    st.subheader("1 · Scope")
    ui.kpi_row([
        ui.kpi("Area analysed", f'{sb["area_km2"]:.1f} km²', "land only" if sb["land_only"] else f"{region.width_km:.1f} × {region.height_km:.1f} km"),
        ui.kpi("Existing towers", str(len(towers))),
        ui.kpi("Proposed towers", str(len(res.proposed)) if res else "–", "run optimizer" if not res else "", "#FA5F05"),
        ui.kpi("Grid", f"{region.nx}×{region.ny}", f"{region.cell_area_km2 * 1e6:,.0f} m² / cell"),
    ])
    if not res:
        st.info("Run the optimizer to add the after-optimisation comparison to this report.")
        st.button("Go to optimizer →", on_click=goto, args=(PAGE_OPT,))

    st.subheader("2 · Coverage classes")
    if res:
        _compare_block(sb, sa)
        d0, d1 = sb["km2"]["Dead zone"], sa["km2"]["Dead zone"]
        ui.kpi_row([
            ui.kpi("Dead-zone reduction", f"{(1 - d1 / d0) * 100 if d0 > 0 else 0:.1f}%", f"{d0:.2f} → {d1:.2f} km²", "#e8808a"),
            ui.kpi("Coverage gain", f'{sa["covered_pct"] - sb["covered_pct"]:+.1f} pp', f'{sb["covered_pct"]:.1f}% → {sa["covered_pct"]:.1f}%', "#6fc7b0"),
            ui.kpi("Signal gain", f'{sa["mean_rsrp"] - sb["mean_rsrp"]:+.1f} dB', "mean best-server power", "#FDB78F"),
        ])
    else:
        st.dataframe(pd.DataFrame({"Class": list(reversed(CLASS_NAMES)),
                                   "Area (%)": [round(sb["pct"][c], 2) for c in reversed(CLASS_NAMES)],
                                   "Area (km²)": [round(sb["km2"][c], 3) for c in reversed(CLASS_NAMES)]}),
                     width="stretch", hide_index=True)

    st.subheader("3 · Coverage overlap analysis")
    hist = pd.DataFrame({"Before (%)": sb["serving_hist"]}) if not res else pd.DataFrame(
        {"Before (%)": sb["serving_hist"], "After (%)": sa["serving_hist"]})
    st.bar_chart(hist)
    st.caption(f"Towers serving each cell at or above the usable threshold. Redundant coverage (≥2 towers) is "
               f'{sb["redundancy_of_covered_pct"]:.1f}% of covered area before'
               + (f' and {sa["redundancy_of_covered_pct"]:.1f}% after.' if res else "."))
    st.dataframe(per_tower_table(towers + (res.proposed if res else []), (res.cov_after if res else s["cov_before"]), region),
                 width="stretch", hide_index=True)

    st.subheader("4 · Areas requiring improvement")
    ub = find_underserved_regions(s["cov_before"], region)
    st.markdown("**Before optimisation**")
    if ub.empty:
        st.success("None – no weak or dead cells.")
    else:
        st.dataframe(ub, width="stretch", hide_index=True)
    ua = None
    if res:
        ua = find_underserved_regions(res.cov_after, region)
        st.markdown("**Remaining after optimisation**")
        if ua.empty:
            st.success("None – no weak or dead cells remain.")
        else:
            st.dataframe(ua, width="stretch", hide_index=True)

    if res:
        st.subheader("5 · Recommended tower coordinates")
        st.dataframe(res.proposals, width="stretch", hide_index=True)
        st.caption(f"{res.n_candidates} candidate sites evaluated · {res.swaps} local-search swap(s) · "
                   f"spacing used {res.effective_sep_km:.3f} km. Coordinates are cell centres of the analysis grid.")
        d1c, d2c = st.columns(2)
        d1c.download_button("⬇️ Recommended towers (CSV)", res.proposals.to_csv(index=False), "signalsight_proposed_towers.csv", "text/csv")
        d2c.download_button("⬇️ Full report (Markdown)", build_markdown_report(cfg, sb, sa, res, ub, ua),
                            "signalsight_report.md", "text/markdown")
    with st.expander("Methodology & limitations"):
        st.markdown(
            "- **Propagation:** `P_rx = EIRP − 10·log10(60·BW_MHz) − PL(d)`, with `PL = FSPL(d)` up to 100 m and `FSPL(100 m) + 10·n·log10(d/100 m)` beyond (10 m near-field clamp). The subcarrier term makes the result RSRP-like.\n"
            "- **Best server:** each cell takes the strongest tower; *overlap* counts towers above the usable threshold.\n"
            "- **Optimiser:** maximises Σ utility(best-server power) with an overlap penalty – greedy selection then swap local search.\n"
            "- **Not modelled:** terrain, clutter, building loss, antenna patterns/tilt, interference, capacity/traffic, shadowing.\n"
            "- **Use:** relative comparison and shortlisting of sites, not guaranteed field performance.")
