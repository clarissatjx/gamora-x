# SHM subsystem — plan and results

Owner: SHM lead. Scope: `data/SHM/Test/*.csv` → scored `shm_predictions.csv`, plus the SHM page of
the shared app. Team context in [PLANNING.md](../../PLANNING.md); spec in
[references/SHM/SHM_Info_Kit.md](../../references/SHM/SHM_Info_Kit.md).

## 0. Facts established from the data (don't re-derive these)

| Fact | Value | Why it matters |
|---|---|---|
| File format | one headerless column of stress values, **581,120 samples**, every file | Loader must not expect a header; equal length means no per-file duration term |
| Labels | 64 files, damage 0.029–0.928, median 0.099, p75 0.39 | 32× spread, skewed low → MAPE is dominated by small-damage files; model in log space |
| Generator | labels ∝ **Σ nᵢ·σᵢ⁵** over a standard rainflow count | log-log slope vs S₅ is 0.9965 ≈ 1, r = 0.9994; score peaks at exactly m = 5 and falls off both sides |
| Rainflow convention | ASTM 3-point, trailing residual counted ×0.5 | ×0 → 0.881, ×1 → 0.942, ×0.5 → 0.973; 4-point converges to the same |
| Ruled out (each scores lower) | Goodman and SWT mean-stress corrections, endurance cutoff, bilinear S-N, range binning, additive offset | The reference is *pure* Miner with one exponent; adding physics that isn't there hurts |
| Best scale estimator | `C = median(S₅ / D)` | 0.9744 LOO vs 0.9729 for the geometric mean; MAPE-optimal C overfits (0.928) |
| Residual correction | ridge (α = 1) on 7 cycle features, clipped ±20% | 0.9778 LOO; all standardised coefficients < 0.08, so it is a gentle trim |
| Test vs train | all 16 Test files inside the Train S₅ range; predictions 0.029–0.828 vs labels 0.029–0.928 | No distribution shift to worry about |
| Constant-guess floor | 0.085 | Anything near 0.97 is real signal, not the metric being easy |

## 1. Module layout

```
subsystems/shm/
├── PLAN.md
├── loader.py       # load_series(path) -> np.ndarray, with plain-language errors
├── rainflow.py     # reversals(), count(), cycles(); self-test vs the ASTM E1049 example
├── model.py        # M = 5, FEATURES, miner_sum(), cycle_features()
├── scoring.py      # mape_score(), score_frames(); self-test vs the Info Kit example
├── train.py        # builds the feature table, LOO gates, fits C + ridge -> model.joblib
├── predict.py      # analyse() breakdown, predict(), predict_many(); CLI --input file|dir --output
├── evaluate.py     # LOO recap + Test drift check -> SHIP / INSPECT
├── model.joblib
└── artifacts/train_features.csv   # 64 rows, cached so evaluate/app need no re-count
```

No new dependencies: rainflow counting is implemented in `rainflow.py` (≈40 lines) rather than
adding the `rainflow` package, and is verified against that package's documented example.

## 2. Steps and gates (all passed)

| Step | Gate | Result |
|---|---|---|
| loader | 581,120 finite floats; header / 2-column / empty files rejected with a sentence | ✅ |
| rainflow | ASTM example `[-2,1,-3,5,-1,3,-4,4,-2]` → `{3:0.5, 4:1.5, 6:0.5, 8:1.0, 9:0.5}` | ✅ exact |
| scorer | Info Kit example → 0.850; constant 0.5 → 0; perfect → 1 | ✅ |
| train | analytic LOO ≥ 0.96; correction only enabled if it beats analytic on LOO | ✅ 0.9744 → 0.9778, enabled |
| predict | 16 rows, `file_id, prediction`, natural file order, all positive, no NaN | ✅ |
| evaluate | 0 Test files outside train S₅ range; 0 predictions >20% outside label range | ✅ SHIP |
| app | SHM page: metrics, stress trace with top excursions, damage-share histogram, "how the value was built" steps, table, download; `process()` == CLI to 1e-12 | ✅ |

Commands: `python -m subsystems.shm.train` · `python -m subsystems.shm.evaluate` ·
`python -m subsystems.shm.predict --input data/SHM/Test --output predictions/shm_predictions.csv`

## 3. Decisions (and why)

- **Physics first, ML second.** With 64 samples, a one-parameter model that *is* the generator
  beats any regressor on robustness and explainability. The ridge term exists only because LOO
  says it helps (+0.34 pts); the training gate disables it automatically if that ever stops
  being true, and the ±20% clip means an unusual file cannot get a wild correction.
- **Median-ratio scale, not least squares.** The few noisiest files are low-damage ones where
  S₅ depends on a handful of large cycles; the median ignores them when fitting C.
- **Leave-one-out, not a fixed split.** Files are independent segments with random IDs (Info
  Kit), so LOO is valid and uses all 64 labels; a fixed 20% holdout would rest on ~13 files.
- **Damage shown alongside its derivation.** The app's "how the value was built" panel is the
  actual computation (cycles → S₅/C → ×correction → damage), not a narrative.

## 4. Write-up notes

- The S-N exponent was *recovered*, not assumed: grid over m ∈ [2, 10] on LOO score peaks at
  5.0 (0.9729) with 4.95 → 0.9687 and 5.05 → 0.9725.
- Worst LOO file is train12 at 9.3% relative error (damage 0.055); the four next-worst are all
  ≤ 7.1%. Every large miss is a low-damage file, as the metric's weighting predicts.
- Residual caveat: the ridge correction is fitted on 64 files; its LOO gain is small, and a
  reviewer could reasonably ask for the analytic-only number (0.9744) — both are recorded in
  the model bundle and shown in the app sidebar.

## 5. Done

- [x] Pipeline, gates, `model.joblib`, `predictions/shm_predictions.csv`
- [x] App page wired, verified in Chrome, app path == CLI
- [ ] Demo recording of the SHM tab
- [ ] Write-up paragraph (numbers above)
