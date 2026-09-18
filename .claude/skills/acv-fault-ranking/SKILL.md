---
name: acv-fault-ranking
description: Use when building or evaluating the ACV subsystem model (PS3) — localising which car (of 8) has a refrigerant leak from per-car cabin/ambient temperature and control-mode telemetry, and producing a ranked_cars ordering. Covers the tiny-sample-size modeling problem and the exact linear rank-decay scoring formula.
---

# ACV: fault localisation + rank-decay scoring

## Task shape

Each file = one train, ~30s-sampled telemetry for all 8 cars, exactly one car faulty. Output is
one row per file: `file_id`, `ranked_cars` (most- to least-likely faulty, `|`-separated, using
the car ID **exactly as it appears in that file's own column headers**, e.g. `03` not `Car 3`).
No `prediction` column — this is a ranking task, not classification.

**Column schema is not fixed** — some files have ~8 params/car, one file has 60+. Always read
that file's own headers; never assume a fixed column count or order.

## The core modeling problem: only 6 labelled cases

With only 6 training cases (one faulty car each), a supervised classifier trained end-to-end
will overfit badly. Prefer:
- **Per-car anomaly scoring relative to its own train's other 7 cars in the same file**, rather
  than a global classifier across files — e.g. z-score each car's temperature/control-mode
  features against the other cars in that same file/timestamp, since normal cyclic variation is
  shared across the train but a leak is car-specific.
- Feature ideas: deviation of a car's indoor/outdoor temp from the cross-car median at each
  timestamp, control-mode disagreement (e.g. running longer/harder than peers to hit the same
  setpoint), frequency of mode switching, and (where present) any self-check/fault-flag fields.
- **Leave-one-case-out cross-validation** across the 6 training cases (train ranking logic on 5
  cases, validate rank of the true faulty car on the held-out 6th) — a fixed train/val split
  isn't meaningful at n=6.

## Scoring formula (implement this exactly for local validation)

For a file with `n` cars, if the true faulty car is ranked `r` (1 = top pick):

```
score = (n - (r - 1)) / n
```

Worked (n=8): rank 1 → 1.000, rank 2 → 0.875, rank 3 → 0.750, ... rank 8 → 0.125.
Missing the car from `ranked_cars` entirely (or a missing row) → **0**.

Final ACV score = average of this per-file score across all held-out files. Since it's a smooth
partial-credit metric, optimise for the true car being *near the top*, not just for a binary
top-1 hit — a model that reliably ranks the true car in the top 2-3 is worth much more than one
that nails top-1 half the time and ranks last the other half.
