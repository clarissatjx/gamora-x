# gamora-x — NebulaX Hackathon PS3: Train Condition Monitoring

Four condition-monitoring models for rail vehicles behind one web app, built for
[NebulaX PS3](references/PS3_Problem_Statement.md). Upload a raw sensor file, get the
prediction on screen with the evidence behind it, download the submission CSV.

**Live app: <https://gamora-cdm-307993205824.asia-southeast1.run.app/>**

| Subsystem | Task | Metric | Held-out score |
|---|---|---|---|
| Door | segment a continuous motor-current stream into cycles, flag abnormal resistance | IoU-weighted F1 | **1.000** |
| ACV | rank 8 cars by likelihood of a refrigerant leak | rank-decay | **1.000** |
| Rail Corrugation | classify a 1 s axle-box recording: Normal / Side I / Side II | macro F1 | 0.888 |
| SHM | cumulative fatigue damage from a dynamic-stress series | 1 − MAPE | 0.974 |
| **Overall** | | mean of four | **0.9655** |

## Submission contents (this repository is the submission)

| Spec item | Where |
|---|---|
| 1. Demo video | `demo_video.mp4` at the repo root |
| 2. `predictions.zip` | at the repo root — four `*_predictions.csv`, flat; rebuilt by `scripts/validate_submission.py --zip` |
| 3. The app | the web app in [`webapp/`](webapp/) (FastAPI + React), live at <https://gamora-cdm-307993205824.asia-southeast1.run.app/> — see [`webapp/README.md`](webapp/README.md); models live in [`subsystems/`](subsystems/) |
| Optional: write-up | `Optional_Items/write_up.md` |
| Optional: code and models | `Optional_Items/<Door \| ACV \| Rail Corrugation \| SHM>/{code,model}` — copies of `subsystems/`, rebuilt by `scripts/package_submission.py` |

## Run the app

The submitted app is the web app in [`webapp/`](webapp/): a FastAPI backend that calls the
`subsystems/*` predict functions directly, and a React frontend. Nothing to install to try it —
it is deployed at **<https://gamora-cdm-307993205824.asia-southeast1.run.app/>**.

Locally:

```bash
pip install -r requirements.txt -r webapp/backend/requirements.txt
uvicorn webapp.backend.main:app --reload --port 8000   # backend, from the repo root
cd webapp/frontend && npm install && npm run dev        # frontend, http://localhost:5173
```

or as the same single container that is deployed (`docker build -t gamora-cdm . && docker run -p
8080:8080 gamora-cdm`, then <http://localhost:8080>).

The app opens on **Get started**: pick a subsystem tile and upload straight from it, or open a
subsystem from the sidebar. Every page follows the same flow: drop a file (or **Try the
sample**) → plain-English verdict with urgency, confidence and reasoning → metrics → charts and
evidence → **Download CSV** in the exact submission schema. Each page also has **Batch upload**
(several files triaged into one table, one combined CSV), a per-subsystem run history (the **›**
next to each subsystem — rename, re-view, re-download), **Saved** results, and team notes on a
file. **Under the hood** explains each model, how it is scored and how reliable it is. Wrong or
malformed files are rejected with a plain reason rather than a confident-looking wrong answer.

The bundled samples (`app/samples/`) are held-out test files:

```
Test.csv             Door   38 cycles, 8 flagged abnormal
acv_test_case.xlsx   ACV    car 01 ranked most likely faulty
Test33.csv           Rail   Side I, 46 km/h
test02.csv           SHM    damage 0.8276
```

The raw datasets are not in the repo (`data/` is gitignored); mirror the organisers'
`02_Datasets/` layout into `data/`.

### The Streamlit app (earlier frontend)

[`app/`](app/) holds the first frontend, a Streamlit app over the same models
(`streamlit run app/app.py`). It is kept because the web app's backend reuses
`app/reliability.py` (the sourced reliability text) and `app/samples/`, and it still runs
standalone, but the web app is the one submitted and shown in the demo video.

## Test

```bash
python -m subsystems.door.scoring        # official Door metric, four reference checks
python -m subsystems.shm.rainflow        # ASTM E1049 reference example
python -m subsystems.shm.scoring         # Info Kit worked example
python -m subsystems.door.evaluate       # end-to-end holdout score + Test drift check
python -m subsystems.shm.evaluate
python -m subsystems.rail_corrugation.verify_inference
python -m subsystems.acv.evaluate        # leave-one-case-out over the 6 labelled cases
```

Training is deterministic; `python -m subsystems.<name>.train` (Door, SHM) or
`train_final` (Rail) rewrites a byte-identical model.

## Regenerate predictions and package the submission

```bash
python -m subsystems.door.predict  --input data/Door/Test.csv          --output predictions/door_predictions.csv
python -m subsystems.acv.predict   --input data/ACV/Test               --output predictions/acv_predictions.csv
python -m subsystems.rail_corrugation.generate_predictions            # -> predictions/rail_predictions.csv
python -m subsystems.shm.predict   --input data/SHM/Test               --output predictions/shm_predictions.csv

python scripts/validate_submission.py --zip    # checks every file against the scoring rules, writes predictions.zip at the root
python scripts/package_submission.py           # rebuilds Optional_Items/ and predictions.zip in place; --dist NAME for a standalone folder
```

The validator fails loudly on anything that would score zero (wrong column names or labels,
missing test files, ACV car IDs not matching the workbook headers).

## Layout

```
webapp/                   the submitted app: backend/main.py (FastAPI), frontend/ (React + Vite);
                          deployed to Cloud Run via the root Dockerfile
app/                      earlier Streamlit frontend; reliability.py and samples/ are shared with webapp
subsystems/<name>/        one independent package per subsystem: loader, features, model, train,
                          predict (CLI: --input/--output), evaluate, PLAN.md, committed model artifact
scripts/                  validate_submission.py, package_submission.py
references/               organisers' problem statement and the four subsystem Info Kits
Optional_Items/           spec item 4.2: per-subsystem code and model copies, write-up (tracked, generated)
VIDEO.md                  shot list and narration for demo_video.mp4
predictions/              generated *_predictions.csv (gitignored); predictions.zip is at the root (tracked)
```

Each `subsystems/<name>/PLAN.md` records the data facts, the method, every experiment run
(including the rejected ones), the validation numbers and the decisions — that is the source
material for the write-up.

## Methodology in one paragraph each

- **Door** — cycles are separated by ≥10 s gaps in the stream, so a timestamp-gap split
  reproduces all 110 labelled boundaries exactly; a logistic regression on per-cycle
  current/back-EMF features then separates abnormal resistance (more current, less back-EMF).
  Validated on a time-ordered holdout; the score matched it.
- **ACV** — a leaking unit cannot pull its cabin down to the cooling setpoint, so each car's
  mean (cabin − setpoint) in cooling mode is the direct signature; it is blended with a
  peer-deviation heuristic that covers files without cabin sensors. No fitted parameters;
  1.000 leave-one-case-out.
- **Rail Corrugation** — 239 per-channel time/frequency features pooled per rail side plus
  side asymmetries, gradient boosting with balanced class weights, a stationary-train rule.
  Twelve alternatives were tested under repeated stratified CV with a pre-declared noise floor;
  none beat it. Side I (14 training files) is the data-limited ceiling.
- **SHM** — the labels are a Miner's-rule sum over a rainflow count with S-N exponent 5,
  recovered from the data (log-log slope 0.997); the model is that sum with one fitted scale
  and a small, clipped ridge correction. 0.978 leave-one-out; 0.974 held-out.
