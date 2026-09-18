"""Phase 5 follow-up: trade Normal precision for fault recall via a decision-rule boost.

Side I recall is the macro-F1 bottleneck. The default argmax rule requires a Side I file to
beat Normal outright, which is hard when Normal holds 84% of the prior. Since macro F1
weights all three classes equally and Normal F1 sits at ~0.97 with plenty of headroom,
biasing the decision toward the fault classes should be a favourable trade.

This sweeps a single multiplier applied to both fault-class probabilities before argmax.

Run:  python -m subsystems.rail_corrugation.threshold_tuning
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from . import config
from .model import build_model, pooled_scores
from .split import feature_columns, load_training_frame

N_REPEATS = 5
N_SPLITS = 5
BOOSTS = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]


def oof_probabilities(df, cols, seed):
    """Out-of-fold predicted probabilities, so boosts can be swept without refitting."""
    X = df[cols].to_numpy(dtype=np.float64)
    y = df["label"].to_numpy()
    folds = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=seed).split(
        np.zeros(len(df)), y
    )
    proba = np.zeros((len(df), len(config.CLASSES)))
    for train_idx, val_idx in folds:
        model = build_model("balanced", seed).fit(X[train_idx], y[train_idx])
        # Align columns to config.CLASSES order regardless of the model's internal order.
        p = model.predict_proba(X[val_idx])
        for j, cls in enumerate(config.CLASSES):
            proba[val_idx, j] = p[:, list(model.classes_).index(cls)]
    return proba, y


def apply_boost(proba, boost):
    scaled = proba.copy()
    for j, cls in enumerate(config.CLASSES):
        if cls != "Normal":
            scaled[:, j] *= boost
    return np.array(config.CLASSES, dtype=object)[scaled.argmax(axis=1)]


if __name__ == "__main__":
    df = load_training_frame(verbose=True)
    cols = feature_columns(df)

    cached = [oof_probabilities(df, cols, seed) for seed in range(N_REPEATS)]

    rows = []
    for boost in BOOSTS:
        per_repeat = [pooled_scores(y, apply_boost(proba, boost)) for proba, y in cached]
        mean = pd.DataFrame(per_repeat).mean()
        sd = pd.DataFrame(per_repeat).std()
        rows.append({
            "boost": boost,
            "macro_F1": mean["macro_F1"],
            "sd": sd["macro_F1"],
            "F1_Normal": mean["F1_Normal"],
            "F1_Side I": mean["F1_Side I"],
            "F1_Side II": mean["F1_Side II"],
        })

    table = pd.DataFrame(rows)
    print(f"\nFault-probability boost sweep ({N_REPEATS} repeats x {N_SPLITS}-fold CV):\n")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    best = table.loc[table["macro_F1"].idxmax()]
    base = table[table["boost"] == 1.0].iloc[0]
    print(f"\nBest boost {best['boost']:.1f}: macro F1 {best['macro_F1']:.3f} "
          f"(vs {base['macro_F1']:.3f} at boost 1.0, gain {best['macro_F1'] - base['macro_F1']:+.3f})")
    print("\nCaveat: the boost is chosen from this same curve, so the peak is mildly")
    print("optimistic. A broad, flat peak is more trustworthy than a sharp spike.")
