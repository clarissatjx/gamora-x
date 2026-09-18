"""Phase 6 verification: does the inference path agree with the training path?

The classic silent bug here is features being built differently at inference than at
training (reordered columns, a different code path, a dropped transform). This recomputes
features through `predict.py` and compares them against the cached training table.

Run:  python -m subsystems.rail_corrugation.verify_inference
"""
import numpy as np
import pandas as pd

from . import config
from .features import extract_file_features
from .predict import load_artifact, predict_rail_detailed

if __name__ == "__main__":
    artifact = load_artifact()
    cached = pd.read_csv(config.ARTIFACTS_DIR / "train_features.csv").set_index("file_id")
    labels = pd.read_csv(config.TRAIN_LABELS_PATH).set_index("filename")["label"]

    # One moving file per class, plus a stationary one to exercise the rule.
    sample = ["Train3.csv", "Train62.csv", "Train2.csv", "Train5.csv"]

    print("1) Feature parity between inference path and cached training table")
    max_diff_overall = 0.0
    for fname in sample:
        fresh = extract_file_features(config.TRAIN_DIR / fname)
        cols = artifact["feature_cols"]
        a = np.array([fresh[c] for c in cols], dtype=np.float64)
        b = cached.loc[fname, cols].to_numpy(dtype=np.float64)
        max_diff = np.max(np.abs(a - b))
        max_diff_overall = max(max_diff_overall, max_diff)
        print(f"   {fname:14s} max |fresh - cached| = {max_diff:.3e}")
    assert max_diff_overall < 1e-9, "inference features diverge from training features"
    print(f"   OK: all features identical to {max_diff_overall:.1e}")

    print("\n2) End-to-end predictions (NOTE: these files were in training, so this checks"
          "\n   plumbing, not accuracy -- the honest accuracy number is the CV macro F1)")
    for fname in sample:
        result = predict_rail_detailed(config.TRAIN_DIR / fname)
        truth = labels[fname]
        flag = "rule" if result["stationary_rule_applied"] else "model"
        print(f"   {fname:14s} true={truth:8s} pred={result['prediction']:8s} "
              f"[{flag}]  speed={result['speed_mps']:5.2f} m/s")

    print("\n3) Stationary rule fires on a stationary file")
    stationary = predict_rail_detailed(config.TRAIN_DIR / "Train5.csv")
    assert stationary["stationary_rule_applied"], "stationary rule did not fire"
    assert stationary["prediction"] == "Normal"
    assert stationary["probabilities"] is None
    print("   OK:", stationary["explanation"])

    print("\n4) A caller can pass a file object instead of a path")
    with open(config.TRAIN_DIR / "Train62.csv", "rb") as fh:
        via_handle = predict_rail_detailed(fh)
    via_path = predict_rail_detailed(config.TRAIN_DIR / "Train62.csv")
    assert via_handle["prediction"] == via_path["prediction"]
    print(f"   OK: file handle and path both give {via_handle['prediction']!r}")

    print("\nAll inference checks passed.")
