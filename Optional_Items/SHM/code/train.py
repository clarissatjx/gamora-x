import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .loader import load_series
from .model import FEATURES, M, cycle_features
from .rainflow import cycles
from .scoring import mape_score

ROOT = Path(__file__).resolve().parents[2]
TRAIN_DIR = ROOT / "data/SHM/Train"
LABELS_CSV = ROOT / "data/SHM/Train_Labels.csv"
HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "model.joblib"
FEATURES_CSV = HERE / "artifacts" / "train_features.csv"

RIDGE_ALPHA = 1.0
CORRECTION_CLIP = 0.2   # cap on |log correction|, ~ +-22%
GATE_ANALYTIC = 0.96


def make_ridge():
    return make_pipeline(StandardScaler(), Ridge(alpha=RIDGE_ALPHA))


def build_training_table() -> pd.DataFrame:
    labels = pd.read_csv(LABELS_CSV)
    rows = []
    for fn in labels.filename:
        x = load_series(TRAIN_DIR / fn)
        f = cycle_features(*cycles(x))
        f["filename"] = fn
        rows.append(f)
    return pd.DataFrame(rows).merge(labels, on="filename")


def fit_scale(log_s5: np.ndarray, damage: np.ndarray) -> float:
    """C in D = S5 / C, by the median ratio (robust to the few noisiest files)."""
    return float(np.median(np.exp(log_s5) / damage))


def loo(table: pd.DataFrame):
    """Leave-one-out predictions for the analytic model and the corrected model."""
    y = table.damage.to_numpy()
    X = table[FEATURES].to_numpy()
    ls5 = table.log_S5.to_numpy()
    analytic = np.empty_like(y)
    corrected = np.empty_like(y)
    for i in range(len(y)):
        m = np.arange(len(y)) != i
        c = fit_scale(ls5[m], y[m])
        base_m = ls5[m] - np.log(c)
        ridge = make_ridge().fit(X[m], np.log(y[m]) - base_m)
        base_i = ls5[i] - np.log(c)
        analytic[i] = np.exp(base_i)
        corrected[i] = np.exp(base_i + np.clip(ridge.predict(X[i:i + 1])[0], -CORRECTION_CLIP, CORRECTION_CLIP))
    return analytic, corrected


def main():
    t0 = time.time()
    table = build_training_table()
    FEATURES_CSV.parent.mkdir(exist_ok=True)
    table.to_csv(FEATURES_CSV, index=False)
    print(f"training table: {table.shape} in {time.time() - t0:.0f}s -> {FEATURES_CSV.relative_to(ROOT)}")

    y = table.damage.to_numpy()
    analytic, corrected = loo(table)
    s_an, s_co = mape_score(y, analytic), mape_score(y, corrected)
    print(f"  LOO  analytic  D = S{M:g}/C            : {s_an:.4f}")
    print(f"  LOO  analytic + ridge correction  : {s_co:.4f}")
    print(f"  constant-guess (median) baseline  : {mape_score(y, np.full_like(y, np.median(y))):.4f}")
    assert s_an >= GATE_ANALYTIC, f"gate: analytic LOO >= {GATE_ANALYTIC}"

    use_correction = s_co > s_an
    print(f"  correction {'ENABLED' if use_correction else 'DISABLED'} (must beat analytic on LOO)")

    C = fit_scale(table.log_S5.to_numpy(), y)
    base = table.log_S5.to_numpy() - np.log(C)
    ridge = make_ridge().fit(table[FEATURES].to_numpy(), np.log(y) - base)
    coef = pd.Series(ridge[-1].coef_, index=FEATURES).round(4)
    print(f"\n  C = {C:.6e}   (D = S5 / C)")
    print("  ridge coefficients (standardised features):\n" + coef.to_string())

    joblib.dump({
        "m": M, "C": C, "ridge": ridge, "features": FEATURES,
        "use_correction": use_correction, "clip": CORRECTION_CLIP,
        "loo_analytic": s_an, "loo_corrected": s_co,
        "train_damage": y, "train_log_s5": table.log_S5.to_numpy(),
    }, MODEL_PATH)
    print(f"\nsaved {MODEL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
