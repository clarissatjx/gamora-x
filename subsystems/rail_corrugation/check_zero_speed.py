"""Investigate the files whose pulse train yields zero rising edges."""
import numpy as np
import pandas as pd

from . import config

if __name__ == "__main__":
    train = pd.read_csv(config.ARTIFACTS_DIR / "train_features.csv")
    zero = train[train["speed_mps"] <= 1e-9]

    print("Label distribution among zero-speed TRAIN files:")
    print(zero["label"].value_counts().to_dict())
    print("\nLabel distribution among non-zero-speed TRAIN files:")
    print(train[train["speed_mps"] > 1e-9]["label"].value_counts().to_dict())

    print("\nRaw pulse-column inspection for 4 zero-speed files:")
    for fname in zero["file_id"].head(4):
        col0 = pd.read_csv(config.TRAIN_DIR / fname, usecols=[0], dtype=np.float32)
        vals = col0.to_numpy().ravel()
        uniq, counts = np.unique(vals, return_counts=True)
        print(f"  {fname:15s} unique={dict(zip(uniq.tolist(), counts.tolist()))}")

    print("\nVibration energy: do zero-speed files actually look stationary?")
    print("  (if the train were truly stopped, vibration RMS should be much lower)")
    for label, grp in [("zero-speed", zero), ("moving", train[train["speed_mps"] > 1e-9])]:
        rms = grp["Side_I_vib_rms_mean"]
        print(f"  {label:12s} Side_I_vib_rms_mean: mean={rms.mean():.4f} "
              f"median={rms.median():.4f} min={rms.min():.4f} max={rms.max():.4f}")
