"""Phase 2: extract per-file features for every Train and Test file, cache to CSV.

Run:  python -m subsystems.rail_corrugation.build_features
"""
import time

import numpy as np
import pandas as pd

from . import config
from .features import extract_file_features


def _numeric_key(filename):
    digits = "".join(ch for ch in filename if ch.isdigit())
    return int(digits) if digits else 0


def build_table(directory, filenames):
    rows = []
    t0 = time.time()
    for i, fname in enumerate(filenames, start=1):
        feats = extract_file_features(directory / fname)
        feats["file_id"] = fname
        rows.append(feats)
        if i % 25 == 0 or i == len(filenames):
            elapsed = time.time() - t0
            print(f"  {i}/{len(filenames)} files  ({elapsed:.1f}s elapsed)", flush=True)
    df = pd.DataFrame(rows)
    cols = ["file_id"] + [c for c in df.columns if c != "file_id"]
    return df[cols]


def report(name, df):
    feature_cols = [c for c in df.columns if c not in ("file_id", "label")]
    values = df[feature_cols].to_numpy(dtype=np.float64)
    n_nan = int(np.isnan(values).sum())
    n_inf = int(np.isinf(values).sum())
    print(f"\n{name}: {len(df)} rows x {len(feature_cols)} features")
    print(f"  NaN values: {n_nan}   inf values: {n_inf}")
    speed = df["speed_mps"]
    print(f"  speed_mps: min={speed.min():.3f} max={speed.max():.3f} "
          f"mean={speed.mean():.3f} median={speed.median():.3f}")
    n_zero_speed = int((speed <= 1e-9).sum())
    print(f"  files with zero/degenerate speed (no pulse transitions): {n_zero_speed}")
    if n_zero_speed:
        print("   ->", df.loc[speed <= 1e-9, "file_id"].tolist())


if __name__ == "__main__":
    config.ARTIFACTS_DIR.mkdir(exist_ok=True)

    labels = pd.read_csv(config.TRAIN_LABELS_PATH)
    train_files = sorted(labels["filename"].tolist(), key=_numeric_key)
    test_files = sorted(
        [p.name for p in config.TEST_DIR.glob("*.csv")], key=_numeric_key
    )

    print(f"Extracting train features ({len(train_files)} files)...")
    train_df = build_table(config.TRAIN_DIR, train_files)
    train_df = train_df.merge(
        labels.rename(columns={"filename": "file_id"}), on="file_id", how="left"
    )
    assert train_df["label"].notna().all(), "some train files failed to join a label"

    print(f"\nExtracting test features ({len(test_files)} files)...")
    test_df = build_table(config.TEST_DIR, test_files)

    train_path = config.ARTIFACTS_DIR / "train_features.csv"
    test_path = config.ARTIFACTS_DIR / "test_features.csv"
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    report("TRAIN", train_df)
    print("  label counts:", train_df["label"].value_counts().to_dict())
    report("TEST", test_df)

    print(f"\nWrote {train_path}")
    print(f"Wrote {test_path}")

    # Does the asymmetry feature separate the classes in the expected direction?
    print("\nSanity check -- mean asym_diff_vib_rms_mean by label "
          "(expect Side I > 0 > Side II if the feature captures the faulty side):")
    print(train_df.groupby("label")["asym_diff_vib_rms_mean"].agg(["mean", "std", "count"]))
