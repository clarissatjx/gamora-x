# NebulaX Hackathon — PS3: Train Condition Monitoring — Planning Doc

Team: **gamora-x** (4 people)
Problem statement source: [NebulaX-Hackathon-ProblemStatement/PS3](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/tree/main/PS3)
Assumed window: **~24 hours**. Fill in the actual start/deadline once confirmed:

- Kickoff: `TBD`
- Submission deadline: `TBD`
- Held-out test input files released: `TBD` (organisers distribute these ahead of the deadline — see Data Conventions below)

---

## 1. The challenge, in one paragraph

We're given sensor data from **4 independent rail-vehicle subsystems**, each its own self-contained task. We can attempt any subset — more subsystems raises our **Overall Score** and can never hurt it, but focusing on fewer can raise our **Average Score**. Every subsystem needs: a model, a `*_predictions.csv` on the held-out test file(s), and **one shared app** (not one app per subsystem) that lets a non-technical user upload a file and get a prediction back. See Section 4 for the scoring math behind that tradeoff.

## 2. Subsystem cheat-sheet

| # | Subsystem | Task type | Input signal | Output file | Metric |
|---|---|---|---|---|---|
| 1 | **Door** | Segment the continuous `Test.csv` stream into door cycles, then classify each cycle | Motor current/voltage/back-EMF + door position, 17 cols, continuous stream | `door_predictions.csv` — one row **per predicted segment**: `start_time`, `end_time`, `prediction` (`Normal`/`Abnormal resistance`). **No `file_id`.** | IoU-weighted F1 (harmonic mean of soft precision/recall, credit = IoU per match) |
| 2 | **ACV** | Rank all 8 cars in a file from most- to least-likely to have the refrigerant leak | Per-car telemetry (8–60+ params/car depending on file), 1 row per 30s timestamp | `acv_predictions.csv` — one row per file: `file_id`, `ranked_cars` (`\|`-separated, car IDs exactly as in that file's headers, e.g. `03`). **No `prediction` column.** | Linear rank-decay: `score = (n-(r-1))/n` where r = rank of true faulty car |
| 3 | **Rail Corrugation** | Classify a 1s axle-box recording as Normal / Side I / Side II | 129 cols (speed + 64 axle-boxes × vibration/shock), 10kHz, 1s files | `rail_predictions.csv` — one row per file: `file_id`, `prediction` (`Normal`/`Side I`/`Side II`) | Macro F1 (unweighted avg across 3 classes — dataset is ~86% Normal, so this matters a lot) |
| 4 | **SHM** | Predict a single cumulative fatigue-damage number per file | Dynamic stress time series, equal-length segments | `shm_predictions.csv` — one row per file: `file_id`, `prediction` (numeric) | `max(0, 1 − MAPE)` |

Full authoritative details (schemas, edge cases, worked scoring examples) live in each subsystem's own Info Kit under `03_References/<Subsystem>/` in the problem-statement repo — **read the relevant one in full before that subsystem's owner starts building**, this table is just an index.

Dataset sizes worth knowing up front:
- **Door**: 1 continuous labelled stream (`Train.csv` + `Train_Segments_Answer.csv`) + 1 unlabelled continuous `Test.csv`. Segmentation is the hard part, not just classification.
- **ACV**: only **6 labelled training cases** total (one faulty car each) + 1 test case. Very low sample count — expect to lean on domain reasoning/feature engineering over deep learning.
- **Rail Corrugation**: 272 train files (234 Normal / 14 Side I / 24 Side II — heavily imbalanced), 68 test files.
- **SHM**: 64 train files, 16 test files, regression only, no fault examples (all healthy — predicting a continuous damage value).

## 3. Repo / submission structure

Final deliverable folder must be named exactly after our registered team name and contain:

```
<Team Name>/
├── demo_video.mp4              # <=3 min, app end-to-end: pick subsystem, upload file, view+download result
├── predictions.zip              # flat zip of *_predictions.csv, one per subsystem attempted, no subfolders
├── app/                          # our Streamlit app source + deploy instructions
└── Optional_Items/
    ├── write_up.md               # approach, features, model choice, metrics, assumptions
    ├── Door/{code/,model/}
    ├── ACV/{code/,model/}
    ├── Rail_Corrugation/{code/,model/}
    └── SHM/{code/,model/}        # omit any subsystem folder we don't attempt
```

Proposed working layout in **this repo** while building (reorganize into the shape above only at submission time):

```
gamora-x/
├── app/                    # single Streamlit app, one page/tab per subsystem
├── subsystems/
│   ├── door/                {notebooks, features.py, train.py, predict.py, model artifact}
│   ├── acv/
│   ├── rail_corrugation/
│   └── shm/
├── data/                   # gitignored — raw datasets from the problem-statement repo, not committed
└── predictions/            # generated *_predictions.csv, zipped at the end
```

**Note:** Do not commit the raw datasets or the `04_Example_Submission/` folder — the spec explicitly says not to include these in the submission, and they're large/not ours to redistribute. Add `data/` to `.gitignore`.

## 4. Breadth vs. depth — the actual tradeoff to decide as a team

- **Overall Score** = (sum of per-subsystem score across all 4) / 4, always. Skipping a subsystem just contributes 0 for it — never negative, but never helps either.
- **Average Score** = (sum of per-subsystem score across only attempted subsystems) / (number attempted). A team doing 2 subsystems well is judged only on those 2.
- Both numbers get reported, so there's no single "right" answer — but with **4 people on the team, one owner per subsystem lets us attempt all 4 without spreading anyone across two problems**, maximizing Overall Score for roughly the same per-person effort as 2 people each doing 2. Recommend defaulting to **all 4, one owner each**, and only consolidating to fewer if a subsystem's owner gets stuck early (see contingency in Section 6).
- Every subsystem is weighted equally (25%) regardless of how "hard" it seems — there's no bonus for tackling the harder ones.

## 5. Suggested team structure

Fill in names once assigned. With ~24h and 4 subsystems, the natural split is **one person per subsystem, end-to-end (EDA → baseline → iterate → predict.py-equivalent script)**, with the app built collaboratively in short shared blocks rather than by a single "app person" working in isolation — everyone needs the app to actually produce their subsystem's predictions before the deadline.

| Owner | Subsystem | Also responsible for |
|---|---|---|
| `TBD` | Door (segmentation + classification) | |
| `TBD` | ACV (fault ranking) | |
| `TBD` | Rail Corrugation (3-class) | |
| `TBD` | SHM (regression) | |

Shared, cross-cutting responsibilities (rotate or assign based on strengths, not tied to a subsystem):
- **App integration**: wiring each person's trained model into the shared Streamlit app (Section 7).
- **Submission packaging**: zip structure, demo video recording/editing, final folder layout (Section 3).
- **Write-up**: assumptions, train/val split rationale per subsystem (Section 8), metric interpretation.

## 6. Timeline (~24h sprint)

Adjust hour markers once the actual kickoff/deadline times are known — the *relative* structure (roughly a third each for exploration, modeling, integration+polish) should hold regardless of exact clock times.

| Time | Milestone |
|---|---|
| Hour 0–1 | Kickoff: everyone reads the top-level spec; each owner claims a subsystem and reads *only* their Info Kit in full. Confirm team name for the submission folder. |
| Hour 1–2 | Each owner loads their data, visualises a few files, sanity-checks the schema against the Info Kit. Agree on `.gitignore` for `data/`. |
| Hour 2–4 | Each owner defines their train/val split (see Section 8 — must be justified, not random-row-shuffle) and gets a trivial baseline running end-to-end (dumb model → correctly-shaped prediction CSV). **Goal: a valid, correctly-formatted (if bad) prediction file per subsystem by hour 4** — this de-risks the app/format integration early instead of leaving it to the end. |
| Hour 4–5 | Skeleton Streamlit app: subsystem picker, file upload, calls a stub `predict()` per subsystem, shows + downloads output. Merge each owner's real predict function in as it's ready. |
| Hour 5–14 | Main modeling iteration per subsystem, in parallel. Regular check-ins (every ~2-3h) to catch anyone blocked early enough to redistribute help. |
| Hour 14–16 | Freeze modeling. Each owner finalizes their inference path and plugs the real trained model into the app. |
| Hour 16–18 | Run the **actual held-out test input files** (once released — Section 2.3 of the main spec) through the app for every attempted subsystem; produce and sanity-check final `*_predictions.csv` files (correct schema, no missing rows, sensible value ranges). |
| Hour 18–20 | App polish for Ease of Use: clear labels, sensible defaults, error states for malformed uploads, results rendered clearly (table/chart, not raw CSV dump). |
| Hour 20–21 | Record the demo video (<=3 min): pick a subsystem, upload, show result on screen, download it. Repeat per subsystem if time allows, or one continuous walkthrough covering all attempted subsystems. |
| Hour 21–23 | Write-up (optional but strengthens Problem Fit score): approach, features, model choice, split rationale, assumptions per subsystem. |
| Hour 23–24 | Assemble final submission folder exactly per Section 3, zip `predictions.zip` separately, double check naming (`<Team Name>/`), final review. |

## 7. Shared app (Streamlit)

One app, not four — a single entry point with a subsystem selector, since the spec requires "a single app covering every subsystem you attempt."

Minimum viable structure:
```
app/
├── app.py            # subsystem picker (st.selectbox / tabs) + file uploader + results panel
├── models/           # loaded trained artifacts, one per subsystem
├── inference/
│   ├── door.py        # load stream -> segment -> classify -> DataFrame matching door_predictions.csv schema
│   ├── acv.py          # load telemetry -> rank cars -> DataFrame matching acv_predictions.csv schema
│   ├── rail.py         # load vibration file -> classify -> DataFrame matching rail_predictions.csv schema
│   └── shm.py           # load stress series -> regress damage -> DataFrame matching shm_predictions.csv schema
└── requirements.txt
```

Per-subsystem UI flow (all four should follow this same shape for consistency and for a clean demo video):
1. User picks the subsystem tab/selector.
2. User uploads the raw data file(s) for that subsystem (accept the same format as the raw dataset files — `.csv`/`.xlsx` as applicable).
3. App runs that subsystem's `inference/*.py`, renders the result on screen (a table for per-segment/per-file predictions; consider a simple chart e.g. highlighting predicted door segments over the raw signal, or the ranked car list for ACV) — this directly feeds the Ease-of-Use score (Section 6.3 of the spec).
4. A download button exporting the exact `*_predictions.csv` schema required for that subsystem.

Each `inference/*.py` function is also what gets called in bulk to generate the final `*_predictions.csv` submissions in Section 6's Hour 16–18 step — write it once, use it both from the app and from a small batch script, rather than duplicating logic.

## 8. Methodology notes (apply per subsystem)

- **Train/val split must be justified, not arbitrary** — the spec explicitly grades this alongside the headline metric. Suggested starting points per subsystem (confirm against each Info Kit, and record the reasoning in the write-up):
  - *Door*: split by holding out a contiguous time range of `Train.csv` (and its labelled segments) rather than shuffling individual rows, since rows within a cycle are highly correlated.
  - *ACV*: only 6 labelled cases exist — likely leave-one-case-out cross-validation rather than a fixed split, given the tiny sample size.
  - *Rail Corrugation*: stratified split by class label to keep rare Side I/II examples represented in validation, given the ~86/5/9 class imbalance.
  - *SHM*: split by file, and check whether line/load-condition (AW0 vs AW4) metadata is available to stratify against, since the doc notes two lines and two load conditions.
- **Check class balance before picking any secondary/dev metrics** — the primary metric is already fixed per subsystem (Section 2), but this affects what you watch during training (e.g. don't tune Rail Corrugation on plain accuracy, it's misleading with this imbalance — see the Info Kit's worked example).
- **No leakage**: don't let information from a held-out validation fold leak into feature engineering done on the full training set (e.g. global normalization stats computed across train+val before splitting).

## 9. Open questions / things to verify with organisers

- Each subsystem's Info Kit repeatedly references a `predict.py` script with a required `--input`/`--output` CLI interface as a compulsory deliverable, but the **top-level spec's Deliverables section (4.1) only lists the video, `predictions.zip`, and the app** as compulsory — `predict.py`/dev code only appears under *optional* items (4.2). This looks like leftover text from an earlier spec version. **Confirm with organisers whether a standalone `predict.py` CLI is actually required, or whether the app satisfies that role** — don't spend time building a CLI wrapper on faith if the app already covers it.
- Exact hackathon start/deadline times and when the held-out test input files get released (needed to finalize Section 6's hour markers).
- Confirm registered team name for the final submission folder name.

## 10. Deliverables checklist (compulsory)

- [ ] `demo_video.<ext>` — ≤3 min, shows app end-to-end for every subsystem attempted
- [ ] `predictions.zip` — flat, contains only `*_predictions.csv` for attempted subsystems, correct schema per Section 2
- [ ] `app/` — single app, covers every attempted subsystem, used to actually generate the predictions above
- [ ] Submission folder named exactly as the registered team name
- [ ] Raw datasets and `04_Example_Submission/` **excluded** from the submission

Optional, but strengthens scoring:
- [ ] `Optional_Items/write_up.md` — approach, features, model choice, metric interpretation, split rationale/assumptions per subsystem
- [ ] `Optional_Items/<Subsystem>/code/` and `/model/` for each attempted subsystem
