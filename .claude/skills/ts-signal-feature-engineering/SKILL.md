---
name: ts-signal-feature-engineering
description: Shared feature-extraction toolkit for PS3's signal-heavy subsystems (Door motor current/voltage/back-EMF, Rail axle-box vibration/shock, SHM dynamic stress). Use when turning a raw sensor time series into model-ready features for any of these three subsystems.
---

# Shared time-series/signal feature engineering (Door, Rail Corrugation, SHM)

Three of the four PS3 subsystems (Door, Rail Corrugation, SHM) are fundamentally
"characterise a raw sensor time series" problems before any classifier/regressor sees the data.
Reuse the same feature toolkit across them rather than reinventing it per subsystem.

## Time-domain features (cheap, always compute first)
- mean, std, RMS, min, max, peak-to-peak, skewness, kurtosis
- zero-crossing rate, rate-of-change stats (first difference mean/std)
- rolling-window versions of the above (window sized to the subsystem's sampling rate and
  expected event duration) — useful both as segmentation signals (Door) and as per-file
  aggregate features (Rail, SHM)

## Frequency-domain features (needed wherever periodicity is diagnostic)
- FFT / power spectral density; dominant frequency and its magnitude
- Rail corrugation is *defined* by a characteristic wavelength/frequency tied to train speed —
  don't skip spectral features here, raw time-domain amplitude alone conflates speed and fault
- Band-power ratios (energy in expected fault-frequency bands vs. total energy) generalise
  better across different operating speeds/conditions than raw peak amplitude

## Event/cycle-oriented features (Door segmentation, SHM rainflow)
- Idle-vs-active regime detection via a data-derived (not hardcoded) activity threshold with a
  minimum dwell time, for segmenting continuous streams (Door)
- Rainflow cycle counting → cycle amplitude/mean/count distributions, for fatigue-relevant
  summary stats (SHM) — see `shm-fatigue-regression` for how these feed the regression target

## Practical notes
- **Fit any normalization/scaling stats (mean/std, min/max) on the training split only**, then
  apply to validation/test — computing them on the full dataset before splitting is a leakage
  bug the grading rubric explicitly penalises (see `train-val-split-strategy`).
- Compute features per logical unit (per file for Rail/SHM/ACV, per detected segment for Door),
  not per raw row — a raw row is rarely the right unit of prediction here.
- Sanity-check every new feature by plotting it against the known labels on a few
  training files before wiring it into a full pipeline — catches sign errors, unit mismatches,
  and off-by-one window issues cheaply.
