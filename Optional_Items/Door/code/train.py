from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_COLUMNS, featurize
from .loader import load_stream
from .segment import segment

ROOT = Path(__file__).resolve().parents[2]
TRAIN_CSV = ROOT / "data/Door/Train.csv"
ANSWERS_CSV = ROOT / "data/Door/Train_Segments_Answer.csv"
MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"

POSITIVE = "Abnormal resistance"
HOLDOUT_TRAIN_N = 88


def make_primary():
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))


def make_crosscheck():
    return RandomForestClassifier(n_estimators=300, random_state=0)


def load_training_set():
    df = load_stream(TRAIN_CSV)
    segs = segment(df)
    ans = pd.read_csv(ANSWERS_CSV)
    assert segs.start_str.is_unique and ans.start_time.is_unique, "segment start keys must be unique"
    merged = segs.merge(ans[["start_time", "status"]], left_on="start_str", right_on="start_time", how="left")
    assert len(merged) == len(segs) == len(ans), f"expected {len(ans)} labelled segments, got {len(segs)}"
    assert merged.status.notna().all(), "every segment must match a labelled answer row"
    X = featurize(df, segs)
    y = (merged.status == POSITIVE).astype(int).to_numpy()
    return X, y


def main():
    X, y = load_training_set()
    strat = y * 2 + X.op.to_numpy()
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=0)

    print(f"training set: {X.shape}, abnormal={y.sum()}")
    results = {}
    for name, model in [("primary(logreg)", make_primary()), ("crosscheck(rf)", make_crosscheck())]:
        acc = cross_val_score(model, X, y, cv=list(cv.split(X, strat)), scoring="accuracy")
        f1 = cross_val_score(model, X, y, cv=list(cv.split(X, strat)), scoring="f1")
        results[name] = acc.mean()
        print(f"  CV  {name:16s} acc={acc.mean():.3f}±{acc.std():.3f}  abnormal-F1={f1.mean():.3f}")

    tr, te = np.arange(HOLDOUT_TRAIN_N), np.arange(HOLDOUT_TRAIN_N, len(y))
    holdout = {}
    for name, model in [("primary(logreg)", make_primary()), ("crosscheck(rf)", make_crosscheck())]:
        model.fit(X.iloc[tr], y[tr])
        pred = model.predict(X.iloc[te])
        holdout[name] = accuracy_score(y[te], pred)
        print(f"  HOLDOUT(last {len(te)}) {name:16s} acc={holdout[name]:.3f}  abnormal-F1={f1_score(y[te], pred):.3f}")

    assert results["primary(logreg)"] >= 0.97, "gate: primary CV accuracy >= 0.97"
    assert holdout["primary(logreg)"] >= 0.95, "gate: primary holdout accuracy >= 0.95"

    primary = make_primary().fit(X, y)
    crosscheck = make_crosscheck().fit(X, y)
    coefs = pd.Series(primary[-1].coef_[0], index=FEATURE_COLUMNS).sort_values()
    print("\nlogistic coefficients (standardised features, + => more likely Abnormal):")
    print(coefs.round(2).to_string())

    joblib.dump({"primary": primary, "crosscheck": crosscheck, "feature_columns": FEATURE_COLUMNS}, MODEL_PATH)
    print(f"\nsaved {MODEL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
