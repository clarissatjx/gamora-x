# Rail Corrugation — Build Plan

Working plan for the Rail Corrugation subsystem (3-class: Normal / Side I / Side II,
scored on macro F1). Each phase below ends with a **stop point** — I pause, you check the
listed things, and we move on once you're satisfied. Nothing in a later phase gets built
on top of an earlier one until you've signed off.

Code lives in `subsystems/rail_corrugation/`. Data lives at
`data/data/Rail_Corrugation/{Train,Test}/` + `Train_Labels.csv`.

---

## Phase 0 — Data audit (done)

What was done: inspected raw CSVs directly (via shell, no code) to confirm the schema
matches the Info Kit before writing any pipeline code.

Findings:
- 129 columns confirmed: col 0 = speed sensor, cols 1–128 = Car1‑Pos1‑vib, Car1‑Pos1‑shock,
  ... Car8‑Pos8‑vib, Car8‑Pos8‑shock — matches Info Kit ordering exactly.
- Label counts confirmed: 234 Normal / 14 Side I / 24 Side II (matches Info Kit).
- Col 0 ("rotating speed") is a raw binary `{0, 1}` pulse toggle signal, **not** a
  precomputed speed value.
- Real data path is `data/data/Rail_Corrugation/...` (extra nested `data/`), not
  `data/Rail_Corrugation/...` as CLAUDE.md describes.

**Stop point — how to check:**
- Run `cut -d',' -f1 "data/data/Rail_Corrugation/Train/Train1.csv" | tail -n +2 | sort -u`
  yourself — should print only `0` and `1`.
- Run `head -1 "data/data/Rail_Corrugation/Train/Train1.csv"` — should show 129
  comma-separated column names, first one about rotating speed.
- Run `tail -n +2 "data/data/Rail_Corrugation/Train_Labels.csv" | cut -d',' -f2 | sort | uniq -c`
  — should show 234/14/24.

*(Already implicitly approved since you asked me to continue past this — flagged here for
completeness/traceability.)*

---

## Phase 1 — Speed derivation + per-file feature extraction module (done, pending your check)

Files: `config.py` (paths/constants), `features.py` (speed derivation + feature
extraction), `eda_check.py` (spot-check script, not part of the pipeline).

What it does:
- `derive_speed_mps`: counts 0→1 rising edges in the pulse train, divides by 90 teeth,
  converts to m/s via wheel circumference (π × 0.85m). **Assumption**: 1 rising edge = 1
  tooth. Not disclosed/verified against ground truth — documented as an assumption to
  state in the write-up, not a confirmed calibration.
- Per-channel features (time domain: RMS, std, peak-to-peak, skew, kurtosis,
  zero-crossing rate; frequency domain: dominant frequency, its energy ratio, spectral
  centroid, and a derived "wavelength" = speed / dominant frequency).
- Aggregated per side (Side I / Side II) × signal type (vibration/shock) via mean, max,
  std across each side's 32 channels (4 positions × 8 cars).
- Added Side I vs Side II **asymmetry features** (diff and ratio) per stat — added after
  a 6-file spot check showed the sign of (Side I − Side II) tracked the labelled fault
  side better than either side's raw magnitude alone.
- Ran on 6 sample files (2 per class): ~0.25s/file, speeds ranged 1.7–17.8 m/s (physically
  plausible), 121 features per file before the asymmetry features were added.

**Stop point — what to check and how:**
1. **Read the code**: [features.py](features.py) — does the column-index math in
   `_channel_column_indices` actually match the Info Kit's stated column order? (Formula:
   for car `c` (0-indexed), position `p` (1-indexed), vibration is at
   `1 + (c*8 + (p-1))*2`.) You can hand-verify one or two positions against
   `head -1 Train1.csv` yourself.
2. **Re-run the spot check** and eyeball it:
   ```
   python -m subsystems.rail_corrugation.eda_check
   ```
   Sanity checks on the output: do speeds look like plausible metro speeds (a few to
   tens of m/s, not negative, not absurdly large)? Does `n_features` match what you'd
   expect given the feature list above?
3. **Judgment call to weigh in on**: the "1 rising edge = 1 tooth" assumption for speed
   — alternative would be "1 tooth = 2 transitions" (half the speed value). Either is
   internally consistent (same scaling applied to every file), but if you have domain
   intuition about realistic metro speeds, this is your chance to sanity-check which
   convention is more plausible.
4. **Judgment call to weigh in on**: the asymmetry (diff/ratio) features — reasonable
   addition, or do you want to see it proven out in model results first before trusting
   it as a design choice?

Not yet done at this point: no full feature table built, no model trained, no split
logic.

---

## Phase 2 — Full feature table (272 train + 68 test files) — DONE, pending your check

Files: `build_features.py` (pipeline), `check_zero_speed.py` (follow-up investigation),
`artifacts/train_features.csv`, `artifacts/test_features.csv`.

Results:
- TRAIN: 272 rows × 241 features. TEST: 68 rows × 241 features. Zero `NaN`, zero `inf`.
- Runtime: 69s train + 18s test (~87s total), as estimated.
- **The asymmetry feature works — but only really for Side II.** Mean
  `asym_diff_vib_rms_mean` by class: Normal −0.001, Side I **+0.031**, Side II **−0.109**.
  My first reading ("clean separation") **overstated it**; an independent review caught
  this and I verified the correction with `check_separation.py`:

  | Class | one-vs-rest AUC (this feature alone) | % of Normal inside its IQR |
  |---|---|---|
  | Side II | **0.92** — strong, usable alone | 3.4% |
  | Side I | **0.69** — weak | 62.0% |

  So the means hide heavy overlap for Side I. **Side I is the bottleneck class**: only 14
  examples *and* weakly separated. Since macro F1 weights all three classes equally, Side I
  F1 will cap our score, and Phase 5 iteration should target it specifically rather than
  chasing overall accuracy. Keep the asymmetry block (it earns its place on Side II), but
  don't assume it solves Side I.

### Finding that needs a decision: 38 train / 9 test files are stationary

Investigated via `check_zero_speed.py`:
- 38 of 272 train files (14%) have a pulse column that is **constant 1.0 for all 10,000
  samples** — the toothed-wheel sensor never toggles. The train is stopped, not a bug in
  the edge detector.
- **All 38 are labelled `Normal`** (0 Side I, 0 Side II).
- Their vibration RMS is ~0.0709 with an extremely tight spread (0.0698–0.0718) versus
  0.070–0.833 for moving files — i.e. a flat noise floor, consistent with a stationary
  vehicle.
- The test set has 9 such files (13%), which are therefore near-certainly `Normal` too.

Why this matters: a stationary train physically *cannot* produce a corrugation signature,
so "stopped ⇒ Normal" is legitimate signal, not leakage. But it means ~14% of the Normal
class is trivially separable, which **inflates CV macro F1 relative to the model's real
ability to discriminate faults among moving trains**. The same inflation will apply to the
held-out test score, so the CV number stays an honest *score* estimate — it's just a
misleading *capability* estimate.

**DECIDED (independent review, then verified): exclude stationary files from model
training and handle them with an explicit `speed == 0 ⇒ Normal` rule at inference.**

Rationale: dropping them costs **zero** minority-class information (0 of the 38 are Side I
or Side II), so there is no capability tradeoff — a tree would have learned the split
anyway. What it buys is honesty: CV macro F1 then measures the actually-hard problem
(discriminating faults among *moving* trains) instead of being padded by 14% free Normal
wins, which makes the Phase 5 ablations meaningful. And "a stationary train cannot
corrugate" is a deterministic physical rule, far more defensible in the write-up than
hoping a gradient-boosted tree reconstructed it. At submission time: apply the rule to the
9 stationary test files, the model to the other 59.

### Second finding: two pairs of byte-identical duplicate files

An exhaustive MD5 scan of all 340 raw files (I ran this to confirm the reviewer's claim)
found exactly two duplicate groups, both inside Train, and **no train↔test duplication**:
- `Train107.csv` == `Train115.csv` (both Normal, both moving)
- `Train165.csv` == `Train187.csv` (both Normal, both **stationary**)

This is a real CV leakage risk: if a split puts one member of a pair in train and the
other in validation, that fold validates on a file it literally trained on.

Convenient interaction: the second pair is stationary, so the decision above removes it
from the training set automatically. **Only `Train107`/`Train115` needs explicit
same-fold grouping.**

**Stop point — what to check and how:**
- Row counts: `artifacts/train_features.csv` should have 272 data rows, `test_features.csv`
  68. Check with `wc -l` (expect 273 / 69 including the header).
- Verify the zero-speed finding yourself on one file:
  `cut -d',' -f1 "data/data/Rail_Corrugation/Train/Train5.csv" | tail -n +2 | sort -u`
  — should print only `1`.
- Open `artifacts/train_features.csv` in Excel, sort by `label`, and eyeball
  `asym_diff_vib_rms_mean` — Side I rows should skew positive, Side II rows negative.
- Decide the stationary-files question above.

---

## Phase 3 — Stratified split / cross-validation setup (revised after Phase 2 findings)

Plan: `split.py` — stratified k-fold (k=5) over the **234 moving** train rows (stationary
files excluded per the Phase 2 decision), with:
- **Stratification by `label` alone.** The review recommended (`label` × `stationary`),
  but that dimension is now moot: once stationary files are excluded from training, every
  remaining row is moving, so the second dimension is constant. (Its measured benefit —
  steadying the per-fold stationary count — is achieved outright by exclusion.)
- **Duplicate grouping**: `Train107`/`Train115` forced into the same fold.

Nothing trained yet.

**Stop point — what to check and how:**
- I'll print each fold's class counts — every fold should have ≥2 Side I and ≥2 Side II.
  With 14 Side I over 5 folds, expect 2–3 per fold; a fold with 0 or 1 makes that fold's
  Side I F1 meaningless and needs flagging, not silently averaging.
- Confirm no file appears in two folds, and that the duplicate pair landed together —
  both asserted in code, not just claimed.
- Row count sanity: 234 moving rows (272 − 38 stationary).

---

## Phase 4 — Baseline model + macro-F1 evaluation

Plan: `model.py` — train a baseline classifier (sklearn `HistGradientBoostingClassifier`,
class-balanced) via the 5-fold CV from Phase 3, report **per-class F1 and macro F1** for
each fold and the mean across folds. No hyperparameter tuning yet — this is the
"does the pipeline work end-to-end" checkpoint.

**Stop point — what to check and how:**
- The critical check: is macro F1 meaningfully above ~0.33? A number stuck near 0.33
  with Side I/II F1 near 0 means the model has collapsed to predicting Normal — signals
  a real problem (features, class weighting, or bug), not something to iterate past.
- Compare per-fold macro F1 variance — wildly inconsistent folds suggest the minority
  classes are too sparse per fold to trust single-run numbers (expected given n=14/24,
  worth discussing rather than silently accepting).
- I'll also report **plain accuracy alongside macro F1** in this step specifically so you
  can see the gap between them directly — a large gap (high accuracy, so-so macro F1) is
  expected and confirms the metric choice matters, not a bug.

---

## Phase 5 — Iteration / ablations

Plan: compare a few concrete variants against the Phase 4 baseline, all measured on the
same CV macro F1:
- mean-pooling-only features vs. mean+max+asymmetry (current) feature set
- single 3-way multiclass classifier vs. two independent binary detectors (Side I
  present? Side II present?) combined post-hoc
- with vs. without class weighting

**Stop point — what to check and how:**
- I'll present a small comparison table (variant → mean CV macro F1 ± std across folds).
- You pick which variant we ship, or ask for another variant — this is a judgment call,
  not something I'll decide unilaterally, since it's exactly the kind of choice the
  write-up needs to justify.

---

## Phase 6 — Reusable inference function

Plan: `predict.py` exposing `predict_rail(file_path) -> "Normal"/"Side I"/"Side II"`
(loads the trained model artifact once, wraps feature extraction), so the same function
can be imported by both the shared Streamlit app and a batch script — per the
submission constraint that inference logic must not be forked.

**Stop point — what to check and how:**
- I'll run it against a few known-label train files (held out from training, e.g. one
  fold's validation files) and show predicted vs. actual label.
- Check the function signature is something a teammate could import into
  `app/inference/rail.py` without modification — flag now if you want a different
  call shape (e.g. accepting a DataFrame instead of a path) before it's wired into the
  app.

---

## Phase 7 — Generate final predictions + sanity checks

Plan: run `predict_rail` over every file in `Test/` (68 files), write
`predictions/rail_predictions.csv` with exactly `file_id`, `prediction` columns.

**Stop point — what to check and how:**
- Row count exactly 68, one row per `Test1.csv`..`Test68.csv`.
- `prediction` values are exactly `Normal` / `Side I` / `Side II` (exact spelling/casing
  — this is graded mechanically).
- Open the CSV yourself and compare its class distribution to the train distribution —
  wildly different (e.g. 100% one class) is a red flag worth discussing before calling
  this done.

---

## Judgment calls log (carried into the write-up)

- [ ] Speed derivation convention (1 tooth = 1 rising edge vs. 2 transitions)
- [x] Asymmetry (diff/ratio) features — **keep**, but scoped honestly: strong on Side II
      (AUC 0.92), weak on Side I (AUC 0.69)
- [x] **Stationary files (38 train / 9 test, all Normal): excluded from model training,
      handled by an explicit `speed == 0 ⇒ Normal` rule at inference**
- [x] Duplicate raw files: `Train107`==`Train115` forced into the same CV fold;
      `Train165`==`Train187` removed automatically as stationary
- [x] Stratified k-fold (k=5) **by label alone** — the stationary dimension is constant
      once stationary rows are excluded
- [ ] `asym_diff_shock_dominant_wavelength_m_max` is constant 0.0 across all rows —
      drop as degenerate (harmless to trees, but shouldn't ship in the feature list)
- [ ] Mean+max+std pooling vs. simpler aggregation
- [ ] Single multiclass model vs. two binary detectors
- [ ] Any oversampling/class-weighting choice
- [ ] Mean+max+std pooling vs. simpler aggregation
- [ ] Single multiclass model vs. two binary detectors
- [ ] Any oversampling/class-weighting choice
