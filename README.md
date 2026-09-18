# gamora-x — NebulaX Hackathon PS3: Train Condition Monitoring

Four condition-monitoring models for rail vehicles behind one Streamlit app, built for
[NebulaX PS3](references/PS3_Problem_Statement.md). Upload a raw sensor file, get the
prediction on screen with the evidence behind it, download the submission CSV.

| Subsystem | Task | Metric | Held-out score |
|---|---|---|---|
| Door | segment a continuous motor-current stream into cycles, flag abnormal resistance | IoU-weighted F1 | **1.000** |
| ACV | rank 8 cars by likelihood of a refrigerant leak | rank-decay | 0.875 (v1) |
| Rail Corrugation | classify a 1 s axle-box recording: Normal / Side I / Side II | macro F1 | 0.888 |
| SHM | cumulative fatigue damage from a dynamic-stress series | 1 − MAPE | 0.974 |
| **Overall** | | mean of four | **0.934** |

## Run the app

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

The app opens on an overview. Drop any raw file there — it identifies the subsystem from the
file's contents and routes to that page — or pick a subsystem in the sidebar. Every page follows
the same flow: upload → banner → metrics → charts and evidence → results table → download.
Batch mode accepts several files at once. Uploads persist while you navigate. Try:

```
data/Door/Test.csv                    38 cycles, 8 flagged abnormal
data/ACV/Test/acv_test_case.xlsx      car 01 ranked most likely faulty
data/Rail_Corrugation/Test/Test26.csv Side II, 100 %
data/SHM/Test/test02.csv              damage 0.8276
```

The raw datasets are not in the repo (`data/` is gitignored); mirror the organisers'
`02_Datasets/` layout into `data/`.

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

python scripts/validate_submission.py --zip    # checks every file against the scoring rules, writes predictions.zip
python scripts/package_submission.py --team "<registered team name>"   # assembles dist/<team>/ per the spec
```

The validator fails loudly on anything that would score zero (wrong column names or labels,
missing test files, ACV car IDs not matching the workbook headers).

## Layout

```
app/                      Streamlit app: app.py (shell), theme.py (design system), inference/<page>.py
subsystems/<name>/        one independent package per subsystem: loader, features, model, train,
                          predict (CLI: --input/--output), evaluate, PLAN.md, committed model artifact
scripts/                  validate_submission.py, package_submission.py
references/               organisers' problem statement and the four subsystem Info Kits
predictions/              generated *_predictions.csv and predictions.zip (gitignored)
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
