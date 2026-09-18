---
name: door-segment-scoring
description: Use when building or evaluating the Door subsystem model (PS3) — segmenting the continuous door motor-current/voltage/back-EMF/position stream into open/close cycles and classifying each as Normal or Abnormal resistance. Covers the exact IoU-weighted F1 scoring formula so local validation matches how the held-out test is graded.
---

# Door: segmentation + IoU-weighted F1 scoring

## Task shape

`Test.csv` is one continuous stream, not pre-cut cycles. The model must (1) find where each
door-open/close cycle starts and ends, then (2) classify that cycle as `Normal` or
`Abnormal resistance`. Output is one row **per predicted segment** (no `file_id`):
`start_time`, `end_time`, `prediction`.

## Segmentation approach

Don't rely on a single fixed-threshold flag column. A cycle boundary is where the signal
*changes regime* (e.g. motor current/back-EMF returning to an idle baseline, or the
open/close/DCSR/DCSL/DLSR/DLSL flags transitioning), not any single column crossing a fixed
value — data distributions differ across doors. Practical approach:
1. Build a rolling-window "activity" signal from current/voltage/back-EMF magnitude and rate
   of change.
2. Detect idle-vs-active regions (activity below a data-derived, not hardcoded, threshold for
   a minimum dwell time = idle/gap).
3. Each active region between two idle gaps is a candidate segment.
4. Classify each candidate segment (e.g. peak current, back-EMF variance, duration, position
   trajectory shape) as Normal vs Abnormal resistance.

Validate by holding out a **contiguous time slice** of `Train.csv` (not a row shuffle — rows
inside a cycle are highly correlated) and comparing against `Train_Segments_Answer.csv`.

## Scoring formula (implement this exactly for local validation)

1. **Matching is same-label only** — a `Normal` prediction can never match an
   `Abnormal resistance` true segment, even with perfect timing overlap.
2. **IoU** of `[start_time, end_time]`:
   ```
   intersection = max(0, min(true_end, pred_end) - max(true_start, pred_start))
   union        = (true_end - true_start) + (pred_end - pred_start) - intersection
   IoU          = intersection / union if union > 0 else 0
   ```
   Only pairs with same label AND IoU > 0 are match candidates.
3. **Greedy one-to-one matching**, highest IoU first; each true/predicted segment used at most
   once.
4. **Credit is the IoU value itself**, not a flat 1 per match:
   ```
   soft_recall    = sum(IoU over matches) / num_true_segments
   soft_precision = sum(IoU over matches) / num_predicted_segments
   score = 2 * soft_recall * soft_precision / (soft_recall + soft_precision)   # 0 if both 0
   ```

Implications to design against: missing a cycle hurts recall; over-segmenting (spurious extra
segments) hurts precision; sloppy boundaries reduce that match's IoU contribution even though it
still counts as a match; wrong label = full miss (scores identically to not predicting that
segment at all, plus a spurious extra one).

Write a small local scorer implementing this exact formula and run it against your own
`Train.csv` holdout before touching `Test.csv` — this is the actual grading function, not an
approximation.
