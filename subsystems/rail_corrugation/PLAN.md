# Rail Corrugation — Build Plan

Working plan for the Rail Corrugation subsystem (3-class: Normal / Side I / Side II,
scored on macro F1). Each phase below ends with a **stop point** — I pause, you check the
listed things, and we move on once you're satisfied. Nothing in a later phase gets built
on top of an earlier one until you've signed off.

Code lives in `subsystems/rail_corrugation/`. Data lives at
`data/data/Rail_Corrugation/{Train,Test}/` + `Train_Labels.csv`.

**Scope: this subsystem only — the model, and the `rail_predictions.csv` it produces.**
The shared app is explicitly **not** part of this work and is owned elsewhere. What this
subsystem owes any integrator is a clean importable inference function (Phase 6); wiring it
into anything is someone else's call.

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

**Refinement made while building:** rather than forcing `Train107`/`Train115` into the
same fold, I **dropped `Train115`**. A byte-identical duplicate carries no additional
information, and keeping it would double-weight that one Normal sample in training. Fewer
moving parts, and plain `StratifiedKFold` then gives exact stratification rather than the
approximate balancing of `StratifiedGroupKFold`.

### Result (DONE, pending your check)

File: `split.py` — exports `load_training_frame()` and `make_folds()`, which Phases 4–5
import so the exclusions can't silently diverge between scripts.

```
All train rows:            272
  - stationary excluded:    38
  - duplicates dropped:      1  (Train115.csv)
Modelling frame:           233 rows, 240 features
Class counts: Normal 195 / Side II 24 / Side I 14
```

| fold | n | Normal | Side I | Side II |
|---|---|---|---|---|
| 0 | 47 | 39 | 3 | 5 |
| 1 | 47 | 39 | 3 | 5 |
| 2 | 47 | 39 | 3 | 5 |
| 3 | 46 | 39 | **2** | 5 |
| 4 | 46 | 39 | 3 | 4 |

All assertions passed: folds cover every row exactly once, no row in two folds, every fold
has ≥2 of each minority class, no stationary/duplicate rows survive, `file_id` unique, no
near-constant features survive.

### Independent review of Phase 3 — outcomes

**Near-duplicate leakage: checked and clean.** The worry was that files recorded from the
same run seconds apart would be highly correlated without being byte-identical, which would
make ungrouped `StratifiedKFold` unsound. Pairwise nearest-neighbour distances over the
233×239 z-scored feature matrix are smoothly unimodal (min 8.06, median 12.23,
mean 12.74 ± 2.82) — no tight cluster, no evidence of run-grouping. **Ungrouped stratified
k-fold is sound here.** (A first pass using raw cosine similarity looked alarming — median
0.93 — but that's an artifact of these features being mostly non-negative magnitude
statistics sharing a "loudness" direction; standardised Euclidean is the trustworthy metric.)

**A second degenerate feature, with a root cause worth knowing.**
`asym_ratio_shock_dominant_wavelength_m_max` is constant (std 2.7e-9) — but *only in the
modelling frame*, which is why the first pass missed it: across all 272 rows it varies
(0 for stationary files, 1 for moving), and only becomes constant once stationary files are
excluded. Root cause: `dominant_wavelength_m = speed / dominant_freq`, so the **max**
wavelength over a side's channels is set by the **lowest** dominant frequency — which
saturates at the first FFT bin (1 Hz, since the window is exactly 1 s). Both sides hit that
floor on every file, so max-wavelength collapses to `speed` on both sides: difference
exactly 0, ratio exactly 1. Confirmed: `Side_{I,II}_shock_dominant_wavelength_m_max`
correlate **+1.000** with `speed_mps`.

Both are now excluded (239 features), and `split.py` asserts no near-constant feature
survives, so this can't silently recur.

**Broader implication for Phase 5:** most *per-side* wavelength features correlate 0.78–0.98
with speed — they are largely speed in disguise. The *asymmetry* versions correlate only
−0.21 to +0.18 with speed, i.e. they carry genuine side-contrast information. This motivates
a feature-pruning ablation in Phase 5 rather than assuming all 239 features earn their place.

**Honest caveat to carry into Phase 4:** fold 3 validates Side I on **2 files**. One
misclassification there swings that fold's Side I recall by 50 points. Per-fold Side I F1
will be very noisy — we should read the *mean across folds* and expect a wide spread, not
treat any single fold as signal. This is a hard data limit (n=14), not something to tune away.

**Stop point — what to check and how:**
- Re-run `python -m subsystems.rail_corrugation.split` — it self-checks via assertions, so
  a silent pass means the coverage/overlap/minority-count guarantees actually hold.
- Sanity-check the arithmetic yourself: 272 − 38 stationary − 1 duplicate = 233. ✓
- Feature count dropped 241 → 240: the degenerate constant feature
  (`asym_diff_shock_dominant_wavelength_m_max`) is now excluded via `feature_columns()`.
- Judgment call to weigh in on: dropping `Train115` vs. keeping it grouped into one fold.

---

## Phase 4 —    (DONE, pending your check)

File: `model.py` — `HistGradientBoostingClassifier(class_weight="balanced")`, fit fresh
inside each of the 5 folds, no tuning. `cross_validate()` / `pooled_scores()` are written
for reuse so every Phase 5 ablation is measured identically.

### Results

| | F1 Normal | F1 Side I | F1 Side II | **macro F1** | accuracy |
|---|---|---|---|---|---|
| mean across folds | 0.965 | 0.593 | 0.841 | **0.800** (sd 0.022) | 0.936 |
| pooled out-of-fold | 0.965 | 0.609 | 0.851 | **0.808** | 0.936 |
| always-Normal reference | — | 0 | 0 | **0.304** | 0.837 |

Out-of-fold confusion matrix (rows = true):

| | Normal | Side I | Side II |
|---|---|---|---|
| **Normal** | 191 | 2 | 2 |
| **Side I** | **6** | 7 | 1 |
| **Side II** | 4 | 0 | 20 |

**Accuracy 0.936 vs macro F1 0.808** — exactly the gap the metric exists to expose. A model
tuned on accuracy would look near-perfect while missing half the Side I faults.

### What this tells us

- **Side I recall is the bottleneck: 7/14 = 0.50.** Six of fourteen Side I files are
  predicted Normal. Side I precision is fine (7/9 = 0.78) — the model is *missing* Side I
  faults, not over-calling them. Everything in Phase 5 should target recall on this class;
  lifting it from 0.50 to ~0.70 would take macro F1 from ≈0.81 to ≈0.85.
- Side II is in good shape (recall 20/24 = 0.83, precision 0.87), consistent with its
  AUC 0.92 on the asymmetry feature.
- Per-fold Side I F1 swings 0.50–0.80 (sd 0.136) exactly as the Phase 3 caveat predicted —
  read the pooled number, not any single fold. This is why Phase 5 uses repeated CV.
- **The stationary-exclusion decision cost us nothing in estimate fidelity.** Adding the
  stationary files back as free correct Normals moves macro F1 only 0.808 → **0.810**,
  because Normal F1 was already near ceiling and macro F1 weights it equally with the rare
  classes. The "inflated score" worry turned out to be negligible *for this metric* — good
  news, since we got the honesty benefit for free.

**Stop point — what to check and how:**
- Re-run `python -m subsystems.rail_corrugation.model` and confirm you get macro F1 ≈ 0.81.
  It's seeded (`random_state=42`), so it should reproduce exactly — if it doesn't, something
  is nondeterministic that shouldn't be.
- The critical check, now passed: macro F1 0.808 is far above the 0.304 always-Normal
  collapse, and no class has F1 near 0. The model genuinely detects both fault types.
- Sanity-check the confusion matrix against the per-class F1s yourself — e.g. Side I
  recall 7/14 and precision 7/9 give F1 = 2·(0.778·0.5)/(0.778+0.5) = 0.609. ✓
- Judgment call for Phase 5: is lifting Side I recall worth trading a little Normal
  precision for? Macro F1 says yes (Normal F1 has room to fall from 0.965 before it costs
  as much as Side I gains), but it's your call how aggressively to push it.

### Independent review of Phase 4 — outcomes

**Reproduced exactly**, CV harness verified correct (fresh estimator per fold, positional
alignment of out-of-fold predictions confirmed by assertion, nothing fit outside the fold's
training portion).

**macro F1 0.808 is a typical draw, not a lucky seed.** Over 30 seeds: mean 0.801, median
0.803, sd 0.030, range [0.736, 0.845]. Seed 42 sits on the median. **Expect the real test
score anywhere in roughly [0.73, 0.85]** — with n=14 Side I, that spread is irreducible.
This noise floor (sd ≈ 0.03) is the bar any Phase 5 "improvement" must clear to be real.

**A claimed improvement that did not survive checking.** The review reported that
`class_weight=None` beat `"balanced"` (0.832 vs 0.808) — but measured on a single seed,
precisely the trap repeated CV exists to avoid. Re-measured over 15 seeds:

| setting | macro F1 |
|---|---|
| `class_weight="balanced"` | 0.8019 ± 0.0323 |
| `class_weight=None` | 0.7937 ± 0.0348 |

Per-seed difference (None − balanced) = **−0.008 ± 0.034**; None wins on only 6/15 seeds.
The apparent +0.024 advantage was noise. **Keep `balanced`** — marginally better on average
and more defensible for an imbalanced problem. Recorded because it's a concrete
demonstration of why single-seed ablations get thrown out.

### Side I diagnosis (`diagnose_side_i.py`) — the real finding

Within Side I, `corr(speed, asymmetry) = −0.755`, far stronger than Normal (−0.17) or
Side II (−0.27). The asymmetry signature **weakens and then inverts sign as speed rises**,
and the three fastest Side I files in the dataset (18.4, 18.5, 18.6 m/s) are all missed,
all with negative asymmetry. All 7 caught files have positive asymmetry; 4 of 7 missed are
negative or near-zero.

But the high-speed regime (>17 m/s, n=24) is only *partly* exploitable:

| class (>17 m/s) | n | mean asym | range |
|---|---|---|---|
| Normal | 17 | −0.0135 | [−0.064, +0.048] |
| **Side I** | **3** | −0.0513 | [−0.086, −0.016] |
| Side II | 4 | −0.1261 | [−0.183, −0.072] |

At high speed, Side I lands *between* Normal and Side II — same sign as Side II, so the
feature no longer identifies *which* side. Per-file: `Train202` (−0.086) is beyond every
high-speed Normal but sits squarely in Side II's range (so pushing on it risks a Side II
misclassification — and indeed one Side I file is already predicted Side II); `Train185`
(−0.053) is borderline at the 6th percentile of Normal; **`Train180` (−0.016) sits at the
59th percentile of high-speed Normal — genuinely indistinguishable, not fixable by
conditioning on speed.**

**What this means for Phase 5.** The suggested fix (residualise asymmetry against speed) is
worth testing but oversold: at most it addresses 2 of 7 misses, and it is being designed
against **n=3** high-speed Side I files, so any measured gain is far inside the ±0.03 noise
floor. The tree can already express speed interactions natively, so explicit
residualisation only helps by making that interaction easier to learn from few samples.

A more principled alternative to test alongside it: because corrugation has a characteristic
*wavelength*, its excitation frequency scales with speed. Computing band power in
**speed-scaled frequency bands** (equivalently, binning the spectrum by wavelength rather
than frequency) is speed-invariant by construction, rather than correcting for speed after
the fact. That targets the root cause instead of patching the symptom.

**Discipline for Phase 5: treat any gain under ~0.03 macro F1 as unproven**, and prefer the
simpler model when two variants tie.

---

## Phase 5 — Iteration / ablations

**Use `RepeatedStratifiedKFold(n_splits=5, n_repeats=5)` for all ablation comparisons**, not
the single-seed 5-fold. With 2–3 Side I per validation fold, a single seed's macro F1 is
noisy enough that we could easily select a variant that won on a lucky split. 25 fits of
`HistGradientBoostingClassifier` on 233×239 is seconds of compute — cheap insurance against
choosing on noise. Report mean ± std across repeats.

Variants to compare against the Phase 4 baseline:
- mean-pooling-only features vs. mean+max+asymmetry (current) feature set
- **feature pruning**: drop the per-side wavelength features that are largely speed proxies
  (0.78–0.98 correlation with speed), keep the asymmetry versions
- single 3-way multiclass classifier vs. two independent binary detectors (Side I
  present? Side II present?) combined post-hoc
- with vs. without class weighting
- anything that specifically targets **Side I**, the bottleneck class (AUC 0.69 on the
  headline asymmetry feature vs 0.92 for Side II)

**Leakage discipline for this phase:** `HistGradientBoostingClassifier` needs no scaling, but
if any variant introduces scaling, imputation, or SMOTE-style oversampling, it must be fit
**inside** each fold, never on the full 233-row frame.

### Results (DONE, pending your check)

Files: `ablations.py` (8 variants), `threshold_tuning.py` (decision-rule sweep). Each
variant scored identically: 5 independent 5-fold CVs, pooled macro F1 per repeat, then
mean ± sd across repeats.

| variant | n_feat | macro F1 | sd | F1 Normal | F1 Side I | F1 Side II |
|---|---|---|---|---|---|---|
| **A. baseline (all features)** | 239 | **0.806** | 0.029 | 0.970 | 0.570 | 0.878 |
| G. speed-residualised asymmetry | 239 | 0.805 | 0.036 | 0.970 | 0.582 | 0.863 |
| E. no class weighting | 239 | 0.795 | 0.015 | 0.966 | 0.547 | 0.873 |
| C. drop wavelength family | 217 | 0.791 | 0.037 | 0.972 | 0.542 | 0.859 |
| F. two binary detectors | 239 | 0.762 | 0.042 | 0.960 | 0.477 | 0.849 |
| H. compact + residualised | 109 | 0.613 | 0.019 | 0.930 | 0.220 | 0.690 |
| D. compact (asym, no wavelength) | 109 | 0.609 | 0.027 | 0.931 | 0.189 | 0.707 |
| B. asymmetry only | 119 | 0.597 | 0.025 | 0.927 | 0.189 | 0.676 |

Plus a fault-probability boost sweep (bias the decision rule toward the fault classes,
trading Normal precision for fault recall — macro F1 should reward this since Normal F1 has
headroom at 0.97):

| boost | macro F1 | F1 Normal | F1 Side I | F1 Side II |
|---|---|---|---|---|
| 1.0 (default argmax) | 0.806 | 0.970 | 0.570 | 0.878 |
| 4.0 | 0.803 | 0.967 | 0.584 | 0.858 |
| 8.0 | 0.808 | 0.967 | 0.600 | 0.856 |

**Conclusion: nothing beats the baseline. Ship variant A unchanged.**

### What was learned (this is the write-up material)

Five hypothesised improvements were tested and **all five were rejected**:

1. **Feature pruning — my own hypothesis, and badly wrong.** I argued from the Side I
   diagnosis that 239 features against 14 minority examples was diluting the model, since
   `Train194` (asymmetry +0.128, higher than most *caught* files) was still predicted Normal.
   Pruning to asymmetry-only was **catastrophic**: Side I F1 collapsed 0.570 → 0.189. The raw
   per-side features carry most of the signal; the asymmetry features are valuable *in
   addition to* them, not as a replacement. Gradient boosting handled the wide feature set
   fine — the dilution worry was unfounded.
2. **Speed-residualised asymmetry** (the reviewer's recommendation): a wash (0.805 vs 0.806).
   It did shift the trade as predicted — Side I F1 up 0.570 → 0.582, Side II down 0.878 →
   0.863 — but netted nothing, consistent with it addressing at most 2 of 7 misses.
3. **Two binary detectors instead of one 3-way model**: clearly worse (0.762). The single
   multiclass model wins.
4. **`class_weight=None`**: worse (0.795 vs 0.806) — a third independent measurement now
   agreeing that `balanced` is correct, after the single-seed result that suggested otherwise.
5. **Fault-probability boosting**: +0.002, deep inside noise. It does lift Side I F1 to 0.600
   at boost 8.0, but gives back an equal amount on Side II. The trade the metric appeared to
   favour is real in direction but self-cancelling in magnitude.

**The Side I ceiling is a data limit, not a modelling deficiency.** With 14 examples, several
genuinely overlapping with Normal in feature space (`Train180` sits at the 59th percentile of
high-speed Normal files), no reweighting, decomposition, or feature transform tested here
moves it. Believing otherwise would require reading a sub-noise gain as signal.

**Methodological note worth stating in the write-up**: every variant was judged against a
pre-declared ±0.03 noise floor measured over 30 seeds *before* the ablations were run, not
chosen after seeing results. That is why five plausible ideas were rejected rather than one
lucky seed being promoted.

**Stop point — what to check and how:**
- Re-run `python -m subsystems.rail_corrugation.ablations` (a few minutes) and
  `python -m subsystems.rail_corrugation.threshold_tuning`; both are seeded and should
  reproduce the tables above.
- Sanity-check the headline conclusion: does any variant beat A by more than 0.03? (No.)
- Judgment call: accept "ship the baseline" and move to Phases 6–7, or is there a variant
  you want tested that I haven't covered?

---

## Phase 6 — Reusable inference function (DONE, pending your check)

Files: `train_final.py` (fits variant A on all 233 rows, saves
`artifacts/rail_model.joblib`, 723 KB), `predict.py` (the single inference path),
`verify_inference.py` (correctness checks).

### The interface a teammate imports

```python
from subsystems.rail_corrugation.predict import predict_rail, predict_rail_detailed

predict_rail(source)           # -> "Normal" | "Side I" | "Side II"
predict_rail_detailed(source)  # -> dict: prediction, speed_mps, probabilities,
                               #    stationary_rule_applied, explanation
predict_directory(path)        # -> DataFrame in exact rail_predictions.csv schema
```

`source` is a path **or any file-like object**, so a caller holding an uploaded file can pass
it straight through without writing it to disk. The model artifact is cached at module
level, so it loads once rather than per call.

`predict_rail_detailed` returns class probabilities, the derived train speed, and a
plain-English `explanation` alongside the label — including when the stationary rule fired
instead of the model. Whoever consumes this subsystem can surface as much or as little of
that as they need; `predict_rail` is the minimal label-only contract.

The **`speed == 0 ⇒ Normal` rule lives inside this path**, so every caller gets it
automatically and no two callers can diverge. The feature column list is saved *inside* the
artifact, so inference can't silently reorder columns relative to training.

A CLI is also provided (`--input` / `--output`), covering the `predict.py` interface the
Info Kit mentions, in case the organisers do require it — see the open question in the
repo-level PLANNING.md about whether that's actually compulsory.

### Verification (`verify_inference.py`)

1. **Feature parity** — features rebuilt through the inference path match the cached
   training table to **4.5e-13** (pure float/CSV round-off). This is the check that catches
   the classic "features built differently at inference than at training" bug.
2. **End-to-end** on one file per class: Normal→Normal, Side I→Side I, Side II→Side II,
   stationary→Normal via the rule. *These files were in training, so this verifies plumbing,
   not accuracy — the honest accuracy number remains the CV macro F1 of 0.806.*
3. **Stationary rule fires** and returns no probabilities, as designed.
4. **File-handle input** gives the same answer as a path.

**Stop point — what to check and how:**
- Run `python -m subsystems.rail_corrugation.verify_inference` — it asserts, so a clean pass
  means the guarantees hold.
- Review the interface above: is this the call shape you want to hand to whoever integrates
  this subsystem? Flag now — changing it after other code depends on it is more disruptive.
- Try the CLI: `python -m subsystems.rail_corrugation.predict --input <a test file>`.

---

## Phase 7 — Generate final predictions + sanity checks (DONE, pending your check)

File: `generate_predictions.py` → **`predictions/rail_predictions.csv`**. It calls the same
`predict_directory` path as every other caller, so the submission file is produced by the
shipped inference logic rather than a one-off script.

### Schema checks (asserted in code, not just eyeballed)

Columns exactly `file_id,prediction`; 68 rows; `Test1.csv`..`Test68.csv` all present and
unique; every `file_id` carries the `.csv` extension; every label is exactly `Normal`,
`Side I`, or `Side II`; no nulls. All pass. A formatting slip here forfeits the subsystem's
entire score regardless of model quality, which is why these are assertions.

### Predicted distribution

| class | test n | test % | train % (moving) |
|---|---|---|---|
| Normal | 59 | 86.8 | 83.7 |
| Side I | 5 | 7.4 | 6.0 |
| Side II | 4 | 5.9 | 10.3 |

The nine fault predictions are `Test13, 22, 27, 33, 46` (Side I) and
`Test14, 26, 43, 66` (Side II). Of the 59 Normal predictions, **9 come from the stationary
rule** rather than the model.

Normal and Side I track the training distribution closely. **Side II comes in lower than
training (5.9% vs 10.3%)** — worth noting rather than glossing: with ~59 moving test files,
a matching rate would imply ~6 Side II, and at the model's measured Side II recall of 0.83
we would expect ~5. Predicting 4 is inside sampling noise at these counts, but it is the one
number in this table that isn't a close match, so it belongs in the write-up as an observation
rather than being quietly ignored.

**Stop point — what to check and how:**
- Re-run `python -m subsystems.rail_corrugation.generate_predictions`; it self-asserts.
- Open `predictions/rail_predictions.csv` — confirm 69 lines (68 + header), no index column,
  and no stray whitespace.
- Compare against the organisers' `04_Example_Submission/rail_predictions.csv` for format.
- Judgment call: accept the Side II rate as sampling noise, or investigate further?

---

## Phase 8 — Wavelength-band features: tested and rejected

A final review asked whether anything was still missing, and identified the most
physically-motivated gap: the spectral features were coarse (one dominant frequency, one
centroid, one energy ratio per channel — **no band structure**), while the Info Kit describes
the actual detection method as *"time-frequency analysis extracts the dominant wavelength"*.
Corrugation is defined by its wavelength, and a defect of wavelength L excites the axle box
at `f = speed / L` — so a band fixed in **wavelength** tracks the same physical defect across
speeds, whereas our frequency-domain features do not.

An exploratory check supported this: power in a 0.12–0.25 m wavelength band gave Side I
one-vs-rest **AUC 0.813**, far above the 0.69 of the existing headline asymmetry feature, and
correlated only 0.33 with it — genuinely new information.

**Implementation.** Relative power in five log-spaced wavelength bands spanning 2–64 cm (the
Info Kit's stated "few centimetres to dozens of centimetres"), per channel, aggregated by
side × signal type, with asymmetry versions generated automatically: +120 features, 241 → 361.
The bands were fixed **a priori from the documented physical range, not tuned against measured
separability** — choosing bands by what scores best on training labels is a
multiple-comparisons trap, and the exploratory 0.813 above was itself the best of six bands
tried, so it was already optimistic.

**Result: rejected. The features actively hurt.**

| variant | n_feat | macro F1 | F1 Side I |
|---|---|---|---|
| **pre-band baseline** | 239 | **0.806** | **0.570** |
| + band asymmetry only | 299 | 0.771 | 0.494 |
| + wavelength bands (all) | 359 | 0.768 | 0.475 |

Adding them cost **0.038 macro F1** and **0.10 on Side I** — larger than the ±0.03 noise
floor, so a real degradation rather than a wash.

**Why this is worth recording.** A feature with strong *univariate* separability still damaged
the *multivariate* model, because it arrived as 120 correlated columns against 233 rows with
14 Side I examples. It is the mirror image of the Phase 5 pruning result: that experiment
showed removing features hurts, this one shows adding them hurts too. The 239-feature set sits
near a local optimum for this dataset size, and the binding constraint is the number of Side I
examples, not the richness of the representation.

The feature code was reverted rather than left disabled, so `features.py` reflects what
actually ships. `config.py` and `features.py` are byte-identical to their pre-experiment
state, and the regenerated `rail_predictions.csv` is unchanged.

---

## Speed convention — resolved from evidence, not assumed

Phase 1 flagged the one genuinely open modelling assumption: does one tooth passing the
sensor produce **one** rising edge (so `revolutions = rising_edges / 90`) or **two**
transitions (halving the derived speed)? The Info Kit doesn't state it outright, and the
choice scales every speed value by 2×.

It scales all files identically, so it cannot change the classifier's decisions — but it
does change whether the reported speeds mean anything physically, and the `dominant_wavelength`
features derive from it. Three independent checks resolve it in favour of the shipped
convention:

1. **Duty cycle.** The pulse train is high 50.0–50.9% of the time, and rising edges exactly
   equal falling edges on every file inspected. Teeth and gaps are therefore equal width —
   a standard toothed wheel — so each tooth contributes exactly one rising edge, giving 90
   rising edges per revolution, not 180.
2. **The Info Kit's own wording.** "When a tooth enters and leaves the detection point, the
   sensor output toggles between 1 and 0" describes two *transitions* per tooth but only one
   *rising* edge per tooth — consistent with (1).
3. **Physical plausibility.** Under the shipped convention the fleet runs at mean 37 km/h and
   max 70 km/h, squarely typical metro operation. The doubled convention implies mean
   74 km/h and max 140 km/h, implausible on a line the Info Kit itself describes as having
   "many sharp curves, frequent acceleration and deceleration".

**Conclusion: `revolutions = rising_edges / 90` is correct**, and the derived speeds are
physically meaningful rather than merely internally consistent. This closes the last open
judgment call.

---

## Phase 9 — Independent review after the held-out score (0.888)

Reviewed on the merged branch by the Door/SHM owner, using the same paired repeated-CV harness
(5 repeats × 5-fold, identical folds per repeat, pooled macro F1, ±0.03 noise floor). Every
hypothesis below was written down before it was run.

**Hyperparameters — never tuned before, now closed from both sides.** The default
`min_samples_leaf=20` exceeds the whole Side I class (14), so *smaller* leaves were expected to
help. They hurt, monotonically; and *larger* leaves hurt more. The default is a sharp optimum.

| config | macro F1 | Side I F1 | gain | wins/5 |
|---|---|---|---|---|
| **baseline (defaults)** | **0.806** | **0.570** | — | — |
| msl=10 / 5 / 3 | 0.753 / 0.746 / 0.758 | 0.47 / 0.44 / 0.49 | −0.05 to −0.06 | ≤1 |
| msl=30 / 40 | 0.726 / 0.662 | 0.43 / 0.33 | −0.08 / −0.14 | 0 |
| leaves=15 / 7, it=50 / 200, lr=.05 | 0.773–0.806 | 0.49–0.57 | −0.03 to 0.00 | ≤1 |
| l2=1.0 | 0.815 | 0.587 | +0.009 | 3 |

**Two more feature ideas — both rejected.** (1) A *single* pre-registered wavelength band
(0.12–0.25 m, relative power, per-side means + asymmetry diff/log-ratio: 4 features), the
middle ground between the headline feature and the 120-column Phase 8 set. (2) Per-axle
left/right log-ratios of channel std (positions 1/2, 3/4, 5/6, 7/8 share an axle, so the ratio
cancels per-car sensor scale): 6 features.

| variant | macro F1 | Side I F1 | gain | wins/5 |
|---|---|---|---|---|
| + band (4) | 0.797 | 0.550 | −0.009 | 0 |
| + axle (6) | 0.797 | 0.547 | −0.009 | 0 |
| + both (10) | 0.797 | 0.549 | −0.009 | 2 |

Univariate Side I AUC: band asymmetry 0.750 (vs the exploratory 0.813, which was best-of-six),
per-axle max 0.747, headline `asym_diff_vib_rms_mean` 0.715. Better single features, no
multivariate gain. The code was reverted per the Phase 8 convention.

**Round 2 — three further ideas, all rejected** (same paired protocol):

| variant | macro F1 | Side I F1 | gain | wins/5 |
|---|---|---|---|---|
| + side-averaged, sensor-normalised spectra binned by wavelength (34 features) | 0.793 | 0.544 | −0.013 | 1 |
| demeaned shock time features (rms / zero-crossing) | 0.762 | 0.480 | −0.044 | 0 |
| ensemble of baseline and the spectrum view (mean probability) | 0.720 | 0.388 | −0.086 | 0 |
| 2 × 0.5 s window augmentation, file-grouped folds, probabilities averaged per file | 0.702 | 0.314 | −0.104 | 0 |
| spectrum view alone | 0.565 | 0.147 | −0.241 | 0 |

Two of these are findings, not just failures. (a) The shock channels carry a DC offset that
looks like sensor bias, but **demeaning it costs 0.044** — the offset differs between files in
a label-relevant way, so it must be left in. (b) The textbook corrugation detector — average the
32 channel spectra per side, bin by wavelength — is far *weaker* than per-channel statistics. In
a 1 s window a ~150 m train spans different track, so a corrugated section sits under only some
axle boxes; averaging across a side dilutes exactly those, while the `_max`-pooled per-channel
features (the ones permutation importance singles out) capture "the loudest box". Window
augmentation fails for the same reason.

**Conclusion, now supported twelve independent ways:** the 239-feature default-hyperparameter
model is a local optimum for this dataset — tuning in both directions, three feature families
added, one removed, two re-representations, augmentation and an ensemble all score lower; the
Side I ceiling is the 14 training examples. The 0.888 test score is above the 0.806 ± 0.03 CV estimate — a favourable draw on ~5 Side I test
files, where each file is ≈ ±0.04 macro F1 — and the write-up should present capability as
≈ 0.80, not 0.89.

**Bugs found (none affect the submitted score):**
- `artifacts/rail_model.joblib` is a numpy-2 pickle and fails to load on numpy 1.x. A local
  retrain from the cached feature table reproduces all 68 submitted predictions exactly, so
  `predict.py` now falls back to that (saved as an untracked `*.local.joblib`).
- `config.py` hard-coded `data/data/…`; it now accepts either layout.
- Not wired into the shared app (out of scope here by design); `predict_rail_detailed` is
  ready for it.

**Fragile test calls worth knowing about:** `Test14` (Side II at 18.8 m/s with asymmetry
−0.016, outside the high-speed Side II range) and `Test56` (Normal at 18.3 m/s, inside the
high-speed Side I range). Neither is resolvable without labels.

## Phase 10 — Spatial structure: measured, and it is not there

Asked whether the 64 channels support a *per-car* or per-wheel view ("show the engineer which
wheelset found the fault"). Measured before building anything: per-car asymmetry (that car's
Side I mean RMS minus its Side II mean RMS) across 14 Side I, 10 Side II and 12 Normal moving
files.

| class | mean per-car asymmetry | spread across the 8 cars | cars pointing the right way |
|---|---|---|---|
| Side I | +0.028 | 0.140 | **3.6 / 8** |
| Side II | -0.113 | 0.360 | **4.5 / 8** |

**Car-to-car variation is 5-9x larger than the fault signal**, and individual cars barely agree
with the verdict — 3.6/8 for Side I is at or below chance, and in **0 of 24 fault files did all
eight cars agree**. Whatever drives car-to-car differences (sensor variation, loading, bogie
condition) is far louder than corrugation.

File-level detection still works because averaging 32 channels per side cancels that noise
(~5.7x reduction) while the small consistent fault signal survives. **The signature is a
whole-train average phenomenon, not a localisable one.**

**Consequence for the UI:** a per-car or per-wheel "hotspot" display would show eight cars
disagreeing with each other and with a correct verdict, and would invite an engineer to hunt
for a bad wheel that does not exist in this data. Rejected on that basis. The honest display is
the two side-distributions against a healthy reference band, which shows that the decision is a
distributional call rather than a spot-the-defect exercise.

### Healthy side-asymmetry reference band (used by the UI)

Measured on the 195 moving Normal training recordings, feature `asym_diff_vib_rms_mean`:

| statistic | value |
|---|---|
| healthy mean | **-0.005** |
| healthy standard deviation | **0.034** |
| Side I fault mean | +0.031 (**1.1 sd** from healthy) |
| Side II fault mean | -0.109 (**3.1 sd** from healthy) |

**One sigma versus three** is the most compact statement of why Side II is detected well
(F1 0.878) and Side I poorly (F1 0.570): a Side I fault shifts the asymmetry by about as much
as healthy track varies on its own. These are the numbers `app/reliability.py` cites to give
the raw asymmetry figure a reference an engineer can judge against.

---

## Judgment calls log (carried into the write-up)

- [x] **Speed derivation: 1 tooth = 1 rising edge** (`revolutions = rising_edges / 90`).
      Resolved from evidence rather than assumed — see "Speed convention" below
- [x] Asymmetry (diff/ratio) features — **keep**, but scoped honestly: strong on Side II
      (AUC 0.92), weak on Side I (AUC 0.69)
- [x] **Stationary files (38 train / 9 test, all Normal): excluded from model training,
      handled by an explicit `speed == 0 ⇒ Normal` rule at inference**
- [x] Duplicate raw files: `Train115` dropped outright (byte-identical to `Train107`, so
      zero information lost); `Train165`==`Train187` removed automatically as stationary
- [x] Stratified k-fold (k=5) **by label alone** — the stationary dimension is constant
      once stationary rows are excluded
- [x] Two degenerate features dropped (`asym_{diff,ratio}_shock_dominant_wavelength_m_max`),
      both artifacts of max-wavelength saturating at the 1 Hz FFT bin ⇒ 239 features
- [x] Near-duplicate/run-grouping leakage checked in feature space — none found, so
      ungrouped stratified k-fold is sound
- [ ] **Write-up caveats to record**: (a) `speed_mps` is quantised to ~0.0297 m/s steps
      (π×0.85/90 per rising edge), so repeated identical speed values across files are a
      formula artifact, not duplicate recordings; (b) the asymmetry features were designed
      by inspecting labels across the whole training set — normal EDA, not test leakage, but
      it mildly optimism-biases CV vs. a fully blind pipeline
- [x] Pooling: **mean + max + std kept**. Phase 5 variants B/D/H, which cut the raw per-side
      features back to asymmetry summaries, collapsed Side I F1 from 0.570 to 0.15–0.25
- [x] **Single 3-way multiclass model**, not two binary detectors — the decomposition scored
      0.762 vs 0.806 (Phase 5 variant F)
- [x] **`class_weight="balanced"`**, no oversampling — measured three separate times;
      `None` scored 0.795 vs 0.806 under repeated CV, and SMOTE-style oversampling was not
      pursued because the class weighting already addresses the imbalance and adds a
      fold-fitting step that could leak if done carelessly
- [x] **Wavelength-band power features rejected** — see Phase 8; they cost 0.038 macro F1
      despite strong univariate separability
- [x] **Estimator family: HistGradientBoosting** — RandomForest 0.738, LogisticRegression
      0.714, SVC 0.675, ExtraTrees 0.606, all clearly worse under the same protocol
- [x] **No seed-averaging/bagging** — averaging 7 differently-seeded models per fold gave
      0.806, identical to a single model; the variance comes from fold composition (n=14
      Side I), not model-fit randomness
