import numpy as np
import pandas as pd

from .loader import TIME_COL, POSITION_COL, CLOSING_FLAG_COL, OPENING_FLAG_COL

GAP_SECONDS = 0.5
POSITION_JUMP = 100


def _breaks_by_gap(df: pd.DataFrame) -> pd.Series:
    return df["ts"].diff().dt.total_seconds() > GAP_SECONDS


def _breaks_by_signal(df: pd.DataFrame) -> pd.Series:
    # Position resets between cycles (e.g. 701 -> 0), and the opening/closing flag switches at an
    # Open<->Close boundary. The command columns are NOT used: 'Open command' can flip mid-cycle.
    pos_jump = df[POSITION_COL].diff().abs() > POSITION_JUMP
    op_change = (df[OPENING_FLAG_COL].diff().fillna(0) != 0) | (df[CLOSING_FLAG_COL].diff().fillna(0) != 0)
    return pos_jump | op_change


def segment(df: pd.DataFrame) -> pd.DataFrame:
    """Split a continuous stream into door cycles. One row per cycle."""
    breaks = _breaks_by_gap(df)
    if breaks.sum() == 0:
        breaks = _breaks_by_signal(df)
    seg_id = breaks.fillna(False).astype(int).cumsum()

    rows = []
    for sid, idx in df.groupby(seg_id).indices.items():
        i0, i1 = int(idx[0]), int(idx[-1])
        closing = df[CLOSING_FLAG_COL].iloc[i0:i1 + 1].mean()
        rows.append({
            "seg_id": int(sid),
            "i0": i0,
            "i1": i1,
            "start_str": df[TIME_COL].iloc[i0],
            "end_str": df[TIME_COL].iloc[i1],
            "op": "Close" if closing > 0.5 else "Open",
        })
    return pd.DataFrame(rows)
