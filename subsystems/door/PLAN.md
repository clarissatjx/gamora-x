# Door subsystem — concrete implementation plan

Owner: Door lead. Scope: everything needed to turn `data/Door/Test.csv` into a scored
`door_predictions.csv` plus the Door tab of the shared app. Team-level context is in
[PLANNING.md](../../PLANNING.md); the spec is in
[references/Door/Door_Subsystem_Info_Kit.md](../../references/Door/Door_Subsystem_Info_Kit.md).

## 0. Facts established from the data (don't re-derive these)

| Fact | Value | Why it matters |
|---|---|---|
| Sampling inside a cycle | exactly 0.02 s (50 Hz) | Any timestamp jump > 0.02 s is a boundary |
| Gap between cycles | 10.2 s – 58.8 s (Train), 11.1 s – 55.4 s (Test) | Threshold of 0.5 s is safe by 20x on both sides |
| Rows outside labelled cycles in Train | 0 | Gap-split has no spurious segments |
| Gap-split vs `Train_Segments_Answer.csv` | all 110 start/end timestamps match exactly | Segmentation IoU = 1.0; metric reduces to classification accuracy |
| Train cycles | 110 = 80 Normal / 30 Abnormal; 55 Close (~186 rows) / 55 Open (~142 rows) | Duration is set by Open/Close, not by status |
| Test cycles | 38 = 20 Close / 18 Open | One Open cycle is 185 rows (Train max 147) — inspect it |
| Best separating features | mid-travel mean current, total current, 75th-pct current: AUC 1.00 in both operations | Abnormal = more current, less back-EMF during travel |
| Useless features | peak current (AUC 0.00 Close / 0.49 Open), duration | Peak is the end-stop lock, not the travel |
| Baseline CV accuracy (26 features) | LogReg 98.2 %, RF 99.8 %, GB 99.1 %; all 100 % on last-22-cycle holdout | Target score ≈ 0.97–1.0 |
| Score floor | predict-all-Normal = 0.727 | Every mislabel on Test costs ≈ 0.026 |

## 1. Module layout

```
subsystems/door/
├── PLAN.md          # this file
├── loader.py        # load_stream(path) -> DataFrame with parsed 'ts' column  (not io.py: that name shadows stdlib io)
├── segment.py       # segment(df) -> DataFrame[seg_id, i0, i1, start_str, end_str]
├── features.py      # featurize(df, segs) -> DataFrame (one row per segment)
├── scoring.py       # iou_weighted_f1(true_df, pred_df) -> float   (official metric)
├── train.py         # CV report + fit final model -> model.joblib
├── predict.py       # predict(path) -> DataFrame[start_time, end_time, prediction, confidence]; CLI --input/--output
├── evaluate.py      # end-to-end: segment + classify Train holdout, score with scoring.py
└── model.joblib     # produced by train.py (commit it — it's tiny)
```

Dependencies already present in the conda base env: pandas 2.1, numpy 1.26, scikit-learn 1.3,
scipy 1.13, streamlit 1.37. Add `joblib` (ships with sklearn). No new installs needed.

## 2. Steps, in order, with pass/fail gates

### Step 1 — `loader.py` (15 min)
- `parse_ts(s)`: split on `-`, fields are Y-M-D-h-m-s-ms, **not zero-padded**, ms → microseconds ×1000.
- `load_stream(path)`: read CSV, add `ts` column, keep the raw `Datetime` string column untouched
  (it is emitted verbatim in the output).
- Gate: `load_stream('data/Door/Train.csv')` has 18 036 rows, `ts` strictly increasing.

### Step 2 — `segment.py` (30 min)
- Primary rule: new segment wherever `ts.diff() > 0.5 s`.
- Fallback (only if primary yields a single segment, i.e. a stream with no gaps): new segment
  where `|Δ Door leaf position| > 100` in one step, or where `Door is opening`/`Door is closing`
  changes. Do **not** use the command columns — `Open command` flips mid-cycle once in Train
  and would over-split. Verified: on de-gapped copies of Train and Test the fallback reproduces
  the gap-based boundaries exactly (110 and 38).
- Output per segment: `i0`, `i1` (row indices), `start_str = Datetime[i0]`, `end_str = Datetime[i1]`,
  `op` = `Close` if mean(`Door is closing`) > 0.5 else `Open`.
- Gate: Train → 110 segments whose `start_str`/`end_str` equal `Train_Segments_Answer.csv`
  exactly (string compare, no parsing). Test → 38 segments (20 Close / 18 Open).

### Step 3 — `scoring.py` (20 min, already prototyped)
Implement Info Kit §4 verbatim:
1. Candidate pairs: same label AND IoU > 0, where IoU is on `[start, end]` in seconds.
2. Greedy one-to-one matching, highest IoU first.
3. `soft_recall = ΣIoU / n_true`, `soft_precision = ΣIoU / n_pred`, score = harmonic mean (0 if both 0).

Gate (unit test, keep it in the file under `if __name__ == "__main__"`):
- true vs true → 1.0
- true vs all-labels-flipped → 0.0
- true vs all-Normal → 0.7273
- true vs end-times 0.5 s early → 0.8437

### Step 4 — `features.py` (45 min)
One row per segment. Let `c, v, e, p` be current, voltage, back-EMF, position arrays;
`mid = (p > 100) & (p < 600)`; `n = len(c)`.

| Feature | Definition |
|---|---|
| `op` | 1 = Close, 0 = Open |
| `n_rows` | n |
| `cur_mid` | mean(c[mid]) — the primary discriminator |
| `cur_mean`, `cur_med`, `cur_p25`, `cur_p75` | plain stats of c |
| `cur_first_half` | mean(c[: n//2]) |
| `cur_sum` | sum(c) |
| `volt_mean`, `volt_max` | stats of v |
| `emf_mid`, `emf_std` | mean(e[mid]), std(e) |
| `t_half` | first index where |p − p[0]| ≥ 350 (rows to half-travel) |

Rules: no feature may use anything outside the segment's own rows; no global statistics
(scaling is done inside the sklearn pipeline so it is fit on training folds only).
Gate: shape (110, 14) on Train, no NaNs; `cur_mid` AUC within each op ≥ 0.99.

### Step 5 — `train.py` (45 min)
- Labels: join segments to `Train_Segments_Answer.csv` on `start_str`. Assert 110 matches.
- Split strategy (state this in the write-up): cycles are independent events separated by
  ≥ 10 s, so **segment-level RepeatedStratifiedKFold (5×5, stratified on status×op)** is valid.
  Also report a **time-ordered holdout** (train first 88, test last 22) as the drift check.
- Models: `Pipeline(StandardScaler, LogisticRegression(C=1, max_iter=2000))` as the primary
  (probabilities → `confidence` column, coefficients → explainability), `RandomForest(300)` as
  the cross-check. Fit the primary on all 110 and save `model.joblib` together with the
  feature-column list.
- Gate: CV accuracy ≥ 0.97 for the primary; holdout accuracy ≥ 0.95. Print both plus the
  logistic coefficients (expect large positive weight on `cur_mid`, negative on `emf_mid`).

### Step 6 — `predict.py` (30 min)
- `predict(path) -> DataFrame` with columns exactly `start_time`, `end_time`, `prediction`,
  `confidence` (confidence is optional per the spec and ignored for scoring — keep it, the app
  uses it).
- `start_time`/`end_time` are the **verbatim `Datetime` strings** of the first/last row.
- `prediction` ∈ {`Normal`, `Abnormal resistance`} — exact strings, exact case.
- CLI: `python -m subsystems.door.predict --input data/Door/Test.csv --output predictions/door_predictions.csv`.
- Gate: running on `Train.csv` and scoring the output with `scoring.py` against the answer file
  gives ≥ 0.98 (this is in-sample; it only checks plumbing). Running on `Test.csv` gives 38 rows,
  no NaNs, only the two allowed labels.

### Step 7 — `evaluate.py` + drift check (30 min)
- End-to-end: segment + featurize + fit on first 88 cycles + predict last 22 + `scoring.py`.
  Report the score (expect ≥ 0.95). This is the number that goes in the write-up.
- Drift check on Test (this is the main real risk — the Info Kit warns distributions differ
  between doors):
  1. For each op, take Train's Normal-class max and Abnormal-class min of `cur_mid`; the
     interval between them is the class gap.
  2. Count Test cycles whose `cur_mid` lands in the *middle* of that gap (relative position
     0.25–0.75). Landing just past a tight cluster's edge is expected door-to-door drift and is
     not flagged — a first version flagged those and produced 10 false alarms.
  3. Count Test cycles with LogReg probability in [0.2, 0.8].
  4. Count Test cycles where LogReg and RF disagree.
  If all three counts are 0 → ship. If not → inspect those cycles (plot current vs position
  against a Normal and an Abnormal Train exemplar of the same op) before deciding the label.
- Inspect the 185-row Open cycle in Test explicitly, whatever the counts say.

### Step 8 — Streamlit tab (60 min, coordinate with whoever owns `app/`)
- `app/inference/door.py` imports `subsystems.door.predict.predict` — one implementation, no
  duplicate.
- Tab flow: `st.file_uploader` (csv) → run predict → `st.dataframe` of the segments →
  a line chart of motor current over time with each cycle shaded by predicted label
  (`Abnormal resistance` in a warning colour) → `st.download_button` producing the CSV with
  exactly the four columns above.
- Wrong-format upload (missing `Datetime` or `Motor current(mA)` column) → `st.error` with a
  plain-language message, not a traceback.

### Step 9 — Submission artefacts (20 min)
- `predictions/door_predictions.csv` generated **through the app**, not the CLI, so the demo
  video and the submitted file come from the same path. Diff it against the CLI output — they
  must be identical.
- Write-up paragraph covering: gap-based segmentation and its exact match on Train; segment-level
  stratified CV + time-ordered holdout as the split rationale; the physical mechanism (more
  current, less back-EMF under resistance); the drift-check results on Test.

Total ≈ 5 h including slack; Steps 1–4 are the critical path and can be done before the app
skeleton exists.

## 3. Decisions already made (and why)

- **Gap-based segmentation over signal-based.** It reproduces the labels exactly on Train and the
  same gap structure is present in Test. Signal-based detection would only add ways to be wrong.
  The fallback exists for robustness, not because it is expected to run.
- **Segment-level CV instead of a single contiguous holdout.** With only 30 Abnormal cycles a
  single holdout is too noisy; cycles are independent (≥ 10 s apart, position resets between
  them), so stratified K-fold over cycles does not leak. The time-ordered holdout is reported
  alongside to show there is no temporal drift within Train.
- **Logistic regression as primary.** Accuracy is saturated, so the choice is about robustness
  and explainability: a linear model on physically meaningful features extrapolates more sensibly
  under door-to-door shift than a forest, and its coefficients are the explainability story for
  the judges. RF is kept only as a disagreement detector.
- **Emit verbatim timestamps.** The answer file's `end_time` is literally the last row's
  `Datetime`; re-formatting timestamps can only introduce mismatch.

## 4. Done checklist (results as of 2026-09-18)

- [x] Step 2 gate: 110/110 exact boundary matches on Train; 38 segments on Test (20 Close / 18 Open); flag-derived Open/Close agrees with the answer file on all 110
- [x] Step 3 gate: four scorer unit values reproduce (1.0 / 0.0 / 0.7273 / 0.8437) — `python -m subsystems.door.scoring`
- [x] Step 5 gate: primary CV 0.982 ± 0.022 (RF 0.991); time-ordered holdout 1.000 for both; `model.joblib` (235 KB) saved
- [x] Step 6 gate: in-sample plumbing score 0.9909; Test output 38 rows, only the two allowed labels, no NaNs
- [x] Step 7: end-to-end holdout IoU-weighted F1 = **1.0000**; drift check ambiguous=0, uncertain=0, disagree=0 → SHIP.
      Test's Normal clusters sit 1–17 mA above Train's (Close 199–231 vs ≤214; Open 271–300 vs ≤287) while the
      class gap is ~100 mA, so the shift is real but harmless. Test predictions: 30 Normal / 8 Abnormal.
- [x] 185-row Open cycle (seg 32, starts 2023-7-5-0-20-55-731) inspected: it opened to position 807 instead of ~700,
      so it ran longer at the *lowest* mid-travel current in Test (271 mA). Over-travel at normal current is not
      resistance → Normal (p_abnormal = 0.01, RF agrees). Mention in the write-up as a handled edge case.
- [x] `predictions/door_predictions.csv`: 38 rows via CLI; the app's `process()` returns the identical frame
      (verified programmatically). Still regenerate it through the UI during the demo recording.
- [x] App: `streamlit run app/app.py` starts clean; Door tab = upload → metrics → current trace with cycles shaded by label → table → download
- [x] Independent review (separate agent, adversarial brief): SOUND WITH CAVEATS — its own scorer implementation
      matched ours on 12 edge cases; no leakage; format compliant; agreed with both judgment calls. Its three
      hardening findings (fallback used command flips, train.py lacked a row-count assert, ugly upload errors) are
      fixed; model and Test predictions byte-identical after the fixes. One residual caveat for the write-up: the
      two lowest-current Abnormal Train cycles (Close 309 mA, Open 386 mA) are missed under leave-one-out, so a
      *mild* resistance case near the class boundary could be missed — no Test cycle sits in that zone.
- [x] **Official held-out score: 1.000** (judge leaderboard) — every cycle correctly bounded and labelled
- [ ] Door tab demoed end-to-end in the browser for the video
- [ ] Write-up paragraph drafted (all the numbers needed are in this checklist)
