"""
ACV subsystem: turn a per-car feature matrix (see ``features.extract_features``)
into a most-to-least-likely-faulty ranking of the 8 cars in one file.

Two approaches are provided, per the ``acv-fault-ranking`` skill's guidance
that n=6 labelled cases is too small to trust a fully end-to-end supervised
classifier without a strong prior:

- ``heuristic_scores`` / ``fit_heuristic_weights``: unsupervised-by-default,
  weighted sum of within-file z-scored anomaly features. Weights can either
  be a fixed, domain-reasoned prior (``HEURISTIC_WEIGHTS``) or *lightly*
  data-tuned per point-biserial correlation with the faulty-car label,
  pooled across a set of training cases (still not a black-box classifier --
  each feature's weight is independent and clipped to >=0).
- ``fit_supervised`` / ``score_cars(..., method="supervised")``: a small
  logistic regression over category-level scores (``reduce_to_category_scores``),
  deliberately low-dimensional (~10 features) to have a fighting chance at
  n=6 cases (~40-48 car-rows).

See ``evaluate.py`` for the leave-one-case-out comparison between the two
and the resulting recommendation.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from subsystems.acv.features import CATEGORICAL_STATS, NUMERIC_STATS, ALL_CATEGORIES

# ---------------------------------------------------------------------------
# Unsupervised heuristic
# ---------------------------------------------------------------------------

# Fixed, domain-reasoned prior weights (used as-is for the "naive" heuristic,
# and as the fallback if data-driven correlation weighting degenerates -- see
# `fit_heuristic_weights`). A refrigerant leak should show up as: abnormal
# cabin/outdoor temperature behaviour relative to peers, the control system
# disagreeing with/switching modes more than peers to compensate, abnormal
# refrigeration pressure (only present in the 60+-param file), and more
# fault/invalid readings.
HEURISTIC_WEIGHTS: Dict[str, float] = {
    "temperature_z_absmean": 1.5,
    "temperature_z_max": 1.0,
    "temperature_num_extreme_rate": 1.0,
    "pressure_z_absmean": 1.5,
    "pressure_z_max": 1.0,
    "pressure_num_extreme_rate": 1.0,
    "mode_disagree_rate": 1.2,
    "mode_switch_z": 0.8,
    "mode_cat_extreme_rate": 1.0,
    "running_z_absmean": 0.8,
    "running_disagree_rate": 0.8,
    "running_num_extreme_rate": 0.6,
    "running_cat_extreme_rate": 0.6,
    "fault_z_absmean": 1.5,
    "fault_disagree_rate": 1.5,
    "fault_num_extreme_rate": 1.2,
    "fault_cat_extreme_rate": 1.2,
    "valid_disagree_rate": 1.0,
    "valid_z_absmean": 1.0,
    "valid_num_extreme_rate": 0.8,
    "valid_cat_extreme_rate": 0.8,
    "closed_disagree_rate": 0.5,
    "closed_z_absmean": 0.5,
    "load_disagree_rate": 0.5,
    "load_z_absmean": 0.5,
}


def _coerce_feature_df(feature_vectors) -> pd.DataFrame:
    """Accept either a DataFrame (index=car_id) or a dict[car_id -> vector]."""
    if isinstance(feature_vectors, pd.DataFrame):
        return feature_vectors
    if isinstance(feature_vectors, dict):
        return pd.DataFrame.from_dict(feature_vectors, orient="index")
    raise TypeError(f"expected a DataFrame or dict[car_id -> vector], got {type(feature_vectors)}")


def _within_file_z(feature_df: pd.DataFrame, cols: Sequence[str]) -> pd.DataFrame:
    """z-score each feature column across the 8 cars *within this one file*
    (never across files -- files differ in units/scale/schema)."""
    sub = feature_df[cols]
    z = (sub - sub.mean()) / sub.std(ddof=0).replace(0, np.nan)
    return z.fillna(0.0)


def heuristic_scores(feature_df: pd.DataFrame, weights: Optional[Dict[str, float]] = None) -> pd.Series:
    """Unsupervised per-car anomaly score.

    Each feature is z-scored across the 8 cars within this file, clipped to
    >=0 (only "more anomalous than the peer average" contributes -- being
    unusually *quiet* on one channel shouldn't cancel out being loud on
    another), then combined as a weighted average.

    Returns a Series indexed by car_id, sorted descending (most anomalous
    first).
    """
    weights = weights or HEURISTIC_WEIGHTS
    cols = [c for c in feature_df.columns if c in weights and weights[c] != 0]
    if not cols:
        cols = list(feature_df.columns)
        weights = {c: 1.0 for c in cols}

    z = _within_file_z(feature_df, cols).clip(lower=0)
    w = pd.Series({c: weights.get(c, 1.0) for c in cols})
    score = (z * w).sum(axis=1) / w.sum()
    return score.sort_values(ascending=False)


def fit_heuristic_weights(
    train_feature_dfs: Sequence[pd.DataFrame],
    train_labels: Sequence[str],
    base_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Data-tune the heuristic's feature weights on a set of training cases.

    For every feature column, compute its point-biserial correlation with
    the binary "is this car the known-faulty one" label, pooled across all
    (car, file) rows in the training cases (each file's features are
    z-scored within that file first, matching how they're used at score
    time). Weights are clipped to >=0 (a feature that's *lower* for faulty
    cars isn't a useful positive-anomaly signal here) and normalised to sum
    to 1.

    This intentionally stays close in spirit to the fixed-prior heuristic
    (each feature's contribution is still independent and monotonic) rather
    than becoming an opaque joint classifier -- appropriate at n=5 training
    cases per fold.

    Falls back to ``base_weights`` (default: ``HEURISTIC_WEIGHTS``) if no
    feature shows positive correlation (can happen with very few training
    cases).
    """
    if len(train_feature_dfs) != len(train_labels):
        raise ValueError("train_feature_dfs and train_labels must be the same length")

    all_cols = train_feature_dfs[0].columns
    z_rows, y_rows = [], []
    for fdf, faulty in zip(train_feature_dfs, train_labels):
        z_rows.append(_within_file_z(fdf, all_cols))
        y_rows.extend([1 if car == faulty else 0 for car in fdf.index])

    Z = pd.concat(z_rows, axis=0, ignore_index=True)
    y = np.array(y_rows, dtype=float)

    weights: Dict[str, float] = {}
    for col in Z.columns:
        x = Z[col].to_numpy(dtype=float)
        if x.std() < 1e-9 or y.std() < 1e-9:
            weights[col] = 0.0
            continue
        corr = np.corrcoef(x, y)[0, 1]
        weights[col] = max(corr, 0.0) if not np.isnan(corr) else 0.0

    total = sum(weights.values())
    if total <= 0:
        return dict(base_weights or HEURISTIC_WEIGHTS)
    return {k: v / total for k, v in weights.items() if v > 0}


# ---------------------------------------------------------------------------
# Physics rule: a leaking unit cannot pull its cabin down to the cooling setpoint
# ---------------------------------------------------------------------------

COOLING_MODES = {"Automatic Cooling", "Full Cooling", "Half Cooling"}
MODE_PARAM = "ACV Running Mode"
# (cabin temperature, cooling setpoint) under each schema seen so far
TEMP_PAIRS = (
    ("Indoor Average Temperature", "ACV Control Temperature (Cooling)"),
    ("Passenger Cabin Temperature Detected Value", "Target Temperature Value"),
)


def physics_gap(case_df: pd.DataFrame) -> pd.Series:
    """Mean (cabin temperature - cooling setpoint) per car over cooling-mode timestamps.

    This is the direct thermal signature of refrigerant loss and has no free parameters.
    NaN for cars that carry no cabin-temperature measurement in this file (case_04 has
    it for four of eight cars), which the callers rank below the measured cars.
    """
    car_ids = sorted(case_df["car_id"].unique())
    params = set(case_df["param"].unique())
    pair = next((p for p in TEMP_PAIRS if set(p) <= params), None)
    if pair is None:
        return pd.Series(np.nan, index=car_ids)

    def wide(param):
        w = case_df[case_df["param"] == param].pivot(index="Time", columns="car_id", values="value")
        return w.apply(pd.to_numeric, errors="coerce").reindex(columns=car_ids)

    gap = wide(pair[0]) - wide(pair[1])
    if MODE_PARAM in params:
        mode = case_df[case_df["param"] == MODE_PARAM].pivot(index="Time", columns="car_id", values="value")
        cool = mode.astype(str).isin(COOLING_MODES).reindex(index=gap.index, columns=car_ids).fillna(False)
        if cool.to_numpy().any():
            gap = gap.where(cool)
    return gap.mean().reindex(car_ids)


def _z(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    return (s - s.mean()) / (sd if sd > 0 else 1.0)


def blend_scores(feature_df: pd.DataFrame, gap: pd.Series, alpha: float = 0.5,
                 weights: Optional[Dict[str, float]] = None) -> pd.Series:
    """alpha * z(physics gap) + (1 - alpha) * z(heuristic score), both z-scored within the
    file. Cars without a cabin-temperature measurement are ordered by the heuristic alone
    and placed after every measured car. alpha=1 is the pure physics ranking."""
    h = heuristic_scores(feature_df, weights=weights).reindex(feature_df.index)
    zh = _z(h)
    gap = gap.reindex(feature_df.index)
    measured = gap.notna()
    zp = _z(gap[measured]).reindex(feature_df.index)
    score = np.where(measured, alpha * zp.fillna(0.0) + (1 - alpha) * zh, zh - 10.0)
    return pd.Series(score, index=feature_df.index).sort_values(ascending=False)


# ---------------------------------------------------------------------------
# Supervised approach (small logistic regression over category-level scores)
# ---------------------------------------------------------------------------

# Magnitude-type stats only (exclude signed z_mean) so every reduced feature
# is "higher = more anomalous", consistent across categories.
_REDUCE_STATS = [s for s in NUMERIC_STATS if s != "z_mean"] + [s for s in CATEGORICAL_STATS if s != "switch_z"]


def reduce_to_category_scores(feature_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse the full ~70-column feature matrix into one score per
    semantic category (mean of that category's magnitude-type stat columns:
    ``z_absmean``, ``z_max``, ``num_extreme_rate``, ``disagree_rate``,
    ``cat_extreme_rate``; the signed ``z_mean``/``switch_z`` columns are
    excluded so every reduced column points the same direction, "higher =
    more anomalous").

    Used as the (deliberately low-dimensional, ~10-column) input to the
    supervised model, since the full ~70-column matrix is too wide relative
    to n=6 training cases.
    """
    data = {}
    for cat in ALL_CATEGORIES:
        cols = [f"{cat}_{stat}" for stat in _REDUCE_STATS if f"{cat}_{stat}" in feature_df.columns]
        data[f"{cat}_score"] = feature_df[cols].mean(axis=1) if cols else pd.Series(0.0, index=feature_df.index)
    return pd.DataFrame(data, index=feature_df.index)


def fit_supervised(
    train_feature_dfs: Sequence[pd.DataFrame],
    train_labels: Sequence[str],
    C: float = 0.5,
):
    """Fit a small, heavily-regularised logistic regression: category-level
    scores (~10 features) -> P(this car is the faulty one), pooled across
    training cases' cars (1 positive row per case, 7 negative rows per case).

    Returns ``(model, scaler)`` -- both fit on the training cases only (no
    leakage; see ``train-val-split-strategy`` skill), to be applied to
    held-out/test cases via ``score_cars(..., method="supervised", model=...,
    scaler=...)``.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    if len(train_feature_dfs) != len(train_labels):
        raise ValueError("train_feature_dfs and train_labels must be the same length")

    reduced = [reduce_to_category_scores(fdf) for fdf in train_feature_dfs]
    X = pd.concat(reduced, axis=0, ignore_index=True)
    y = np.concatenate(
        [np.array([1 if car == faulty else 0 for car in fdf.index]) for fdf, faulty in zip(train_feature_dfs, train_labels)]
    )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X.values)

    model = LogisticRegression(C=C, class_weight="balanced", max_iter=2000)
    model.fit(X_scaled, y)
    return model, scaler


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


def score_cars(
    feature_vectors,
    method: str = "heuristic",
    weights: Optional[Dict[str, float]] = None,
    model=None,
    scaler=None,
    gap: Optional[pd.Series] = None,
) -> Tuple[List[str], pd.Series]:
    """Rank all cars in one file most-to-least-likely faulty.

    Parameters
    ----------
    feature_vectors : pd.DataFrame or dict[car_id -> vector]
        Per-car feature matrix for ONE file (e.g. ``extract_features``'s
        output for a single case), index/keys = car_id.
    method : {"heuristic", "supervised", "physics", "blend"}
        "physics" ranks by the cabin-minus-setpoint gap (see ``physics_gap``); "blend"
        averages its within-file z-score with the heuristic's. Both need ``gap``.
    weights : dict, optional
        Feature weights for ``method="heuristic"`` (default: fixed prior
        ``HEURISTIC_WEIGHTS``, or pass a fitted dict from
        ``fit_heuristic_weights``).
    model, scaler :
        Fitted objects from ``fit_supervised``, required for
        ``method="supervised"``.

    Returns
    -------
    (ranked_car_ids, scores) : (list[str], pd.Series)
        ``ranked_car_ids`` is most-to-least-likely faulty. ``scores`` is
        indexed by car_id, sorted to match, for debugging/visualisation
        (higher = more anomalous / more likely faulty).
    """
    feature_df = _coerce_feature_df(feature_vectors)

    if method == "heuristic":
        scores = heuristic_scores(feature_df, weights=weights)
    elif method in ("physics", "blend"):
        if gap is None:
            raise ValueError(f"method={method!r} requires `gap` (see physics_gap)")
        scores = blend_scores(feature_df, gap, alpha=1.0 if method == "physics" else 0.5, weights=weights)
    elif method == "supervised":
        if model is None or scaler is None:
            raise ValueError("method='supervised' requires a fitted `model` and `scaler` (see fit_supervised)")
        reduced = reduce_to_category_scores(feature_df)
        X_scaled = scaler.transform(reduced.values)
        proba = model.predict_proba(X_scaled)[:, 1]
        scores = pd.Series(proba, index=feature_df.index).sort_values(ascending=False)
    else:
        raise ValueError(f"unknown method: {method!r} (expected 'heuristic', 'supervised', 'physics' or 'blend')")

    ranked = list(scores.index)
    return ranked, scores
