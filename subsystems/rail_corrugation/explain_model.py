"""Which features actually drive the model's decisions?

Permutation importance: shuffle one feature's values and measure how much macro F1 drops.
A feature that matters a lot will wreck the score when scrambled; an ignored one won't.

Computed out-of-fold (fit on the training fold, permuted on the validation fold) so the
importances reflect generalisation rather than memorised training structure.

Run:  python -m subsystems.rail_corrugation.explain_model
"""
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import f1_score, make_scorer

from . import config
from .model import build_model
from .split import feature_columns, load_training_frame, make_folds

N_REPEATS = 10
TOP_N = 15

macro_f1 = make_scorer(
    f1_score, labels=list(config.CLASSES), average="macro", zero_division=0
)


def feature_family(name):
    """Group the 239 features into human-readable families for the presentation."""
    if name == "speed_mps":
        return "train speed"
    side = "asymmetry (Side I vs II)" if name.startswith("asym_") else "single-side"
    if "band" in name or "wavelength" in name or "dominant" in name or "centroid" in name:
        domain = "frequency-domain"
    else:
        domain = "time-domain"
    signal = "shock" if "_shock_" in name else "vibration"
    return f"{side}, {domain}, {signal}"


if __name__ == "__main__":
    df = load_training_frame()
    cols = feature_columns(df)
    X = df[cols].to_numpy(dtype=np.float64)
    y = df["label"].to_numpy()

    importances = np.zeros(len(cols))
    for train_idx, val_idx in make_folds(df):
        model = build_model("balanced").fit(X[train_idx], y[train_idx])
        result = permutation_importance(
            model, X[val_idx], y[val_idx],
            scoring=macro_f1, n_repeats=N_REPEATS, random_state=42,
        )
        importances += result.importances_mean
    importances /= 5

    table = (pd.DataFrame({"feature": cols, "importance": importances})
             .sort_values("importance", ascending=False))

    print(f"Top {TOP_N} features by permutation importance "
          f"(drop in macro F1 when the feature is scrambled):\n")
    for _, row in table.head(TOP_N).iterrows():
        print(f"  {row['importance']:+.4f}  {row['feature']}")

    print("\nAggregated by feature family:")
    table["family"] = table["feature"].map(feature_family)
    by_family = (table.groupby("family")["importance"]
                 .agg(total="sum", n="size", best="max")
                 .sort_values("total", ascending=False))
    print(by_family.to_string(float_format=lambda v: f"{v:.4f}"))

    is_asym = table["feature"].str.startswith("asym_")
    share_of_importance = 100 * table[is_asym]["importance"].sum() / table["importance"].sum()
    share_of_count = 100 * is_asym.sum() / len(cols)
    print(f"\nAsymmetry (Side I vs Side II) features carry "
          f"{share_of_importance:.0f}% of total importance "
          f"while making up {share_of_count:.0f}% of the feature count.")
