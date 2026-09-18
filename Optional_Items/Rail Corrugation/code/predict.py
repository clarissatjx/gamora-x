"""Phase 6: the single inference path for Rail Corrugation.

Every caller goes through here -- the batch script that generates `rail_predictions.csv`,
and anything that later integrates this subsystem -- so the logic is never forked. The
`speed == 0 => Normal` rule lives here rather than in any caller, for the same reason.

    from subsystems.rail_corrugation.predict import predict_rail
    label = predict_rail("Test1.csv")          # -> "Normal" | "Side I" | "Side II"

`predict_rail_detailed` returns the same label plus the supporting numbers (class
probabilities, derived speed, whether the stationary rule fired) for a caller to display.

CLI:  python -m subsystems.rail_corrugation.predict --input <dir|file> --output preds.csv
"""
import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import config
from .features import extract_file_features
from .split import is_stationary
from .train_final import ARTIFACT_PATH

_ARTIFACT = None

STATIONARY_LABEL = "Normal"
STATIONARY_REASON = (
    "The speed sensor shows no wheel rotation, so the train is stationary. A stationary "
    "train cannot generate the wheel-rail excitation that produces a corrugation "
    "signature, so this file is reported Normal without consulting the model."
)


def load_artifact(path=ARTIFACT_PATH):
    """Load (and cache) the trained model, so repeated calls don't reload it from disk.

    The committed artifact was pickled under numpy 2; on numpy 1.x it fails to unpickle
    (`PCG64 is not a known BitGenerator`). Training is deterministic and takes ~5 s from the
    cached feature table, and a local retrain reproduces the submitted predictions exactly
    (verified on all 68 test files), so fall back to that, saved beside the artifact as an
    untracked *.local.joblib.
    """
    global _ARTIFACT
    if _ARTIFACT is None:
        if not path.exists():
            raise FileNotFoundError(
                f"No trained model at {path}. Run: "
                "python -m subsystems.rail_corrugation.train_final"
            )
        local = path.with_suffix(".local.joblib")
        try:
            _ARTIFACT = joblib.load(local if local.exists() else path)
        except Exception:  # noqa: BLE001 - cross-version pickle; retrain rather than fail
            from .train_final import train_and_save
            _ARTIFACT, _ = train_and_save(path=local)
    return _ARTIFACT


def predict_rail_detailed(source, artifact=None):
    """Classify one raw recording. `source` is a path or any file-like object pandas can
    read, so a caller holding an uploaded file can pass it through without touching disk."""
    artifact = artifact or load_artifact()
    features = extract_file_features(source)
    speed = features["speed_mps"]

    if is_stationary(speed):
        return {
            "prediction": STATIONARY_LABEL,
            "speed_mps": speed,
            "stationary_rule_applied": True,
            "explanation": STATIONARY_REASON,
            "probabilities": None,
        }

    row = np.array([[features[c] for c in artifact["feature_cols"]]], dtype=np.float64)
    model = artifact["model"]
    proba = model.predict_proba(row)[0]
    order = list(model.classes_)
    probabilities = {cls: float(proba[order.index(cls)]) for cls in config.CLASSES}
    label = max(probabilities, key=probabilities.get)

    return {
        "prediction": label,
        "speed_mps": speed,
        "stationary_rule_applied": False,
        "explanation": (
            f"Classified from axle-box vibration and shock features at "
            f"{speed:.1f} m/s, with {probabilities[label]:.0%} confidence."
        ),
        "probabilities": probabilities,
    }


def predict_rail(source, artifact=None):
    """Minimal contract: raw file in, class label out."""
    return predict_rail_detailed(source, artifact=artifact)["prediction"]


def predict_directory(directory, progress=None):
    """Run every .csv in a directory, returning the exact `rail_predictions.csv` schema:
    `file_id` (source filename including extension) and `prediction`."""
    directory = Path(directory)
    paths = sorted(
        directory.glob("*.csv"),
        key=lambda p: int("".join(ch for ch in p.stem if ch.isdigit()) or 0),
    )
    artifact = load_artifact()
    rows = []
    for i, path in enumerate(paths, start=1):
        rows.append({
            "file_id": path.name,
            "prediction": predict_rail(path, artifact=artifact),
        })
        if progress:
            progress(i, len(paths))
    return pd.DataFrame(rows, columns=["file_id", "prediction"])


def main():
    parser = argparse.ArgumentParser(description="Rail Corrugation inference")
    parser.add_argument("--input", required=True,
                        help="a raw .csv file, or a directory of them")
    parser.add_argument("--output", help="write predictions CSV here")
    args = parser.parse_args()
    source = Path(args.input)

    if source.is_dir():
        df = predict_directory(
            source,
            progress=lambda i, n: print(f"  {i}/{n}", end="\r", flush=True),
        )
        print()
    else:
        df = pd.DataFrame(
            [{"file_id": source.name, "prediction": predict_rail(source)}],
            columns=["file_id", "prediction"],
        )

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output, index=False)
        print(f"Wrote {args.output} ({len(df)} rows)")
    else:
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
