"""Phase 5: model/feature ablations, measured under repeated stratified CV.

Every variant is scored the same way: 5 independent 5-fold CVs (different fold seeds),
pooled macro F1 within each repeat, then mean +/- sd across repeats. Single-seed CV is
too noisy here to select on -- an earlier single-seed result suggested class_weight=None
beat "balanced" by +0.024, which vanished under repeated measurement.

Run:  python -m subsystems.rail_corrugation.ablations
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from . import config
from .model import build_model, cross_validate, pooled_scores
from .split import feature_columns, load_training_frame

N_REPEATS = 5
N_SPLITS = 5

# The noise floor measured in Phase 4 (sd ~0.03 across seeds). Treat any gain smaller
# than this as unproven rather than as an improvement.
NOISE_FLOOR = 0.03


# --- feature subsets (chosen by rule, not by measured importance, so no selection leakage) ---

def all_features(cols):
    return cols


def asymmetry_only(cols):
    return [c for c in cols if c.startswith("asym_") or c == "speed_mps"]


def drop_wavelength(cols):
    return [c for c in cols if "dominant_wavelength" not in c]


def compact(cols):
    """Asymmetry features, minus the wavelength family that is largely a speed proxy."""
    return [c for c in cols
            if (c.startswith("asym_") and "dominant_wavelength" not in c)
            or c == "speed_mps"]


# --- estimators ---

class SpeedResidualizer(BaseEstimator, TransformerMixin):
    """Replace each asymmetry feature with its residual after regressing on speed.

    Within Side I, asymmetry correlates -0.755 with speed (the signature weakens and
    flips sign as speed rises), so the raw feature conflates fault with speed. The
    regression is fit on the training fold only.
    """

    def __init__(self, asym_idx, speed_idx):
        self.asym_idx = asym_idx
        self.speed_idx = speed_idx

    def fit(self, X, y=None):
        speed = X[:, [self.speed_idx]]
        self.models_ = []
        for j in self.asym_idx:
            lr = LinearRegression().fit(speed, X[:, j])
            self.models_.append(lr)
        return self

    def transform(self, X):
        X = X.copy()
        speed = X[:, [self.speed_idx]]
        for lr, j in zip(self.models_, self.asym_idx):
            X[:, j] = X[:, j] - lr.predict(speed)
        return X


class BinaryDecomposition(BaseEstimator):
    """Two independent one-vs-rest detectors (Side I present? Side II present?) combined,
    rather than one 3-way classifier. With 14/24 minority examples, two focused binary
    problems may separate better than a single softmax over three classes."""

    def __init__(self, class_weight="balanced", random_state=42):
        self.class_weight = class_weight
        self.random_state = random_state

    def fit(self, X, y):
        self.clf_i_ = HistGradientBoostingClassifier(
            class_weight=self.class_weight, random_state=self.random_state
        ).fit(X, (y == "Side I").astype(int))
        self.clf_ii_ = HistGradientBoostingClassifier(
            class_weight=self.class_weight, random_state=self.random_state
        ).fit(X, (y == "Side II").astype(int))
        return self

    def predict(self, X):
        p_i = self.clf_i_.predict_proba(X)[:, 1]
        p_ii = self.clf_ii_.predict_proba(X)[:, 1]
        out = np.full(len(X), "Normal", dtype=object)
        # Whichever detector fires strongest wins; Normal if neither is confident.
        fires = (p_i > 0.5) | (p_ii > 0.5)
        out[fires & (p_i >= p_ii)] = "Side I"
        out[fires & (p_ii > p_i)] = "Side II"
        return out


def residualized_pipeline(feature_cols, class_weight="balanced", random_state=42):
    asym_idx = [i for i, c in enumerate(feature_cols) if c.startswith("asym_")]
    speed_idx = feature_cols.index("speed_mps")
    return Pipeline([
        ("resid", SpeedResidualizer(asym_idx, speed_idx)),
        ("clf", HistGradientBoostingClassifier(
            class_weight=class_weight, random_state=random_state)),
    ])


# --- evaluation ---

def evaluate(df, select_features, make_estimator, n_repeats=N_REPEATS):
    """Pooled macro F1 per repeat, each repeat a full 5-fold CV with its own fold seed."""
    cols = select_features(feature_columns(df))
    per_repeat = []
    for repeat in range(n_repeats):
        folds = list(
            StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=repeat)
            .split(np.zeros(len(df)), df["label"])
        )
        results = cross_validate(
            df, folds,
            make_estimator=lambda: make_estimator(cols, repeat),
            feature_cols=cols,
        )
        per_repeat.append(pooled_scores(results["y_true"], results["oof_pred"]))
    out = pd.DataFrame(per_repeat)
    return {"n_features": len(cols), "mean": out.mean(), "sd": out.std()}


VARIANTS = [
    ("A. baseline (all features)", all_features,
     lambda cols, seed: build_model("balanced", seed)),
    ("B. asymmetry only", asymmetry_only,
     lambda cols, seed: build_model("balanced", seed)),
    ("C. drop wavelength family", drop_wavelength,
     lambda cols, seed: build_model("balanced", seed)),
    ("D. compact (asym, no wavelength)", compact,
     lambda cols, seed: build_model("balanced", seed)),
    ("E. no class weighting", all_features,
     lambda cols, seed: build_model(None, seed)),
    ("F. two binary detectors", all_features,
     lambda cols, seed: BinaryDecomposition("balanced", seed)),
    ("G. speed-residualised asymmetry", all_features,
     lambda cols, seed: residualized_pipeline(cols, "balanced", seed)),
    ("H. compact + residualised", compact,
     lambda cols, seed: residualized_pipeline(cols, "balanced", seed)),
]


if __name__ == "__main__":
    df = load_training_frame(verbose=True)
    print(f"\nScoring each variant over {N_REPEATS} repeats x {N_SPLITS}-fold CV "
          f"(pooled macro F1 per repeat, then mean +/- sd)...\n")

    rows = []
    for name, select, make_est in VARIANTS:
        res = evaluate(df, select, make_est)
        rows.append({
            "variant": name,
            "n_feat": res["n_features"],
            "macro_F1": res["mean"]["macro_F1"],
            "sd": res["sd"]["macro_F1"],
            "F1_Normal": res["mean"]["F1_Normal"],
            "F1_Side I": res["mean"]["F1_Side I"],
            "F1_Side II": res["mean"]["F1_Side II"],
        })
        print(f"  done: {name}")

    table = pd.DataFrame(rows).sort_values("macro_F1", ascending=False)
    print("\n" + "=" * 100)
    print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("=" * 100)

    best = table.iloc[0]
    baseline = table[table["variant"].str.startswith("A.")].iloc[0]
    gain = best["macro_F1"] - baseline["macro_F1"]
    print(f"\nBest: {best['variant']} at macro F1 {best['macro_F1']:.3f}")
    print(f"Gain over baseline: {gain:+.3f}  (noise floor ~{NOISE_FLOOR:.2f})")
    if gain < NOISE_FLOOR:
        print("  -> WITHIN NOISE. Not a proven improvement; prefer the simpler variant.")
    else:
        print("  -> exceeds the noise floor; a real improvement.")
