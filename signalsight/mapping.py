"""Folium / OpenStreetMap map construction with raster overlays and legends."""
from __future__ import annotations

import base64
import html as _html
import io
from typing import Sequence

import folium
import numpy as np
import pandas as pd
from folium import plugins
from PIL import Image
from scipy import ndimage

from .coverage import Coverage
from .models import CLASS_COLORS, Region, Thresholds, Tower
from .propagation import tower_radius_km

_RSRP_STOPS = [-125, -110, -100, -90, -80, -65]
_RSRP_COLS = np.array([(196, 96, 116), (232, 128, 138), (245, 179, 131), (244, 224, 140), (130, 208, 170), (80, 170, 165)], float)
_OVERLAP_COLS = {1: (107, 124, 136), 2: (253, 183, 143), 3: (250, 95, 5), 4: (188, 71, 4)}  # azure -> peach -> orange -> deep orange


def _hex_rgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _heat_rgba(power: np.ndarray) -> np.ndarray:
    p = np.clip(power, _RSRP_STOPS[0], _RSRP_STOPS[-1])
    rgba = np.zeros(p.shape + (4,), np.uint8)
    for c in range(3):
        rgba[..., c] = np.interp(p, _RSRP_STOPS, _RSRP_COLS[:, c]).astype(np.uint8)
    rgba[..., 3] = 255
    return rgba


def _class_rgba(classes: np.ndarray) -> np.ndarray:
    rgba = np.zeros(classes.shape + (4,), np.uint8)
    for i, col in enumerate(CLASS_COLORS):
        rgba[classes == i, :3] = _hex_rgb(col)
    rgba[..., 3] = 255
    return rgba


def _overlap_rgba(ns: np.ndarray) -> np.ndarray:
    rgba = np.zeros(ns.shape + (4,), np.uint8)
    for k, col in _OVERLAP_COLS.items():
        sel = (ns == k) if k < 4 else (ns >= 4)
        rgba[sel, :3] = col
        rgba[sel, 3] = 255
    return rgba


def _overlay(rgba: np.ndarray, region: Region, name: str, opacity: float, show: bool) -> folium.raster_layers.ImageOverlay:
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG")
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return folium.raster_layers.ImageOverlay(
        image=uri, bounds=region.bounds, opacity=opacity, name=name, show=show, interactive=False, zindex=3)


def _tower_icon(label: str, proposed: bool) -> folium.DivIcon:
    if proposed:
        html = (
            '<div style="width:40px;height:40px;background:#FA5F05;display:flex;align-items:center;'
            'justify-content:center;color:#0B0C0D;font:800 11px sans-serif;filter:drop-shadow(0 2px 3px rgba(0,0,0,.7));'
            'clip-path:polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%)">'
            f'<span style="margin-top:6px">{label}</span></div>')
        return folium.DivIcon(html=html, icon_size=(40, 40), icon_anchor=(20, 20))
    html = (
        '<div style="width:30px;height:30px;border-radius:50%;background:#333F48;border:3px solid #fff;'
        'box-shadow:0 0 0 3px rgba(250,95,5,.55),0 2px 6px rgba(0,0,0,.6);color:#fff;font:700 11px sans-serif;'
        f'display:flex;align-items:center;justify-content:center">{label}</div>')
    return folium.DivIcon(html=html, icon_size=(30, 30), icon_anchor=(15, 15))


def _legend(thr: Thresholds, has_proposed: bool, land_only: bool = False) -> str:
    rows = ""
    labels = [f"Strong ≥ {thr.strong_dbm:g} dBm", f"Usable ≥ {thr.usable_dbm:g} dBm",
              f"Weak ≥ {thr.weak_dbm:g} dBm", f"Dead zone < {thr.weak_dbm:g} dBm"]
    for col, lab in zip(reversed(CLASS_COLORS), labels):
        rows += f'<div><span style="background:{col}"></span>{lab}</div>'
    ov = "".join(f'<span style="background:rgb{c};width:12px;height:12px;display:inline-block;margin-right:3px;'
                 f'border-radius:2px"></span>' for c in _OVERLAP_COLS.values())
    prop = ('<div><span style="background:#FA5F05;border-radius:2px"></span>Proposed tower ★</div>'
            if has_proposed else "")
    sea = ('<div style="margin-top:5px;font-size:11px">Sea / outside boundary: not analysed</div>' if land_only else "")
    return f"""
    <style>
    .ss-legend{{position:fixed;bottom:38px;left:12px;z-index:9999;background:rgba(11,12,13,.92);color:#F6F6F6;
    font:12px/1.5 sans-serif;padding:10px 12px;border-radius:12px;border:1px solid rgba(246,246,246,.16);
    box-shadow:0 8px 24px rgba(0,0,0,.45);max-width:236px;max-height:calc(100vh - 60px);overflow:auto}}
    .ss-legend b{{display:block;margin-bottom:3px;color:#FA5F05}}
    .ss-legend span.k,.ss-legend div>span{{display:inline-block;width:14px;height:14px;margin-right:7px;
    vertical-align:-2px;border-radius:50%}}
    .ss-legend .ss-note{{margin-top:6px;font-size:10.5px;color:#A9A5A2}}
    .leaflet-control-layers{{max-width:min(340px,58vw);max-height:calc(100vh - 120px);overflow:auto;border-radius:12px!important}}
    .leaflet-control-layers-list{{font:12px/1.5 sans-serif}}
    @media (max-width:640px){{.ss-legend{{max-width:150px;padding:8px 9px;font-size:11px}}.ss-more{{display:none}}
    .leaflet-control-layers{{max-width:46vw}}}}
    </style>
    <div class="ss-legend"><b>Predicted signal (best server)</b>{rows}
    <div style="margin-top:5px"><span style="background:#333F48;box-shadow:0 0 0 2px rgba(250,95,5,.7)"></span>Existing tower</div>{prop}
    <div class="ss-more"><div style="margin-top:5px;font-size:11px">Overlap layer (1→4+ towers):<br>{ov}</div>
    {sea}<div class="ss-note">Model prediction, not measured coverage.</div></div></div>"""


def build_map(
    existing: Sequence[Tower],
    proposed: Sequence[Tower],
    region: Region,
    cov: Coverage,
    thr: Thresholds,
    table: pd.DataFrame | None = None,
    opacity: float = 0.65,
    show_footprints: bool = True,
) -> folium.Map:
    m = folium.Map(location=[region.lat0, region.lon0], zoom_start=13, tiles="OpenStreetMap",
                   control_scale=True, max_zoom=19, prefer_canvas=True)
    m.fit_bounds(region.bounds)

    smooth = ndimage.zoom(cov.best, 4, order=1)
    up = lambda a: np.repeat(np.repeat(a, 4, axis=0), 4, axis=1)
    sea4 = None if cov.land is None else ~up(cov.land)

    def clear_sea(rgba):  # sea cells stay transparent so the OpenStreetMap water shows through
        if sea4 is not None:
            rgba = rgba.copy()
            rgba[sea4, 3] = 0
        return rgba
    _overlay(clear_sea(_heat_rgba(smooth)), region, "Signal heatmap (best server)", opacity, True).add_to(m)
    _overlay(clear_sea(_class_rgba(up(cov.classes))), region, "Coverage classes", opacity, False).add_to(m)
    _overlay(clear_sea(_overlap_rgba(up(cov.n_serving))), region, "Overlapping coverage", opacity, False).add_to(m)
    dead = np.zeros(cov.classes.shape + (4,), np.uint8)
    dead[cov.classes == 0] = (232, 128, 138, 255)
    dead[cov.classes == 1] = (245, 179, 131, 255)
    _overlay(clear_sea(up(dead)), region, "Problem areas (dead + weak)", min(opacity + 0.15, 1.0), False).add_to(m)

    folium.Rectangle(region.bounds, color="#605D5B", weight=2, dash_array="6 6", fill=False,
                     tooltip="Analysed region").add_to(m)

    towers = list(existing) + list(proposed)
    fp = folium.FeatureGroup(name="Tower footprints", show=show_footprints)
    mk = folium.FeatureGroup(name="Towers", show=True)
    tab = table.set_index("Tower") if table is not None and not table.empty else None
    for i, t in enumerate(towers):
        col = "#FA5F05" if t.proposed else "#333F48"
        for thr_dbm, w, dash in ((thr.strong_dbm, 2.5, None), (thr.usable_dbm, 2, "6 4"), (thr.weak_dbm, 1.5, "2 6")):
            r = tower_radius_km(t, thr_dbm) * 1000
            if r > 0:
                folium.Circle([t.lat, t.lon], radius=r, color=col, weight=w, dash_array=dash,
                              fill=False, opacity=0.9).add_to(fp)
        label = ("P" if t.proposed else "T") + str(len([x for x in towers[:i + 1] if x.proposed == t.proposed]))
        extra = ""
        if tab is not None and t.name in tab.index:
            row = tab.loc[t.name]
            extra = (f"<tr><td>Best-server area</td><td>{row['Best-server area (km²)']} km²</td></tr>"
                     f"<tr><td>Usable footprint</td><td>{row['Usable footprint in region (km²)']} km²</td></tr>"
                     f"<tr><td>Overlapped footprint</td><td>{row['Overlapped footprint (km²)']} km²</td></tr>")
        popup = folium.Popup(
            f"<div style='font:13px sans-serif;min-width:230px'><b>{_html.escape(t.name)}</b> "
            f"<span style='color:{col};font-weight:700'>({'proposed' if t.proposed else 'existing'})</span>"
            f"<table style='width:100%;font-size:12px'>"
            f"<tr><td>Latitude</td><td>{t.lat:.6f}</td></tr><tr><td>Longitude</td><td>{t.lon:.6f}</td></tr>"
            f"<tr><td>EIRP</td><td>{t.eirp_dbm:g} dBm</td></tr><tr><td>Frequency</td><td>{t.freq_mhz:g} MHz</td></tr><tr><td>Bandwidth</td><td>{t.bw_mhz:g} MHz</td></tr>"
            f"<tr><td>Path-loss exponent</td><td>{t.path_loss_exp:g}</td></tr>"
            f"<tr><td>Strong radius</td><td>{tower_radius_km(t, thr.strong_dbm):.2f} km</td></tr>"
            f"<tr><td>Usable radius</td><td>{tower_radius_km(t, thr.usable_dbm):.2f} km</td></tr>"
            f"<tr><td>Weak radius</td><td>{tower_radius_km(t, thr.weak_dbm):.2f} km</td></tr>"
            f"{extra}</table><i style='font-size:11px;color:#666'>Predicted by log-distance model</i></div>",
            max_width=300)
        folium.Marker([t.lat, t.lon], icon=_tower_icon(label, t.proposed), popup=popup,
                      tooltip=f"{_html.escape(t.name)}: {t.eirp_dbm:g} dBm @ {t.freq_mhz:g} MHz").add_to(mk)
    fp.add_to(m)
    mk.add_to(m)

    folium.LatLngPopup().add_to(m)
    plugins.Fullscreen().add_to(m)
    plugins.MousePosition(position="bottomright", num_digits=5).add_to(m)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    m.get_root().html.add_child(folium.Element(_legend(thr, bool(proposed), cov.land is not None)))
    return m
