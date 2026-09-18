"""
ACV inference module -- the single source of truth for turning one raw ACV
case file into a ranked-car prediction.

This is what the future shared Streamlit app (``app/app.py``, not yet built)
will import to serve on-screen predictions, and it's also what the batch CLI
script (``subsystems/acv/predict.py``) imports to regenerate
``acv_predictions.csv``. Neither caller reimplements feature extraction or
ranking -- both just chain the Checkpoint A building blocks:
``features.load_case`` -> ``features.extract_features`` ->
``rank.score_cars(method="heuristic")`` (fixed-prior weights; see the
Checkpoint A LOOCV verdict in ``subsystems/acv/evaluate.py`` for why no
per-inference fold-fitting happens here).
"""

from __future__ import annotations

import os
from typing import List, Tuple

import pandas as pd

from subsystems.acv.features import extract_features, load_case
from subsystems.acv.rank import physics_gap, score_cars

# "blend": within-file z of the physics gap (cabin temperature minus cooling setpoint, the
# direct thermal signature of a leak) averaged with the fixed-prior heuristic. Scores 1.000
# on all six labelled cases; the heuristic alone also does, but its Test top pick was driven
# by the "Information Valid" telemetry flag rather than temperature. See subsystems/acv/PLAN.md.
DEFAULT_METHOD = "blend"


def _resolve_file_id(file) -> str:
    """Source filename (including extension), for the output `file_id`
    column -- works for a plain path (str/Path) or a file-like object that
    exposes a `.name` attribute (e.g. Streamlit's `UploadedFile`)."""
    name = getattr(file, "name", None)
    if name is not None:
        return os.path.basename(str(name))
    return os.path.basename(str(file))


def rank_case(file, method: str = DEFAULT_METHOD) -> Tuple[str, List[str]]:
    """Rank one raw ACV case file's cars most-to-least-likely to have the
    refrigerant leak.

    Parameters
    ----------
    file : str, os.PathLike, or file-like object
        Path to a raw ``.xlsx`` ACV case file (e.g. from a batch script), or
        an already-open file-like object with the same raw ``.xlsx`` content
        (e.g. a Streamlit ``UploadedFile`` from ``st.file_uploader``).

    Returns
    -------
    (file_id, ranked_cars) : (str, list[str])
        ``file_id`` is the source filename including its extension.
        ``ranked_cars`` is the car IDs, most-to-least-likely faulty, in the
        file's own native ID format (e.g. ``"03"``, not ``"Car 3"``).
    """
    file_id = _resolve_file_id(file)
    case_df = load_case(file)
    feature_df = extract_features(case_df)
    gap = physics_gap(case_df) if method in ("physics", "blend") else None
    ranked_cars, _scores = score_cars(feature_df, method=method, gap=gap)
    return file_id, ranked_cars


def predict_file(file, method: str = DEFAULT_METHOD) -> pd.DataFrame:
    """Predict one raw ACV case file -> one-row DataFrame matching the exact
    ``acv_predictions.csv`` submission schema: columns ``file_id``,
    ``ranked_cars`` (pipe-``|``-joined car IDs, most-to-least-likely
    faulty). No ``prediction`` column, no extras.
    """
    file_id, ranked_cars = rank_case(file, method=method)
    return pd.DataFrame({"file_id": [file_id], "ranked_cars": ["|".join(ranked_cars)]})
