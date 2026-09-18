"""Phase 4: baseline model + macro-F1 cross-validation.

The evaluation helpers here are written to be reused by the Phase 5 ablations, so every
variant is measured exactly the same way.

Run:  python -m subsystems.rail_corrugation.model
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from . import config
from .split import feature_columns, load_training_frame, make_folds

RANDOM_STATE = 42


def build_model(class_weight="balanced", random_state=RANDOM_STATE):
    return HistGradientBoostingClassifier(
        class_weight=class_weight,
        random_state=random_state,
    )


def cross_validate(df, folds, make_estimator=build_model, feature_cols=None):
    """Fit one estimator per fold and collect per-fold metrics + out-of-fold predictions.

    The estimator is constructed fresh inside each fold, so nothing is fit on data outside
    that fold's training portion.
    """
    feature_cols = feature_cols if feature_cols is not None else feature_columns(df)
    X = df[feature_cols].to_numpy(dtype=np.float64)
    y = df["label"].to_numpy()

    oof_pred = np.empty(len(df), dtype=object)
    per_fold = []

    for fold_i, (train_idx, val_idx) in enumerate(folds):
        model = make_estimator()
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[val_idx])
        oof_pred[val_idx] = pred

        per_class = f1_score(
            y[val_idx], pred, labels=list(config.CLASSES), average=None, zero_division=0
        )
        per_fold.append({
            "fold": fold_i,
            **{f"F1_{c}": per_class[i] for i, c in enumerate(config.CLASSES)},
            "macro_F1": f1_score(
                y[val_idx], pred, labels=list(config.CLASSES),
                average="macro", zero_division=0,
            ),
            "accuracy": accuracy_score(y[val_idx], pred),
        })

    return {
        "per_fold": pd.DataFrame(per_fold),
        "oof_pred": oof_pred,
        "y_true": y,
        "feature_cols": feature_cols,
    }


def pooled_scores(y_true, y_pred):
    """Metrics computed once over all out-of-fold predictions. This mirrors how the
    organisers score the test set (one macro F1 over the whole set) more closely than
    averaging per-fold F1s, which is unstable when a fold holds only 2 Side I files."""
    per_class = f1_score(
        y_true, y_pred, labels=list(config.CLASSES), average=None, zero_division=0
    )
    return {
        **{f"F1_{c}": per_class[i] for i, c in enumerate(config.CLASSES)},
        "macro_F1": f1_score(
            y_true, y_pred, labels=list(config.CLASSES), average="macro", zero_division=0
        ),
        "accuracy": accuracy_score(y_true, y_pred),
    }


if __name__ == "__main__":
    df = load_training_frame(verbose=True)
    folds = make_folds(df)
    results = cross_validate(df, folds)

    print("\nPer-fold validation scores:")
    print(results["per_fold"].to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    means = results["per_fold"].drop(columns="fold").mean()
    stds = results["per_fold"].drop(columns="fold").std()
    print("\nMean across folds:")
    for k in means.index:
        print(f"  {k:<16} {means[k]:.3f}  (sd {stds[k]:.3f})")

    pooled = pooled_scores(results["y_true"], results["oof_pred"])
    print("\nPooled over all out-of-fold predictions (closest analogue to the test score):")
    for k, v in pooled.items():
        print(f"  {k:<16} {v:.3f}")

    print(f"\n  >> accuracy {pooled['accuracy']:.3f} vs macro F1 {pooled['macro_F1']:.3f} "
          f"-- the gap is why the metric is macro F1, not accuracy")

    cm = confusion_matrix(
        results["y_true"], results["oof_pred"], labels=list(config.CLASSES)
    )
    print("\nOut-of-fold confusion matrix (rows = true, cols = predicted):")
    print(pd.DataFrame(cm, index=config.CLASSES, columns=config.CLASSES).to_string())

    always_normal = np.full(len(df), "Normal", dtype=object)
    baseline = pooled_scores(results["y_true"], always_normal)
    print(f"\nReference -- an always-Normal model on this frame: "
          f"macro F1 {baseline['macro_F1']:.3f}, accuracy {baseline['accuracy']:.3f}")

    # The CV frame excludes stationary files, but the real test set contains them (9/68),
    # and the explicit `speed == 0 => Normal` rule gets them right for free. Adding them
    # back as correct Normals estimates the score on the actual test distribution.
    n_stationary = 38
    y_full = np.concatenate([results["y_true"], np.full(n_stationary, "Normal", dtype=object)])
    pred_full = np.concatenate([results["oof_pred"], np.full(n_stationary, "Normal", dtype=object)])
    full = pooled_scores(y_full, pred_full)
    print("\nEstimated score on the full test distribution "
          "(stationary files added back, answered by the explicit rule):")
    for k, v in full.items():
        print(f"  {k:<16} {v:.3f}")
