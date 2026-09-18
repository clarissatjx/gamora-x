# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

This repo is a 4-person team's submission for **NebulaX Hackathon PS3 (Train Condition
Monitoring)** — see [PLANNING.md](PLANNING.md) for the full plan and [PS3.md](PS3.md) for the
organisers' top-level problem statement. The problem covers **4 independent subsystems**, each
its own self-contained ML task, plus one compulsory shared app:

| Subsystem | Task | Metric |
|---|---|---|
| Door | Segment a continuous sensor stream into open/close cycles, classify each Normal/Abnormal resistance | IoU-weighted F1 |
| ACV | Rank 8 cars by likelihood of refrigerant leak | Linear rank-decay |
| Rail Corrugation | 3-class classification (Normal/Side I/Side II) from axle-box vibration | Macro F1 |
| SHM | Regress a cumulative fatigue-damage value from stress time series | max(0, 1 − MAPE) |

Each subsystem has its own full spec (schema, business context, worked scoring example) in the
Info Kits under the organisers' repo (referenced from PLANNING.md) — read the relevant one before
touching that subsystem's code, since column schemas and split-worthy grouping vary by subsystem
and are not interchangeable.

**No application code exists yet** — the repo currently holds planning docs, the raw datasets,
and `.claude/` skills/agents scaffolding. The intended structure (not yet built) is:

```
app/                    # single shared Streamlit app, one inference module per subsystem
subsystems/
├── door/ acv/ rail_corrugation/ shm/   # per-subsystem EDA/training code
data/                   # raw datasets (gitignored by default — see Data below)
predictions/            # generated *_predictions.csv, zipped for submission
```

As real code lands, update this file's Commands section with the actual run/lint/test commands
(there's no build system to describe yet since nothing has been scaffolded).

## Data

Raw datasets (`data/<Subsystem>/...`) mirror the organisers' `02_Datasets/` layout exactly —
`Door`, `ACV`, `Rail_Corrugation`, `SHM`, each with `Train`/`Test` splits. Total size is ~6.5GB,
dominated by `Rail_Corrugation` (~5.5GB across 341 files). `data/` was intentionally excluded from
`.gitignore` on 2026-09-18 to push it to the repo temporarily — this is meant to be removed later
by re-adding `data/` to `.gitignore` and cleaning it out of git history (a plain file deletion
commit does not remove it from history/repo size; that needs an explicit history rewrite).

## Submission requirements to keep in mind while building

These constraints shape how any code here should be structured, since they're graded
mechanically, not just by intent:
- Each subsystem's inference logic must be reusable both from the shared app and from a batch
  script that regenerates `*_predictions.csv` — don't fork the logic in two places.
- Prediction output schemas are exact and subsystem-specific (e.g. Door has no `file_id` and one
  row per predicted segment; ACV has no `prediction` column and a pipe-separated `ranked_cars`
  instead) — see `.claude/skills/prediction-submission-packager/SKILL.md` for the full table.
- Train/validation splits must be justified per subsystem (contiguous time-block for Door,
  leave-one-out for ACV's 6 cases, stratified for Rail Corrugation's imbalanced classes, grouped
  by line/load-condition for SHM) — the rubric grades split soundness alongside the metric itself,
  so a naive random-row split is a scoring risk. See `.claude/skills/train-val-split-strategy/SKILL.md`.
- Raw datasets and the organisers' `04_Example_Submission/` folder must never appear in the final
  submission zip.

## Skills and agents

`.claude/skills/` has one skill per subsystem (exact scoring formulas + modeling guidance) plus
shared ones for signal feature engineering, split strategy, submission packaging, and the
Streamlit app — these activate automatically when working on the matching task; read the relevant
one before implementing that subsystem's model or the app. `.claude/agents/ml-engineer.md` is a
general-purpose ML engineering subagent, invokable via the Agent tool for production-ML-pipeline
style tasks.
