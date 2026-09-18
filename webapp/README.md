# React frontend (prototype)

A second presentation layer for the same subsystem models, in progress on `feat/react-frontend`.
The graded submission is unaffected — `app/` (Streamlit) still runs standalone and is what was
scored. Nothing about the models changes here; this only changes how results are displayed.

All four subsystems (Door, ACV, Rail Corrugation, SHM) are wired up with a sidebar to switch
between them. Every page carries over the honesty/reliability fixes from the Streamlit app:
the verdict/severity/confidence panel, the "How reliable is this?" panel sourced from
`app/reliability.py`, and malformed-file rejection (a 422 with a clear reason, never a
confident-looking wrong answer) at the same validation layer the Streamlit app uses
(`subsystems/*/features.py`, `subsystems/*/loader.py`). Rail additionally shows the
held-out-vs-cross-validation score footnote and the stationary-train "Inconclusive" display
(while the submitted CSV still says "Normal").

## Run it

```bash
# backend — from the repo root
uvicorn webapp.backend.main:app --reload --port 8000

# frontend — in another terminal
cd webapp/frontend
npm install   # first time only
npm run dev   # http://localhost:5173, proxies /api to :8000
```

## Layout

- `backend/main.py` — FastAPI. Imports `subsystems/<name>` and `app/reliability.py` directly
  (the same functions each Streamlit page calls) — never `app/inference/*.py` itself, so the
  backend has no dependency on Streamlit at all. One `build_<name>_result()` per subsystem
  reimplements that page's verdict/evidence text and returns it as JSON instead of rendering
  it; `/api/<name>/predict` (upload), `/api/<name>/sample` (bundled sample), `/api/<name>/meta`.
- `frontend/src/theme.css`, `theme.js` — palette and tier-colour mapping ported from
  `app/theme.py`'s `DARK` dict and `TIER_COLOR`.
- `frontend/src/components/` — `Verdict`, `ReliabilityPanel`, `Panel`, `Metrics`, `DataTable`
  mirror `app/theme.py`'s `verdict`/`reliability_panel`/`panel`/`metrics`/`table` helpers, same
  data shape. Chart components (`DoorChart`, `GapChart`, `StressChart`, `HistogramChart`,
  `ChannelChart`) are plain SVG/div, not a charting library — see "Known simplifications".
- `frontend/src/pages/{Door,Acv,Rail,Shm}Page.jsx` — one page per subsystem, all following the
  same fetch → verdict → reliability → metrics → chart → table → download shape.
- `frontend/src/App.jsx` — sidebar nav switching between the four pages (local state, no router).

## Known simplifications vs. the Streamlit app

- **ACV's cabin-temperature chart** shows the top-ranked car's line against a shaded min/max
  band of the other cars, not one line per car (the Streamlit version overlays all 8) — a
  deliberate simplification to avoid pulling in a charting library for the prototype.
- **No batch mode, session results zip, or dark/light toggle** — every page runs one file at a
  time; `Download CSV` builds the file client-side per page rather than a combined submission
  zip.
- A couple of malformed-file error messages (notably ACV's, via pandas/openpyxl) are more raw
  than the Streamlit app's hand-written ones — they still correctly reject the file with a 422,
  just less politely worded.

## Not done yet

- Deep links / URL routing (`?view=`), single-service deploy (FastAPI serving the built React
  bundle instead of two dev processes).
