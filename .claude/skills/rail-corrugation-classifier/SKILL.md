---
name: rail-corrugation-classifier
description: Use when building or evaluating the Rail Corrugation subsystem model (PS3) — classifying 1s, 10kHz, 64-axle-box vibration/shock recordings as Normal / Side I / Side II corrugation. Covers the severe class imbalance and the exact macro-F1 scoring formula.
---

# Rail Corrugation: 3-class classification + macro-F1 scoring

## Task shape

Each file: column 1 = rotational speed (toothed-wheel pulse, 90 teeth, 0.85m wheel diameter),
columns 2-129 = vibration + shock for 64 axle-box positions (Car 1..8 × Position 1..8), 10kHz,
1 second. Positions 1/3/5/7 = Side I, positions 2/4/6/8 = Side II — both sides must be judged
from the *same* file, independently, then combined into one 3-class label. Output: one row per
file, `file_id`, `prediction` ∈ {`Normal`, `Side I`, `Side II`}.

## Class imbalance is the central risk

Train split: 234 Normal / 14 Side I / 24 Side II (~86% / 5% / 9%). A model that always predicts
`Normal` looks great on accuracy (~86%) but scores **macro F1 ≈ 0.33** (0 F1 on both fault
classes) — this is exactly what the metric is designed to punish. Concretely:
- Use **stratified** train/val splits to keep Side I/II represented in validation.
- Consider class weighting, oversampling the minority classes, or per-side binary
  detectors (Side I present? Side II present?) combined into the final label, rather than a
  single naive multiclass classifier trained on raw class frequencies.
- Convert rotational speed into an actual train speed (via the pulse count / 90 teeth / wheel
  circumference) and use it as a feature/normalisation factor — corrugation's vibration
  signature is speed-dependent, so raw amplitude alone conflates speed and fault.
- Extract per-position spectral features (dominant wavelength/frequency via FFT, tied to speed)
  since corrugation is fundamentally a periodic-wavelength phenomenon, not just raw amplitude —
  see `ts-signal-feature-engineering` for shared spectral feature helpers.
- Aggregate Side I's 4 positions (and Side II's 4) per car, and across cars, rather than treating
  all 64 columns as independent features with no structure.

## Scoring formula (implement this exactly for local validation)

Macro F1 = unweighted mean of each class's own F1 (precision/recall computed per-class,
one-vs-rest), then averaged across the 3 classes equally regardless of class frequency:

```
macro_f1 = (F1_Normal + F1_SideI + F1_SideII) / 3
```

Worked example from the Info Kit: F1 = 0.97 (Normal), 0.40 (Side I), 0.60 (Side II) →
macro F1 = 0.657. An always-Normal model: F1 = 1.0, 0, 0 → macro F1 ≈ 0.33 despite ~85-90%
plain accuracy.

**During development, track macro F1 (or per-class F1) directly — not accuracy** — accuracy will
mislead you into thinking a broken fault detector is a good model.
