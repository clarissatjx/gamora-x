import numpy as np
import pandas as pd

EXPECTED_SAMPLES = 581_120


def load_series(path) -> np.ndarray:
    """One headerless column of dynamic stress values."""
    try:
        df = pd.read_csv(path, header=None)
    except pd.errors.EmptyDataError:
        raise ValueError("The file is empty.")
    except UnicodeDecodeError:
        raise ValueError("The file is not a plain-text CSV (is it an Excel file? Export it as .csv first).")
    if df.shape[1] != 1:
        raise ValueError(
            f"Expected a single column of stress values, found {df.shape[1]} columns. "
            "SHM files are one headerless column."
        )
    x = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy(dtype=float)
    if np.isnan(x).all():
        raise ValueError("The column contains no numeric values.")
    if np.isnan(x[0]) and not np.isnan(x[1:]).any():
        raise ValueError(
            f"The first line ({df.iloc[0, 0]!r}) looks like a header. SHM files are headerless — "
            "remove it and try again."
        )
    if np.isnan(x).any():
        raise ValueError(f"The file has {int(np.isnan(x).sum())} non-numeric or missing values.")
    if len(x) < 1000:
        raise ValueError(f"Only {len(x)} samples — an SHM segment has about {EXPECTED_SAMPLES:,}.")
    return x
