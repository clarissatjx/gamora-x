# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Team gamora-x's submission for **NebulaX Hackathon PS3 (Train Condition Monitoring)**: four
independent sensor-based models (Door, ACV, Rail Corrugation, SHM) behind one Streamlit app.
All four are built, scored on the organisers' held-out sets, and wired into the app — see
[README.md](README.md) for results and commands. The spec is
[references/PS3_Problem_Statement.md](references/PS3_Problem_Statement.md); each subsystem's
authoritative Info Kit is under `references/<Subsystem>/`.

## Commands

```bash
streamlit run app/app.py                              # the app (lands on the overview)
python -m subsystems.door.scoring                     # self-tests: door scoring, shm rainflow, shm scoring
python -m subsystems.<name>.evaluate                  # holdout / LOO score + Test drift check (door, shm, acv)
python -m subsystems.rail_corrugation.verify_inference
python -m subsystems.<name>.train                     # deterministic retrain (door, shm); rail: train_final
python -m subsystems.<name>.predict --input <file|dir> --output predictions/<name>_predictions.csv
python scripts/validate_submission.py --zip           # schema checks on every prediction CSV, writes predictions.zip at the root
python scripts/package_submission.py                  # rebuilds Optional_Items/ (tracked copies of subsystems/) and the zip
```

Run everything from the repo root. The raw data lives in `data/<Subsystem>/` (gitignored,
~6.5 GB, mirrors the organisers' `02_Datasets/`); `predictions/*.csv` is gitignored but the
root `predictions.zip` is tracked. **This repository is the submission**: its root must keep
the spec's tree (`demo_video.*`, `predictions.zip`, `app/`, `Optional_Items/`), and what the
judges see is the default branch, so finished work has to reach `main`. After any subsystem
change, re-run the packager so `Optional_Items/*/code` doesn't drift from `subsystems/`.

## Architecture

- `subsystems/<name>/` is an independent package: `loader`/`features` → `train` (saves a
  committed model artifact) → `predict` (`predict(path)` plus a `--input/--output` CLI) →
  `evaluate`. Each has a `PLAN.md` holding the data facts, every experiment (including rejected
  ones), validation numbers and decisions — the write-up's source material. Rail's package
  was built by a teammate and has a wider set of phase scripts; its PLAN.md indexes them.
- `app/app.py` is the shell (sidebar nav, run mode, evidence toggle, theme toggle, model
  metadata) and routes to `app/inference/<page>.py`. Pages call the subsystem's `predict`/
  `analyse` functions — the CLI and the app share one inference path, and the shipped
  predictions must be byte-identical either way (checked in each subsystem's evaluate/verify).
- `app/theme.py` is the design system: palette as CSS custom properties (dark and light),
  Source Sans 3 + IBM Plex Mono, and the HTML/Altair helpers (`page_title`, `banner`,
  `metrics`, `panel`, `table`, `pill`, `evidence`, `style_chart`). Altair cannot read CSS
  variables, so charts take concrete hex from `theme.chart_colors()`.
- `app/inference/acv.py` is a Streamlit-free inference module (the ACV CLI imports it); the
  page is `acv_page.py`. Keep that split.

## Gotchas that have bitten

- `st.set_page_config` must be the first Streamlit call; SUBS metadata that touches a
  `@st.cache_resource` loader has to come after it.
- Sidebar buttons call `st.rerun()`, which aborts before main-area widgets render and makes
  Streamlit drop their state. Uploads are therefore stashed in `st.session_state["<name>_files"]`
  and pages read from the stash; the overview's content-based routing writes to the same keys.
- Panels are `st.container(border=True)` matched by an exact parent-chain `:has()` selector,
  because Streamlit tags *every* vertical block with `stVerticalBlockBorderWrapper`.
- `subsystems/rail_corrugation/artifacts/rail_model.joblib` is version-fragile in both
  directions: on numpy 1.x it fails to unpickle, and on scikit-learn 1.9.1 it unpickles fine
  but raises on the first `predict_proba`. `predict.load_artifact` therefore smoke-tests every
  candidate with a real prediction (`_usable`) and retrains from the cached feature table
  (deterministic, ~2 s, reproduces the submitted predictions on all 68 test files) into an
  untracked `*.local.joblib`. Do not narrow that check back to catching unpickling errors.
- Rail's shock channels carry a DC offset that looks like sensor bias — leave it in; demeaning
  costs 0.044 macro F1. Rail is at a measured local optimum (12 rejected alternatives); do not
  spend time re-tuning it.
- Submission formats are graded mechanically and a malformed file scores zero for its
  subsystem: run the validator before anything is submitted.

## Skills

`.claude/skills/` has one skill per subsystem with the exact scoring formulas, plus shared
ones for split strategy, signal features, submission packaging and the app. They load
automatically when the matching work comes up.
