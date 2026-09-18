import numpy as np
import pandas as pd

from .loader import CURRENT_COL, VOLTAGE_COL, EMF_COL, POSITION_COL

FEATURE_COLUMNS = [
    "op", "n_rows",
    "cur_mid", "cur_mean", "cur_med", "cur_p25", "cur_p75", "cur_first_half", "cur_sum",
    "volt_mean", "volt_max",
    "emf_mid", "emf_std",
    "t_half",
]

MID_LO, MID_HI = 100, 600
HALF_TRAVEL = 350


def _segment_features(c, v, e, p, op: str) -> dict:
    n = len(c)
    mid = (p > MID_LO) & (p < MID_HI)
    if not mid.any():
        mid = np.ones(n, dtype=bool)
    travel = np.abs(p - p[0])
    t_half = int(np.argmax(travel >= HALF_TRAVEL)) if travel.max() >= HALF_TRAVEL else n
    return {
        "op": 1 if op == "Close" else 0,
        "n_rows": n,
        "cur_mid": float(c[mid].mean()),
        "cur_mean": float(c.mean()),
        "cur_med": float(np.median(c)),
        "cur_p25": float(np.percentile(c, 25)),
        "cur_p75": float(np.percentile(c, 75)),
        "cur_first_half": float(c[: n // 2].mean()) if n >= 2 else float(c.mean()),
        "cur_sum": float(c.sum()),
        "volt_mean": float(v.mean()),
        "volt_max": float(v.max()),
        "emf_mid": float(e[mid].mean()),
        "emf_std": float(e.std()),
        "t_half": t_half,
    }


def featurize(df: pd.DataFrame, segs: pd.DataFrame) -> pd.DataFrame:
    """One feature row per segment, using only that segment's own rows."""
    c_all = df[CURRENT_COL].to_numpy(dtype=float)
    v_all = df[VOLTAGE_COL].to_numpy(dtype=float)
    e_all = df[EMF_COL].to_numpy(dtype=float)
    p_all = df[POSITION_COL].to_numpy(dtype=float)
    rows = []
    for s in segs.itertuples(index=False):
        sl = slice(s.i0, s.i1 + 1)
        rows.append(_segment_features(c_all[sl], v_all[sl], e_all[sl], p_all[sl], s.op))
    return pd.DataFrame(rows, index=segs.seg_id.values)[FEATURE_COLUMNS]
