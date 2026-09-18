"""Leave-one-out score on Train, then a distribution-shift check on Test."""
from pathlib import Path

import numpy as np
import pandas as pd

from .loader import load_series
from .model import cycle_features
from .predict import load_model, predict_many
from .rainflow import cycles
from .scoring import mape_score
from .train import FEATURES_CSV, ROOT, loo

TEST_DIR = ROOT / "data/SHM/Test"


def holdout():
    table = pd.read_csv(FEATURES_CSV)
    y = table.damage.to_numpy()
    analytic, corrected = loo(table)
    print(f"LOO analytic : {mape_score(y, analytic):.4f}")
    print(f"LOO corrected: {mape_score(y, corrected):.4f}")
    rel = np.abs(corrected - y) / y
    worst = table.assign(pred=corrected, rel_err=rel).sort_values("rel_err", ascending=False).head(5)
    print("worst files (corrected):")
    print(worst[["filename", "damage", "pred", "rel_err"]].round(4).to_string(index=False))
    return table


def drift_check(table: pd.DataFrame):
    bundle = load_model()
    paths = sorted(TEST_DIR.glob("*.csv"))
    feats = []
    for p in paths:
        rng, mean, cnt = cycles(load_series(p))
        f = cycle_features(rng, mean, cnt)
        f["file_id"] = p.name
        feats.append(f)
    te = pd.DataFrame(feats)
    preds = predict_many(paths, bundle)

    lo, hi = table.log_S5.min(), table.log_S5.max()
    outside = int(((te.log_S5 < lo) | (te.log_S5 > hi)).sum())
    plo, phi = table.damage.min(), table.damage.max()
    pred_out = int(((preds.prediction < plo * 0.8) | (preds.prediction > phi * 1.2)).sum())
    print(f"\nTEST: {len(preds)} files | predicted damage {preds.prediction.min():.4f}-{preds.prediction.max():.4f} "
          f"(train labels {plo:.4f}-{phi:.4f})")
    print(f"  log_S5 outside train range : {outside}")
    print(f"  predictions >20% outside train label range : {pred_out}")
    verdict = "SHIP" if outside == pred_out == 0 else "INSPECT flagged files before shipping"
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    drift_check(holdout())
