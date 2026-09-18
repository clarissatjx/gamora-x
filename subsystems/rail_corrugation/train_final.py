"""Phase 6: fit the shipped model on the full modelling frame and save the artifact.

Variant A from the Phase 5 ablations (all features, class_weight="balanced"), which no
challenger beat. Cross-validation is what estimates the score; this fit uses every
available row so the shipped model sees as much of the 14 Side I examples as possible.

Run:  python -m subsystems.rail_corrugation.train_final
"""
import joblib
import numpy as np

from . import config
from .model import build_model
from .split import feature_columns, load_training_frame

ARTIFACT_PATH = config.ARTIFACTS_DIR / "rail_model.joblib"


def train_and_save(path=ARTIFACT_PATH):
    df = load_training_frame(verbose=True)
    cols = feature_columns(df)

    model = build_model(class_weight="balanced")
    model.fit(df[cols].to_numpy(dtype=np.float64), df["label"].to_numpy())

    # The column list travels with the model: inference must build features in exactly
    # this order, and a silent reordering would be a hard bug to spot.
    payload = {
        "model": model,
        "feature_cols": cols,
        "classes": list(config.CLASSES),
        "n_train_rows": len(df),
        "train_class_counts": df["label"].value_counts().to_dict(),
    }
    path.parent.mkdir(exist_ok=True)
    joblib.dump(payload, path)
    return payload, path


if __name__ == "__main__":
    payload, path = train_and_save()
    print(f"\nTrained on {payload['n_train_rows']} rows, "
          f"{len(payload['feature_cols'])} features")
    print(f"Class counts: {payload['train_class_counts']}")
    print(f"Wrote {path}  ({path.stat().st_size / 1024:.0f} KB)")
