# 📡 SignalSight – Intelligent Cellular Tower Placement & Coverage Optimization

Python + Streamlit + OpenStreetMap (Folium). All results are calculated from your inputs – nothing is hard-coded or random.
Dark theme in the Vivid Orange / Onyx / Dark Azure palette, an animated tower-and-signal welcome page and slow, smooth page transitions.

## Run it (no command line needed)
1. Unzip the folder.
2. **Windows:** double-click `run_app.bat`  ·  **Mac/Linux:** double-click / run `run_app.sh`
   (installs the packages, then opens the app in your browser).

### Or from VS Code
1. File ▸ Open Folder… ▸ select `SignalSight`.
2. Terminal ▸ New Terminal.
3. Run `pip install -r requirements.txt`, then `streamlit run app.py`.

Internet is required in the browser for the OpenStreetMap tiles (and the Manrope web font; a system font is used offline).

## Workflow
Welcome → **Tower Configuration** (count, lat/lon, frequency, EIRP, path-loss exponent, bandwidth, validation) →
**Coverage Map** (heatmap, classes, overlap, footprints, dead zones) →
**Placement Optimizer** (exactly K new towers, before/after maps) → **Analysis & Report** (CSV + Markdown download).

## Model & algorithm
* Path loss (log-distance, 100 m reference): `PL = FSPL(d)` for d ≤ 100 m, else `FSPL(100 m) + 10·n·log10(d / 100 m)`,
  with `FSPL(d) = 20·log10(f_MHz) + 20·log10(d_km) + 32.44` and a 10 m near-field clamp.
* Received power: `P_rx = EIRP − 10·log10(60·BW_MHz) − PL(d)`. The middle term spreads the total EIRP over the carrier's
  subcarriers (12 per resource block, 5 blocks per MHz) because RSRP – and the thresholds below – are per subcarrier.
* Classes (editable): Strong ≥ −85 dBm, Usable ≥ −100, Weak ≥ −110, Dead < −110.
* Best-server map + overlap count (towers ≥ usable) per grid cell.
* Optimizer: greedy facility-location over a candidate lattice (utility = class score + continuous signal term,
  minus an overlap penalty), then swap-based local search. The un-penalised utility is monotone submodular (greedy has a
  1 − 1/e guarantee); the overlap penalty removes that guarantee, so treat the result as a strong heuristic.
  Minimum spacing is enforced and only relaxed if needed to place all K.

## What changed in this version
* Theme: orange / onyx / dark-azure palette (`.streamlit/config.toml` and `signalsight/ui.py`). The welcome page now shows a tower whose signal
  rings and arcs pulse, data packets travelling to devices, breathing coverage zones and a filling signal meter (pure CSS/SVG, works offline).
* Overlap fixes: page content now starts below Streamlit's fixed top bar; map legend sits clear of the scale bar, scrolls instead of
  growing past the map, and shrinks on narrow maps; the layer panel is size-limited; input labels wrap instead of running into the next column;
  welcome cards share one row height; extra bottom padding so the last element is never cut off.
* Model: per-subcarrier (RSRP) power and a 100 m reference distance replace the earlier total-EIRP / 1 m-anchor mix.
* Report: all tables are real Markdown (no `tabulate` needed); empty-area messages are accurate (small clusters are no longer dropped).
* Validation: coordinates that look swapped (latitude > 60° with a small longitude) now raise a warning.
* Inputs on the Configuration and Optimizer pages are kept when you move between pages.
* Map/hero embedding falls back automatically between `components.html` and `st.iframe`.
* Unused import / variable and statement-style ternaries cleaned up.

## Land mask (towers stay off the sea)
* The analysis box is a rectangle, so near a coast part of it is water. A NumPy point-in-polygon test (`land.py`) marks each
  grid cell as land or sea using a bundled, simplified India boundary (`data/india_land.geojson`, ~450 m tolerance).
* Sea cells are ignored in all statistics, left transparent on the maps, and never receive a proposed tower.
* Switch it off on the Configuration page, or upload a GeoJSON boundary for another country or area.
* The boundary is simplified, so towers can fall within a few hundred metres of the true coastline. Lakes and rivers are not removed.

## Code layout
`app.py` (navigation) · `signalsight/models.py` · `propagation.py` · `coverage.py` · `optimizer.py` ·
`mapping.py` · `land.py` · `validation.py` · `report.py` · `ui.py` · `views.py`

## Limits (stated in the app too)
Predictions only – no terrain, buildings, antenna patterns, interference or traffic. Validate with drive tests.
