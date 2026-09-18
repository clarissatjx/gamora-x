"""
ACV subsystem: data loading + feature engineering.

Each raw file (``data/ACV/Train/acv_case_XX.xlsx`` or
``data/ACV/Test/acv_test_case.xlsx``) is one train's continuous, ~30s-sampled
telemetry for all 8 cars. Column headers look like ``Car 03 - ACV Running
Mode``; the car ID (``03``) and parameter name (``ACV Running Mode``) are
parsed directly from each file's own headers, never assumed fixed, because
schema varies a lot across files:

- Most files: ~8 params/car (temperature + control-mode + a couple of flags).
- One file (``acv_case_04.xlsx``): 60+ params/car (per-component running/fault
  flags, refrigeration system high/low pressure, several temperature probes).
- Even the "8-param" files don't use identical param *names* across cases
  (e.g. ``Outdoor Average Temperature`` vs. ``Outside Temperature Sensor
  Reading``).

Because of that last point, features are engineered at the level of a small,
fixed set of **semantic categories** (temperature, pressure, mode, fault,
...) inferred from keyword matches on each param's name, not at the level of
literal param names. This is what lets ``extract_features`` produce a
same-shape, same-meaning feature vector per car regardless of which literal
columns a given file happens to have -- required for leave-one-case-out
cross-validation across files with different schemas (see ``evaluate.py``).
"""

from __future__ import annotations

import re
import warnings
from collections import defaultdict
from typing import Dict, List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

# Matches headers like "Car 03 - ACV Running Mode" -> group(1)="03",
# group(2)="ACV Running Mode". Car ID is kept as the exact string from the
# header (e.g. "03", not "3" or "Car 3") since that's what submission output
# must reuse verbatim.
CAR_COL_RE = re.compile(r"^Car\s*(\d+)\s*-\s*(.+)$")

# Non-car metadata columns seen across files; anything else that doesn't
# match CAR_COL_RE is ignored (with a note) rather than assumed absent.
KNOWN_NON_CAR_COLS = {"Car model", "Train number", "Time"}


def load_case(filepath: str) -> pd.DataFrame:
    """Load one ACV case workbook into a tidy long-format DataFrame.

    Reads the file's own headers to discover car IDs and parameter names --
    never assumes a fixed column count/order, since schema differs across
    files (see module docstring).

    Parameters
    ----------
    filepath : str
        Path to an ``.xlsx`` file with columns ``Car model``, ``Train
        number``, ``Time``, and one or more ``Car NN - <param>`` columns.

    Returns
    -------
    pd.DataFrame
        Long/tidy format, one row per (timestamp, car, param), columns:

        - ``Time``       : pd.Timestamp, sample timestamp (sorted ascending)
        - ``car_id``     : str, exact car ID as it appears in the header
                            (e.g. ``"03"``)
        - ``param``      : str, parameter name (e.g. ``"ACV Running Mode"``)
        - ``value``      : object, raw cell value (numeric or string)
        - ``is_numeric`` : bool, whether this *param* (pooled across all its
                            cars in this file) is numeric or categorical --
                            decided once per param, not per car, so a param
                            is treated consistently even if one car's column
                            happens to be sparse/all-NaN.
    """
    df = pd.read_excel(filepath)

    if "Time" not in df.columns:
        raise ValueError(f"{filepath}: expected a 'Time' column, none found")
    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values("Time").reset_index(drop=True)

    car_cols: List[tuple] = []
    unmatched = []
    for col in df.columns:
        if col in KNOWN_NON_CAR_COLS:
            continue
        m = CAR_COL_RE.match(str(col))
        if m:
            car_id, param = m.group(1), m.group(2).strip()
            car_cols.append((col, car_id, param))
        else:
            unmatched.append(col)

    if not car_cols:
        raise ValueError(f"{filepath}: no 'Car NN - <param>' columns found")
    if unmatched:
        # Not fatal -- just means this file has some metadata column we
        # don't recognise yet. Surface it rather than silently drop it.
        print(f"  [load_case] {filepath}: ignoring unrecognised column(s): {unmatched}")

    # Decide numeric-vs-categorical per PARAM (pooling every car's column for
    # that param in this file), so the same param is handled consistently
    # even if a particular car's column is sparse.
    param_names = sorted({p for _, _, p in car_cols})
    param_is_numeric: Dict[str, bool] = {}
    for p in param_names:
        cols = [c for c, _cid, pp in car_cols if pp == p]
        pooled = pd.concat([df[c] for c in cols], ignore_index=True)
        non_null = pooled.notna().sum()
        if non_null == 0:
            param_is_numeric[p] = False
            continue
        numeric_pooled = pd.to_numeric(pooled, errors="coerce")
        param_is_numeric[p] = (numeric_pooled.notna().sum() / non_null) >= 0.99

    frames = []
    n = len(df)
    for col, car_id, param in car_cols:
        raw = df[col]
        is_numeric = param_is_numeric[param]
        value = pd.to_numeric(raw, errors="coerce") if is_numeric else raw
        frames.append(
            pd.DataFrame(
                {
                    "Time": df["Time"].values,
                    "car_id": car_id,
                    "param": param,
                    "value": value.values,
                    "is_numeric": is_numeric,
                }
            )
        )
    long_df = pd.concat(frames, ignore_index=True)
    long_df.attrs["source_file"] = filepath
    long_df.attrs["n_rows_raw"] = n
    return long_df


# ---------------------------------------------------------------------------
# Semantic categorisation of params (schema-invariant feature grouping)
# ---------------------------------------------------------------------------

# Order matters: first keyword match wins. Checked as case-insensitive
# substring match against the param name.
CATEGORY_KEYWORDS = [
    ("fault", ["fault", "alarm", "fire", "smoke"]),
    ("valid", ["valid", "self-check", "self check"]),
    ("pressure", ["pressure"]),
    ("temperature", ["temperature", "temp"]),
    ("mode", ["mode"]),
    ("running", ["running"]),
    ("closed", ["closed"]),
    ("load", ["load"]),
    ("command", ["command", "signal"]),
]
DEFAULT_CATEGORY = "other"

ALL_CATEGORIES = [c for c, _ in CATEGORY_KEYWORDS] + [DEFAULT_CATEGORY]

NUMERIC_STATS = ["z_mean", "z_absmean", "z_max", "num_extreme_rate"]
CATEGORICAL_STATS = ["disagree_rate", "switch_z", "cat_extreme_rate"]
# NOTE: the two stat lists must not share names -- a category (e.g. "load")
# can have both numeric and categorical params contributing to it, and a
# shared name would silently collide/overwrite in the `data` dict below.

# Fixed, schema-invariant universe of feature columns produced by
# extract_features for every file, regardless of that file's own literal
# param set. This is what makes feature vectors comparable/poolable across
# cases with different schemas (needed for LOO CV and the supervised model).
FEATURE_COLUMNS = [f"{cat}_{stat}" for cat in ALL_CATEGORIES for stat in NUMERIC_STATS] + [
    f"{cat}_{stat}" for cat in ALL_CATEGORIES for stat in CATEGORICAL_STATS
]


def categorize_param(param_name: str) -> str:
    """Map a raw param name to one of the fixed semantic categories."""
    name = param_name.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in name for kw in keywords):
            return category
    return DEFAULT_CATEGORY


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

MIN_VALID_CARS = 3  # need at least this many non-NaN cars at a timestamp to
# treat "row-wise" cross-car deviation at that timestamp as meaningful


def extract_features(case_df: pd.DataFrame) -> pd.DataFrame:
    """Turn a long-format case DataFrame (from ``load_case``) into one
    feature vector per car.

    For every parameter, cross-car statistics are computed *at each
    timestamp* (median/std for numeric params, majority vote for categorical
    params), each car's per-timestamp deviation from its 7 peers is
    aggregated over time, and finally averaged within each semantic category
    (see ``categorize_param``) so the resulting feature matrix has the same
    fixed columns (``FEATURE_COLUMNS``) no matter which literal params the
    source file had.

    Captures, per category:
    - ``{cat}_z_mean``       : signed mean cross-car z-score over time
                                (systematic bias vs. peers; numeric params)
    - ``{cat}_z_absmean``    : mean |z-score| over time (deviation magnitude)
    - ``{cat}_z_max``        : max |z-score| observed (spikes)
    - ``{cat}_disagree_rate``: fraction of time this car's value differs from
                                the cross-car majority (categorical params;
                                covers control-mode disagreement)
    - ``{cat}_switch_z``     : this car's own value-change frequency,
                                z-scored against its 7 peers' switch
                                frequency for the same param (categorical
                                params; covers mode-switch frequency)
    - ``{cat}_extreme_rate`` : fraction of time this car is uniquely the
                                most-deviant / sole dissenter among all cars

    Parameters
    ----------
    case_df : pd.DataFrame
        Output of ``load_case``.

    Returns
    -------
    pd.DataFrame
        Index = car_id (str), columns = ``FEATURE_COLUMNS`` (fixed set,
        float). Categories absent from this file are filled with 0.0 for
        every car (neutral, non-anomalous default) rather than NaN, so the
        matrix is always ready to feed straight into ranking/modeling code.
    """
    car_ids = sorted(case_df["car_id"].unique())
    param_is_numeric = case_df[["param", "is_numeric"]].drop_duplicates().set_index("param")["is_numeric"].to_dict()

    # bucket[(category, stat)][car_id] = list of per-param values to average
    bucket: Dict[tuple, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

    # Group once up front rather than re-scanning the full long DataFrame
    # with a boolean mask per param (this file can have 60+ params x 22k+
    # timestamps x 8 cars ~= 1M+ long-format rows, so a per-param `==` scan
    # adds up fast). `.pivot` (not `.pivot_table`) is used since (Time,
    # car_id) is unique per param by construction -- no aggregation needed,
    # which also avoids pivot_table's slower object-dtype groupby path.
    for param, group in case_df.groupby("param", sort=False, observed=True):
        is_numeric = param_is_numeric[param]
        wide = group.pivot(index="Time", columns="car_id", values="value")
        wide = wide.reindex(columns=car_ids)
        category = categorize_param(param)

        if is_numeric:
            _accumulate_numeric(wide, car_ids, category, bucket)
        else:
            _accumulate_categorical(wide, car_ids, category, bucket)

    # Aggregate each (category, stat) bucket -> mean across that category's
    # params, one scalar per car. Missing (category, stat) combos (category
    # not present in this file, or present only as numeric/only as
    # categorical) default to 0.0 for every car.
    data = {}
    for cat in ALL_CATEGORIES:
        for stat in NUMERIC_STATS + CATEGORICAL_STATS:
            col = f"{cat}_{stat}"
            per_car_lists = bucket.get((cat, stat))
            if per_car_lists:
                data[col] = {car: float(np.mean(vals)) if vals else 0.0 for car, vals in per_car_lists.items()}
            else:
                data[col] = {car: 0.0 for car in car_ids}

    feature_df = pd.DataFrame(data, index=car_ids)
    feature_df = feature_df.reindex(columns=FEATURE_COLUMNS, fill_value=0.0)
    feature_df.index.name = "car_id"
    return feature_df


def _accumulate_numeric(wide: pd.DataFrame, car_ids, category: str, bucket) -> None:
    """Row-wise (per-timestamp, cross-car) z-score deviation for one numeric param.

    Operates on a plain ``float64`` numpy array (rather than the pandas
    DataFrame directly) for speed: ``wide`` is pivoted out of a long-format
    DataFrame whose ``value`` column mixes numeric and categorical params
    and is therefore ``object``-dtype end to end, which makes pandas fall
    back to slow, unvectorised per-element ops (this was the single biggest
    cost on the 60+-param/22k-row file before switching to numpy here).
    """
    arr = wide.to_numpy(dtype="float64")  # (n_rows, n_cars)
    n_rows, n_cars = arr.shape

    # rows with <2 non-NaN cars trigger benign "all-NaN slice" / "dof<=0"
    # RuntimeWarnings from nanmedian/nanstd; the resulting NaNs are already
    # handled downstream via `valid_rows` (MIN_VALID_CARS=3), so suppress
    # rather than let them spam stdout for every such row across 6 files.
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        n_valid = np.sum(~np.isnan(arr), axis=1)
        valid_rows = n_valid >= MIN_VALID_CARS
        row_median = np.nanmedian(arr, axis=1)
        row_std = np.nanstd(arr, axis=1, ddof=1)
    row_std = np.where(row_std == 0, np.nan, row_std)

    dev = arr - row_median[:, None]
    z = dev / row_std[:, None]
    z = np.where(valid_rows[:, None], z, np.nan)
    abs_dev = np.where(valid_rows[:, None], np.abs(dev), np.nan)

    n_rows_valid = int(valid_rows.sum())
    if n_rows_valid == 0:
        for car in car_ids:
            bucket[(category, "z_mean")][car].append(0.0)
            bucket[(category, "z_absmean")][car].append(0.0)
            bucket[(category, "z_max")][car].append(0.0)
            bucket[(category, "num_extreme_rate")][car].append(0.0)
        return

    # per-timestamp "worst" car = largest absolute deviation among cars with
    # a valid row; ties broken by lowest column index (np.argmax default).
    filled = np.where(np.isnan(abs_dev), -np.inf, abs_dev)
    worst_idx = np.argmax(filled, axis=1)
    counts = np.bincount(worst_idx[valid_rows], minlength=n_cars)

    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        z_mean = np.nanmean(z, axis=0)
        z_absmean = np.nanmean(np.abs(z), axis=0)
        z_max = np.nanmax(np.abs(z), axis=0)
    # nan where a car had zero valid timestamps for this param -> neutral 0.0
    z_mean = np.nan_to_num(z_mean, nan=0.0)
    z_absmean = np.nan_to_num(z_absmean, nan=0.0)
    z_max = np.nan_to_num(z_max, nan=0.0, posinf=0.0, neginf=0.0)

    for i, car in enumerate(car_ids):
        bucket[(category, "z_mean")][car].append(float(z_mean[i]))
        bucket[(category, "z_absmean")][car].append(float(z_absmean[i]))
        bucket[(category, "z_max")][car].append(float(z_max[i]))
        bucket[(category, "num_extreme_rate")][car].append(counts[i] / n_rows_valid)


def _factorize_wide(wide: pd.DataFrame) -> np.ndarray:
    """Encode a (Time x car) object DataFrame of categorical values as an
    integer-code numpy array (same shape), NaN -> -1.

    Equality on ``object``-dtype pandas data falls back to slow
    element-by-element Python comparisons; factorizing once up front and
    doing every subsequent comparison on plain ``int32`` numpy arrays turns
    what was ~20s of pandas object-array `eq`/`ne` calls (dominant cost on
    the 22k-row/60-param file) into a sub-second numpy operation. Codes are
    only meaningful within one param's call (arbitrary integer labels).
    """
    flat = wide.to_numpy(dtype=object).ravel()
    codes, _ = pd.factorize(flat, sort=False)
    return codes.reshape(wide.shape).astype("int32")


def _row_majority_codes(codes: np.ndarray) -> np.ndarray:
    """Per-row majority-vote code among a small number of car columns
    (integer-code numpy array, rows=Time, cols=car). Returns an (n_rows,)
    int32 array of the majority code per row (-1 where every car is NaN).

    O(ncars^2) pairwise-equality, fully vectorised in numpy -- car count is
    always small (~8) so this is cheap regardless of row count.
    """
    n_rows, n_cars = codes.shape
    notna = codes != -1
    match_counts = np.zeros((n_rows, n_cars), dtype="int32")
    for j in range(n_cars):
        col_j = codes[:, j : j + 1]
        match_counts[:, j] = ((codes == col_j) & notna).sum(axis=1)
    majority_pos = match_counts.argmax(axis=1)
    majority = codes[np.arange(n_rows), majority_pos]
    has_any = notna.any(axis=1)
    majority = np.where(has_any, majority, -1)
    return majority


def _accumulate_categorical(wide: pd.DataFrame, car_ids, category: str, bucket) -> None:
    """Majority-vote disagreement + switch-rate deviation for one categorical param."""
    codes = _factorize_wide(wide)  # (n_rows, n_cars) int32, -1 = NaN
    notna = codes != -1
    n_valid = notna.sum(axis=1)
    valid_rows = n_valid >= MIN_VALID_CARS

    majority = _row_majority_codes(codes)
    disagree = (codes != majority[:, None]) & notna & valid_rows[:, None]
    n_disagree = disagree.sum(axis=1)
    unique_dissent = n_disagree == 1

    n_rows_valid = int(valid_rows.sum())

    # own value-change (switch) rate per car for this param, then z-scored
    # across this file's cars (n=len(car_ids), small but it's a relative
    # measure by construction -- "does this car switch more than its own
    # train's peers").
    own_valid = notna[1:] & notna[:-1]
    changed = (codes[1:] != codes[:-1]) & own_valid
    with np.errstate(invalid="ignore"):
        switch_rate = np.where(own_valid.sum(axis=0) > 0, changed.sum(axis=0) / np.maximum(own_valid.sum(axis=0), 1), 0.0)
    mu, sigma = np.nanmean(switch_rate), np.nanstd(switch_rate)

    for idx, car in enumerate(car_ids):
        if n_rows_valid == 0:
            disagree_rate = 0.0
            extreme_rate = 0.0
        else:
            dc = disagree[:, idx][valid_rows]
            disagree_rate = float(dc.mean()) if dc.size else 0.0
            n_extreme = int((disagree[:, idx] & unique_dissent).sum())
            extreme_rate = n_extreme / n_rows_valid

        switch_z = 0.0 if sigma <= 1e-9 else float((switch_rate[idx] - mu) / sigma)

        bucket[(category, "disagree_rate")][car].append(disagree_rate)
        bucket[(category, "switch_z")][car].append(switch_z)
        bucket[(category, "cat_extreme_rate")][car].append(extreme_rate)
