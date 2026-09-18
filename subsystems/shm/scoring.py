"""Official SHM metric: max(0, 1 - MAPE) (SHM_Info_Kit.md, section 4)."""
import numpy as np
import pandas as pd


def mape(true, pred) -> float:
    t = np.asarray(true, float)
    p = np.asarray(pred, float)
    return float(np.mean(np.abs(t - p) / np.abs(t)))


def mape_score(true, pred) -> float:
    return max(0.0, 1.0 - mape(true, pred))


def score_frames(true_df: pd.DataFrame, pred_df: pd.DataFrame) -> float:
    """true_df: filename, damage.  pred_df: file_id, prediction.  Joined on file name."""
    m = true_df.merge(pred_df, left_on="filename", right_on="file_id", how="left")
    if m.prediction.isna().any():
        missing = m.loc[m.prediction.isna(), "filename"].tolist()
        raise ValueError(f"no prediction for: {missing}")
    return mape_score(m.damage, m.prediction)


if __name__ == "__main__":
    true = [0.10, 0.30, 0.50, 0.70, 0.90]
    checks = {
        "info-kit worked example": (mape_score(true, [0.15, 0.28, 0.55, 0.68, 0.85]), 0.850),
        "constant 0.5 guess floors at 0": (mape_score(true, [0.5] * 5), 0.0),
        "perfect": (mape_score(true, true), 1.0),
    }
    for name, (got, want) in checks.items():
        print(("OK  " if abs(got - want) < 1e-3 else "FAIL") + f" {name:32s} got={got:.4f} want={want}")
    assert all(abs(g - w) < 1e-3 for g, w in checks.values())
