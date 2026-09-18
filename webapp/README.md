# React frontend (prototype)

A second presentation layer for the same subsystem models, in progress on `feat/react-frontend`.
The graded submission is unaffected — `app/` (Streamlit) still runs standalone and is what was
scored. Nothing about the models changes here; this only changes how results are displayed.

Only **Rail Corrugation** is wired up so far, as a proof of the split before porting Door, ACV
and SHM the same way. It carries over every honesty/reliability fix from the Streamlit app:
the score-mismatch footnote (held-out vs cross-validation), the verdict/severity/confidence
panel, the "How reliable is this?" panel sourced from `app/reliability.py`, the stationary-Rail
"Inconclusive" display (while the submitted CSV still says "Normal"), and the malformed-file
rejection (wrong column count → a clear error, not a confident-looking wrong answer).

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

- `backend/main.py` — FastAPI. Imports `subsystems/rail_corrugation` and `app/reliability.py`
  directly (same functions the Streamlit page calls), adds `/api/rail/predict`,
  `/api/rail/sample`, `/api/rail/meta`. Malformed uploads get a 422 with the same message
  `subsystems/rail_corrugation/features.py::load_raw_file` already raises.
- `frontend/src/theme.css`, `theme.js` — palette and tier-colour mapping ported from
  `app/theme.py`'s `DARK` dict and `TIER_COLOR`.
- `frontend/src/components/` — `Verdict`, `ReliabilityPanel`, `Panel`, `Metrics`, `DataTable`
  mirror `app/theme.py`'s `verdict`/`reliability_panel`/`panel`/`metrics`/`table` helpers, same
  data shape, so a page's props are close to a straight port from the Streamlit call site.
- `frontend/src/pages/RailPage.jsx` — the only page so far; the shape to copy for Door/ACV/SHM.

## Not done yet

- Door, ACV, SHM pages and endpoints (same pattern as Rail).
- Sidebar shell, routing, batch mode, session zip, dark/light toggle — Rail is a single static
  page right now, no navigation.
- Single-service deploy (FastAPI serving the built React bundle) — currently two dev processes.
