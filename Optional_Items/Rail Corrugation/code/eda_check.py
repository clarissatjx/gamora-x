"""Quick sanity check: extract features for a handful of files, check timing, and
spot-check that speed/feature values look plausible before running the full corpus."""
import time

import pandas as pd

from . import config
from .features import extract_file_features

if __name__ == "__main__":
    labels = pd.read_csv(config.TRAIN_LABELS_PATH)
    sample = pd.concat([
        labels[labels["label"] == "Normal"].head(2),
        labels[labels["label"] == "Side I"].head(2),
        labels[labels["label"] == "Side II"].head(2),
    ])

    for _, row in sample.iterrows():
        path = config.TRAIN_DIR / row["filename"]
        t0 = time.time()
        feats = extract_file_features(path)
        dt = time.time() - t0
        print(f"{row['filename']:15s} label={row['label']:8s} "
              f"speed={feats['speed_mps']:.3f} m/s  "
              f"SideI_vib_rms_mean={feats['Side_I_vib_rms_mean']:.4f}  "
              f"SideII_vib_rms_mean={feats['Side_II_vib_rms_mean']:.4f}  "
              f"n_features={len(feats)}  time={dt:.2f}s")
