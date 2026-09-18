---
name: shm-fatigue-regression
description: Use when building or evaluating the SHM subsystem model (PS3) — regressing a single cumulative fatigue-damage value from dynamic stress time-series files. Covers Miner's-rule/rainflow-derived features and the exact MAPE-derived scoring formula.
---

# SHM: fatigue-damage regression + MAPE scoring

## Task shape

64 train files / 16 test files, each an equal-length dynamic-stress time segment from one
measurement point, all healthy operation (no fault examples — pure regression on damage
magnitude). Output: one row per file, `file_id`, `prediction` (single numeric damage value).
File numbers (`train01`..`train64`) are random IDs, not a sequence — never use filename order as
a feature.

## Feature engineering — lean on the domain method even without replicating it exactly

The reference labels were computed via **Miner's rule + rainflow counting**
(`D = Σ nᵢ/Nᵢ`, `Nᵢ = C / σ_{a,i}^m` from an S-N curve). You don't have to reimplement this
method, but its structure suggests strong features even for a plain ML regressor:
- Run rainflow counting on each file's stress series (e.g. via a rainflow-counting library) to
  get cycle-amplitude/mean/count triples, then feed **summary statistics of that cycle
  distribution** (total cycle count, amplitude histogram bins, max amplitude, weighted cycle
  sums) as regressor inputs — this is far more informative than raw time-domain stats alone.
- Also include plain statistical features (RMS, std, peak-to-peak, kurtosis — high kurtosis
  indicates more large-amplitude excursions which drive damage disproportionately) and, if
  identifiable from the data, line/load-condition (AW0 vs AW4) as a categorical feature — the
  dataset spans two lines and two load conditions per the Info Kit.
- Split by file, and check whether line/load-condition metadata can be inferred/derived to
  stratify the train/val split so both conditions are represented in validation.

## Scoring formula (implement this exactly for local validation)

```
MAPE  = mean( |true - predicted| / |true| )       # relative error, per file, averaged
score = max(0, 1 - MAPE)
```

- 0% error → 1.0. 10% average error → 0.90. 25% → 0.75. Floors at 0 once MAPE ≥ 100%.
- This is measured **relative to each file's true value**, so a fixed additive bias hurts small
  true-damage files far more than large ones — don't just minimize plain MAE, minimize relative
  error (e.g. consider training on log(damage) or optimizing a MAPE-like loss directly, since
  plain MSE/MAE optimizes absolute error and can look fine on aggregate while being bad on the
  low-damage files that dominate this metric).
- Worked example (from the Info Kit): true `[0.10,0.30,0.50,0.70,0.90]`, pred
  `[0.15,0.28,0.55,0.68,0.85]` → per-file relative errors 50.0%, 6.7%, 10.0%, 2.9%, 5.6% →
  MAPE = 15.0% → score = 0.850. A constant-guess model (predicting 0.50 for everything) scores
  MAPE ≈ 108% → score floors at 0.

Report MAPE-derived score locally, not R²/RMSE, when comparing candidate models — a model with
lower RMSE can still have worse MAPE if its errors are concentrated on small-true-value files.
