# The app (submission item 3)

**Live: <https://gamora-cdm-307993205824.asia-southeast1.run.app/>**

The submitted app for all four subsystems (Door, ACV, Rail Corrugation, SHM): a FastAPI backend
wrapping the `subsystems/*` predict functions and a React frontend, shipped as one container.
It replaced the earlier Streamlit app in `app/` as the submission; the models, the submitted
predictions and the validation layer are unchanged, and this only changes how results are
presented.

Every page gives a plain-language verdict first (what was found, how urgent — no action needed,
monitor, or inspect before next service — how sure the model is, and why), the "How reliable is
this?" note sourced from `app/reliability.py`, then metrics, charts and evidence, and a download
in the exact submission schema. Malformed or wrong-subsystem files are rejected (a 422 with a
clear reason, never a confident-looking wrong answer) at the same validation layer the models use
(`subsystems/*/features.py`, `subsystems/*/loader.py`). Rail shows the held-out-vs-cross-
validation footnote and displays a stationary train as "Inconclusive" (the submitted CSV still
says "Normal").

Beyond single-file scoring: batch upload per subsystem (a triage table plus one combined CSV),
a per-subsystem run history (rename, re-view, re-download), Saved results (this browser only),
team notes on a file (stored server-side in `backend/notes.db`), inline glossary tooltips on
technical terms, and an "Under the hood" page with each model's method, scoring and reliability.

## Run it

```bash
# backend — from the repo root
pip install -r requirements.txt -r webapp/backend/requirements.txt
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

- **ACV's cabin-temperature chart** shows the top-ranked car against a shaded min/max band of the
  other cars (or against one chosen car), not all 8 lines at once — plain SVG, no charting
  library.
- **No dark/light toggle and no session-wide `predictions.zip`** — downloads are per page (one
  file) or per batch (one combined CSV).
- A couple of malformed-file error messages (e.g. an `.xlsx` dropped on a CSV page) come through
  as the raw parser message rather than a hand-written one — the file is still rejected with a
  422, just less politely worded.

## Deploying (Cloud Run or anywhere Docker runs)

```bash
docker build -t gamora-cdm .
docker run -p 8080:8080 gamora-cdm
```

One image: a Node stage builds the React app, then a Python stage installs `requirements.txt` +
`webapp/backend/requirements.txt` and serves the built frontend alongside the API from a single
`uvicorn` process (`webapp/backend/main.py`'s `FRONTEND_DIST` block — mounts `/assets`, falls
back to `index.html` for any other path so client-side view-switching survives a refresh). No
separate frontend host, no CORS. Verified locally end-to-end (API, static assets, SPA fallback,
and a real browser click-through of a sample) before writing this down.

Cloud Run (the live URL above is this service, region `asia-southeast1`): `gcloud run deploy gamora-cdm --source . --allow-unauthenticated --memory 1Gi` — 1Gi
because pandas/numpy/scikit-learn plus an xlsx parse (ACV, ~7s) need more than the 512Mi default.
Cloud Run scales to zero by default, so `subsystems/rail_corrugation/predict.py`'s retrain-on-
cold-start fallback (a couple of seconds) will fire on the first request after an idle period —
not a bug, just worth knowing if a demo's first click looks slow.

## Not done yet

- Deep links / URL routing (`?view=`) — the sidebar is local state, so a shared link always
  lands on "Get started," not the specific subsystem/result someone meant to share.
