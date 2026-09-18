"""What each model actually gets wrong, in plain language, for a non-technical reader.

Every number here is copied from the subsystem's PLAN.md (cited per block) — nothing is
invented for the UI. Severity/urgency thresholds ARE new: there is no organiser-supplied
maintenance standard to calibrate them against, so they are disclosed as a heuristic triage
aid, not a validated output, everywhere they are shown.
"""

# ---- Rail — subsystems/rail_corrugation/PLAN.md:274-291 (out-of-fold confusion matrix) ----
RAIL_RELIABILITY = {
    "Side I": {"recall": 7 / 14, "precision": 7 / 9, "n_true": 14},
    "Side II": {"recall": 20 / 24, "precision": 20 / 23, "n_true": 24},
    "Normal": {"recall": 191 / 195, "precision": 191 / 201, "n_true": 195},
}
RAIL_RELIABILITY_NOTE = (
    "From repeated cross-validation on the 233 labelled training recordings (out-of-fold, "
    "so no file scored itself). The held-out competition score (0.888) came out higher than "
    "this estimate (0.81) — a favourable mix of test files, not a better model; treat the "
    "numbers below as the more durable read of what to expect on a new recording."
)

# ---- Door — subsystems/door/PLAN.md:184-189 (independent review) ----
DOOR_RELIABILITY_NOTE = (
    "On the labelled training cycles, this model caught every cycle with a clearly abnormal "
    "current draw. Two cycles sat right at the boundary between normal and mildly abnormal "
    "resistance (309 mA and 386 mA — both barely above the normal range) and were missed "
    "under cross-validation. A borderline case like that could still slip through."
)

# ---- SHM — subsystems/shm/PLAN.md:16-17,72 (LOO scale-fit and worst-file error) ----
SHM_TYPICAL_MAPE = 0.026   # 1 - 0.9744 analytic LOO
SHM_WORST_MAPE = 0.093     # worst single LOO file (train12)
# Training files ranged roughly -54..-13 (min) and 18..41 (max) across a 15-file sample; this
# is a generous ~3x envelope used only to flag an implausible upload, never to block one.
SHM_PLAUSIBLE_ABS_MAX = 120.0
SHM_RELIABILITY_NOTE = (
    "Checked by leaving each of the 64 training files out in turn and predicting it from the "
    "rest. Typical error was about 3%; the single worst file was off by 9%. The damage number "
    "also assumes a specific fatigue curve (S-N exponent 5) recovered from this dataset, not "
    "supplied by the organisers — a real segment that doesn't follow that curve would be "
    "scored wrong in a way this error range does not capture."
)

# ---- ACV — subsystems/acv/PLAN.md:35,43-46 (leave-one-case-out) ----
ACV_RELIABILITY_NOTE = (
    "Checked against the 6 labelled cases we have an answer for, leaving each one out in "
    "turn: the current method (physics + heuristic blend) named the right car first in all "
    "6. That is a small sample — six cases is not enough to rule out a rare miss — but it is "
    "the complete record, including the one v1 got wrong before this fix."
)


def rail_class_line(cls: str) -> str:
    r = RAIL_RELIABILITY[cls]
    return (f"Historically, when a recording actually was {cls}, this model caught it "
            f"{r['recall']:.0%} of the time (missed the rest); when it does call {cls}, "
            f"it is right {r['precision']:.0%} of the time.")


# ---- Severity/urgency mapping — heuristic triage overlay, not a validated metric ----
# Tiers, worst to best. Colour is set by the caller from theme so it follows light/dark mode.
OK, MONITOR, INSPECT, ACT, UNKNOWN = "ok", "monitor", "inspect", "act", "unknown"
TIER_LABEL = {
    OK: "No action needed", MONITOR: "Monitor", INSPECT: "Inspect soon",
    ACT: "Inspect before next service", UNKNOWN: "Inconclusive",
}


def door_severity(prediction: str, excess_pct: float, confidence: float) -> str:
    """excess_pct: mid-travel current vs the healthy median of the same operation, this file."""
    if prediction == "Normal":
        return OK
    if excess_pct >= 0.6 and confidence >= 0.9:
        return ACT
    if excess_pct >= 0.3 or confidence >= 0.7:
        return INSPECT
    return MONITOR


def rail_severity(prediction: str, confidence: float, stationary: bool) -> str:
    if stationary:
        return UNKNOWN
    if prediction == "Normal":
        return OK
    return ACT if confidence >= 0.75 else INSPECT


def shm_severity(damage: float) -> str:
    # Thresholds are illustrative (0.5 / 0.8 of the 0-1 damage scale), not an organiser-
    # supplied maintenance limit -- see SHM_RELIABILITY_NOTE, always shown alongside.
    if damage >= 0.8:
        return ACT
    if damage >= 0.5:
        return INSPECT
    return OK if damage < 0.3 else MONITOR


def acv_severity(gap_c: float, margin: float) -> str:
    """gap_c: top car's cabin-above-setpoint gap in cooling mode (NaN if unmeasured)."""
    import math
    if gap_c != gap_c:  # NaN
        return MONITOR if margin < 0.3 else INSPECT
    if gap_c >= 1.5:
        return ACT
    if gap_c >= 0.5:
        return INSPECT
    return MONITOR


def confidence_label(p: float) -> str:
    if p >= 0.9:
        return "High"
    if p >= 0.65:
        return "Medium"
    return "Low"
