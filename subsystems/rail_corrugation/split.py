"""Phase 3: the modelling frame + leakage-safe stratified CV folds.

Single source of truth for "which rows do we train on" -- Phase 4/5 import from here
rather than re-filtering, so the exclusions can't silently diverge between scripts.

Run:  python -m subsystems.rail_corrugation.split
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from . import config

N_SPLITS = 5
RANDOM_STATE = 42

# Byte-identical duplicate of Train107.csv (verified by MD5 over the raw files). A literal
# duplicate carries no extra information, would double-weight that sample in training, and
# would leak across folds if the two members landed on opposite sides of a split -- so one
# member is dropped rather than group-constrained. The other duplicate pair found
# (Train165/Train187) is stationary and already excluded by the filter below.
DROPPED_DUPLICATES = ("Train115.csv",)

# Degenerate by construction, not by chance. `dominant_wavelength_m = speed / dominant_freq`,
# so the *max* wavelength over a side's channels is set by the *lowest* dominant frequency --
# which saturates at the first FFT bin (1 Hz, since the window is exactly 1s). Both sides hit
# that floor on every file, so max-wavelength collapses to `speed` on both sides: their
# difference is exactly 0 and their ratio exactly 1. Confirmed empirically:
# Side_{I,II}_shock_dominant_wavelength_m_max correlate +1.000 with speed_mps.
DEGENERATE_FEATURES = (
    "asym_diff_shock_dominant_wavelength_m_max",
    "asym_ratio_shock_dominant_wavelength_m_max",
)

NEAR_CONSTANT_STD = 1e-6

STATIONARY_SPEED_EPS = 1e-9


def is_stationary(speed_mps):
    """A stationary train cannot produce a corrugation signature -- see PLAN.md Phase 2."""
    return speed_mps <= STATIONARY_SPEED_EPS


def feature_columns(df):
    return [
        c for c in df.columns
        if c not in ("file_id", "label") and c not in DEGENERATE_FEATURES
    ]


def load_training_frame(verbose=False):
    """Load the cached train features, then drop the rows we've decided not to model on:
    stationary files (handled by an explicit rule at inference) and duplicate files."""
    df = pd.read_csv(config.ARTIFACTS_DIR / "train_features.csv")
    n_all = len(df)

    stationary_mask = is_stationary(df["speed_mps"])
    df = df[~stationary_mask]
    n_after_stationary = len(df)

    df = df[~df["file_id"].isin(DROPPED_DUPLICATES)]
    df = df.reset_index(drop=True)

    if verbose:
        print(f"All train rows:            {n_all}")
        print(f"  - stationary excluded:   {n_all - n_after_stationary}")
        print(f"  - duplicates dropped:    {n_after_stationary - len(df)} "
              f"{list(DROPPED_DUPLICATES)}")
        print(f"Modelling frame:           {len(df)} rows, "
              f"{len(feature_columns(df))} features")
    return df


def make_folds(df, n_splits=N_SPLITS, random_state=RANDOM_STATE):
    """Stratified k-fold on the class label. Stratification is by label alone: the
    stationary dimension is constant once stationary rows are excluded."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    return list(skf.split(np.zeros(len(df)), df["label"]))


if __name__ == "__main__":
    df = load_training_frame(verbose=True)
    folds = make_folds(df)

    print(f"\nClass counts in the modelling frame: {df['label'].value_counts().to_dict()}")
    print(f"\n{N_SPLITS}-fold stratified CV -- validation-fold composition:")
    header = f"  {'fold':<6}{'n':<6}" + "".join(f"{c:<10}" for c in config.CLASSES)
    print(header)
    for i, (_, val_idx) in enumerate(folds):
        counts = df.iloc[val_idx]["label"].value_counts()
        row = f"  {i:<6}{len(val_idx):<6}"
        row += "".join(f"{int(counts.get(c, 0)):<10}" for c in config.CLASSES)
        print(row)

    # Assertions -- checked, not just claimed.
    all_val = np.concatenate([val for _, val in folds])
    assert len(all_val) == len(df), "folds do not cover every row exactly once"
    assert len(set(all_val.tolist())) == len(df), "a row appears in more than one fold"

    for i, (_, val_idx) in enumerate(folds):
        counts = df.iloc[val_idx]["label"].value_counts()
        for cls in ("Side I", "Side II"):
            n = int(counts.get(cls, 0))
            assert n >= 2, f"fold {i} has only {n} {cls} example(s) -- F1 would be noise"

    assert not df["file_id"].isin(DROPPED_DUPLICATES).any()
    assert not is_stationary(df["speed_mps"]).any()
    assert df["file_id"].is_unique

    # Catch any *newly* degenerate feature rather than relying on the hardcoded list
    # staying current -- a feature can be non-constant across all 272 rows but constant
    # once stationary files are excluded, which is exactly how the second one was missed.
    stds = df[feature_columns(df)].std()
    leftover = sorted(stds[stds < NEAR_CONSTANT_STD].index)
    assert not leftover, f"near-constant features still in the feature set: {leftover}"

    print("\nAll assertions passed: full coverage, no row in two folds, "
          "every fold has >=2 of each minority class, no stationary/duplicate rows, "
          "no near-constant features.")
