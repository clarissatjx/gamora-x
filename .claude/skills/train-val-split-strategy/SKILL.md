---
name: train-val-split-strategy
description: Use before training any PS3 subsystem model — enforces a leakage-safe, subsystem-appropriate train/validation split. The PS3 rubric explicitly grades split soundness alongside the headline metric, so a naive random row-shuffle split is a scoring risk, not just a modeling one.
---

# Leakage-safe train/val splits per PS3 subsystem

PS3's grading rubric states methodologically sound work — valid splits, no leakage — is judged
**alongside** the headline metric, not as an afterthought. A high local score from a leaky split
will not score well. Use these subsystem-specific defaults, and state whichever one you use (and
why) in the write-up.

| Subsystem | Wrong split | Correct default | Why |
|---|---|---|---|
| Door | Random row shuffle of `Train.csv` | Hold out a **contiguous time range** (a set of whole cycles), validate against the matching slice of `Train_Segments_Answer.csv` | Rows inside one cycle are highly autocorrelated; a row-shuffle split leaks a cycle's own future/past into training |
| ACV | A single fixed train/test split of the 6 cases | **Leave-one-case-out** cross-validation across the 6 labelled cases | n=6 is too small for a stable fixed split; LOO uses every case for validation once |
| Rail Corrugation | Unstratified random split | **Stratified** split by class label (Normal/Side I/Side II) | ~86/5/9% imbalance means an unstratified split can easily zero out a minority class in validation |
| SHM | Random split ignoring line/load condition | Split by file; **stratify by line/load-condition (AW0/AW4) if inferable** | Dataset spans two lines and two load conditions per the Info Kit — validation should cover both, not just whichever the random split happens to include |

## General leakage checks (apply to all four)
- Any per-feature normalization statistic (mean/std, min/max, scaler fit) must be computed on
  the **training portion only**, then applied unchanged to validation/held-out data.
- If a subsystem's files come from a shared source (e.g. same measurement point, same train) and
  that grouping is knowable, split **by group**, not by row/file naively, so no group straddles
  both train and validation.
- Document the split logic in code (not just informally) so it's reproducible and inspectable —
  the write-up should be able to point at the actual split code, not just describe it in prose.
