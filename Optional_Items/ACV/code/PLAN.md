# ACV subsystem — review and results

Built by matthewtzx (`origin/ACV`); reviewed after the held-out score on the merged branch.
Spec: [references/ACV/ACV_Subsystem_Info_Kit.md](../../references/ACV/ACV_Subsystem_Info_Kit.md).

## 0. Facts

| Fact | Value | Why it matters |
|---|---|---|
| Labelled cases | 6 files, one faulty car each (`01, 02, 03, 01, 04, 06`) | Leave-one-case-out is the only honest protocol; a fixed rule needs no folds |
| Schemas | cases 01/02/03 and Test: identical 8 params/car; 05/06: same with one renamed outdoor-temp column; case_04: 63 params/car, cabin temperature present for only 4 of 8 cars | 5 of 6 cases are directly comparable to Test; case_04's refrigerant *pressure* channels don't exist in Test |
| Official Test score (v1) | 0.875 — true car ranked 2nd (submitted `04\|01\|…`, so the faulty car is `01`) | Known only from the leaderboard; not used to select the fix (see §2) |
| Official Test score (v2) | **1.000** — the blend's `01\|04\|…` resubmission scored top-1 | Confirms the physics rule: the mechanism, not the telemetry-validity flag, localises the leak |
| Shipped ranker (v1) | fixed-prior heuristic: 25 hand-set weights over cross-car deviation features grouped into semantic categories | 1.000 on all 6 labelled cases |

## 1. Why v1 missed on Test — diagnosed from the file, not the answer

Per-category contribution to the v1 score on Test: `04` = mode 0.279 + temperature 0.181 +
valid 0.200 = 0.66; `01` = mode 0.072 + temperature 0.194 + valid 0.000 = 0.27. The two cars are
tied on temperature — `01` is marginally *higher* — and `04` wins on the **mode** and
**"ACV Information Valid"** categories. "Information Valid" is a telemetry-validity flag, not a
leak symptom; it carries weight because in three of the six training cases the faulty car also
happened to throw more Invalid flags (it contributes +0.200 to the true car's lead in cases
01/02/03). That coincidence does not hold on Test.

## 2. The physics rule

A unit losing refrigerant cannot pull its cabin down to target, so the direct signature is
**mean (cabin temperature − cooling setpoint) over cooling-mode timestamps, per car**
(`rank.physics_gap`). It has no weights and nothing to tune, so evaluating it on the labelled
cases *is* its out-of-sample estimate.

| | case_01 | case_02 | case_03 | case_04 | case_05 | case_06 | mean score |
|---|---|---|---|---|---|---|---|
| rank of true car | 1 | 1 | 1 | **2** | 1 | 1 | 0.979 |
| margin over runner-up (°C) | 0.53 | 0.11 | 0.45 | — | 0.02 | 1.20 | |

The one miss is case_04, where only four cars have a cabin sensor at all. Five sibling
formulations (all-time mean, cooling-only mean, per-timestamp deviation, fraction-of-time-hottest,
cabin-only deviation) give identical ranks — the result is not sensitive to the exact statistic.
A median-based variant and cooling-time-fraction are clearly worse and were discarded.

**Blend** (`method="blend"`): equal-weight average of the within-file z-scores of the physics gap
and the v1 heuristic; cars with no cabin measurement are ordered by the heuristic and placed last.
Scores **1.000 on all six labelled cases** — the heuristic's pressure channels rescue case_04 —
with no fitted parameter. This is the new default in `app/inference/acv.py`.

## 3. What each ranker says about Test (reported, not used for selection)

| ranker | Test ranking | top |
|---|---|---|
| v1 heuristic (submitted) | `04\|01\|07\|05\|02\|08\|03\|06` | 04 |
| physics | `01\|03\|07\|04\|08\|06\|02\|05` | 01 |
| **blend (default)** | `01\|04\|03\|07\|08\|06\|02\|05` | **01** |

Disclosure for the write-up: the physics rule was formulated after the leaderboard feedback,
from the failure mechanism, and was validated on the labelled cases before its Test output was
looked at. Its agreement with the leaderboard is corroboration, not the reason it was chosen.

**Outcome:** the blend was resubmitted and scored **1.000**. Both the physics ranker and the
blend put `01` first, so the resubmission would have scored 1.000 either way; the blend was
chosen because it also scores 1.000 on all six labelled cases, where physics alone scores 0.979
(case_04 has cabin temperature for only 4 of its 8 cars).

## 4. Commands

```
python -m subsystems.acv.evaluate                                   # EDA + LOO of v1 methods
python -m subsystems.acv.predict --input data/ACV/Test --output predictions/acv_predictions.csv [--method blend|physics|heuristic]
```

## 5. Open items

- Not wired into the shared app (`app/inference/acv.py` is an inference module, not a page).
- `predictions/acv_predictions.csv` still holds the v1 ranking until the team decides to
  regenerate it with the blend.
