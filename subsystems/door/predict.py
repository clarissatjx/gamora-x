import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .features import featurize
from .loader import load_stream
from .segment import segment

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
LABELS = np.array(["Normal", "Abnormal resistance"])
OUTPUT_COLUMNS = ["start_time", "end_time", "prediction", "confidence"]


def load_model(path=MODEL_PATH):
    return joblib.load(path)


def run(df: pd.DataFrame, bundle=None):
    """Segment + featurise + classify an already-loaded stream.

    Returns (segments, features, p_abnormal, crosscheck_labels)."""
    bundle = bundle or load_model()
    segs = segment(df)
    X = featurize(df, segs)[bundle["feature_columns"]]
    p_abnormal = bundle["primary"].predict_proba(X)[:, 1]
    crosscheck = LABELS[bundle["crosscheck"].predict(X)]
    return segs, X, p_abnormal, crosscheck


def to_output(segs: pd.DataFrame, p_abnormal: np.ndarray) -> pd.DataFrame:
    pred = LABELS[(p_abnormal >= 0.5).astype(int)]
    conf = np.where(p_abnormal >= 0.5, p_abnormal, 1 - p_abnormal)
    return pd.DataFrame({
        "start_time": segs.start_str.values,
        "end_time": segs.end_str.values,
        "prediction": pred,
        "confidence": np.round(conf, 3),
    })[OUTPUT_COLUMNS]


def predict(path, bundle=None) -> pd.DataFrame:
    df = load_stream(path)
    segs, _, p_abnormal, _ = run(df, bundle)
    return to_output(segs, p_abnormal)


def main():
    ap = argparse.ArgumentParser(description="Door: segment a stream and classify each cycle.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = predict(args.input)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"wrote {len(out)} segments -> {args.output}")
    print(out.prediction.value_counts().to_string())


if __name__ == "__main__":
    main()
