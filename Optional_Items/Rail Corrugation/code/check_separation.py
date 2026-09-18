"""Quantify how separable each class actually is from the asymmetry feature alone.

Means alone can hide heavy overlap -- this checks one-vs-rest AUC per class, which is
what actually matters for macro F1.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from . import config

FEATURE = "asym_diff_vib_rms_mean"

if __name__ == "__main__":
    train = pd.read_csv(config.ARTIFACTS_DIR / "train_features.csv")
    moving = train[train["speed_mps"] > 1e-9]

    for name, df in (("ALL FILES", train), ("MOVING ONLY", moving)):
        print(f"\n=== {name} (n={len(df)}) ===")
        x = df[FEATURE].to_numpy()
        for cls in config.CLASSES:
            y = (df["label"] == cls).astype(int).to_numpy()
            if y.sum() == 0:
                continue
            # Side I is expected positive, Side II negative -> score each direction.
            auc = roc_auc_score(y, x)
            auc = max(auc, 1 - auc)  # direction-agnostic separability
            grp = x[y == 1]
            print(f"  {cls:8s} n={y.sum():3d}  one-vs-rest AUC={auc:.3f}  "
                  f"median={np.median(grp):+.4f}  IQR=[{np.percentile(grp, 25):+.4f}, "
                  f"{np.percentile(grp, 75):+.4f}]")

    # How much do Normal files intrude into each fault class's own IQR?
    print("\nOverlap: % of Normal files falling inside each fault class's IQR")
    x_all = train[FEATURE].to_numpy()
    normal_vals = x_all[(train["label"] == "Normal").to_numpy()]
    for cls in ("Side I", "Side II"):
        grp = x_all[(train["label"] == cls).to_numpy()]
        lo, hi = np.percentile(grp, 25), np.percentile(grp, 75)
        pct = 100 * np.mean((normal_vals >= lo) & (normal_vals <= hi))
        print(f"  {cls:8s} IQR=[{lo:+.4f}, {hi:+.4f}] -> {pct:.1f}% of Normal files inside")
