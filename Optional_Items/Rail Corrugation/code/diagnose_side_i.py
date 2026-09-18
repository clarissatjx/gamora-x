"""Why does the baseline miss half the Side I faults?

Side I recall is the macro-F1 bottleneck (7/14 at baseline). This characterises the
missed files so Phase 5 targets the actual failure mode rather than guessing.
"""
import pandas as pd

from .model import cross_validate
from .split import load_training_frame, make_folds

FEATURE = "asym_diff_vib_rms_mean"

if __name__ == "__main__":
    df = load_training_frame()
    results = cross_validate(df, make_folds(df))
    df = df.assign(pred=results["oof_pred"])
    df["correct"] = df["pred"] == df["label"]

    side_i = df[df["label"] == "Side I"][
        ["file_id", "speed_mps", FEATURE, "pred", "correct"]
    ].sort_values("speed_mps")

    print("All 14 Side I files, sorted by speed:")
    print(side_i.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    print(f"\ncorr(speed_mps, {FEATURE}) within each class:")
    for cls in ("Normal", "Side I", "Side II"):
        grp = df[df["label"] == cls]
        r = grp["speed_mps"].corr(grp[FEATURE])
        print(f"  {cls:8s} n={len(grp):3d}  r={r:+.3f}")

    caught = side_i[side_i["correct"]]
    missed = side_i[~side_i["correct"]]
    print("\nSpeed and asymmetry, caught vs missed Side I:")
    for name, grp in (("caught", caught), ("missed", missed)):
        print(f"  {name:7s} n={len(grp):2d}  mean speed={grp['speed_mps'].mean():6.2f}  "
              f"mean {FEATURE}={grp[FEATURE].mean():+.4f}")
    print(f"  {'all moving':7s} n={len(df):3d}  mean speed={df['speed_mps'].mean():6.2f}")

    print("\nHow many missed Side I files have a NEGATIVE asymmetry "
          "(i.e. look like Side II / Normal on the headline feature)?")
    print(f"  caught: {(caught[FEATURE] <= 0).sum()}/{len(caught)}   "
          f"missed: {(missed[FEATURE] <= 0).sum()}/{len(missed)}")
