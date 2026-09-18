import argparse
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .loader import load_series
from .model import cycle_features, miner_sum
from .rainflow import cycles

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
OUTPUT_COLUMNS = ["file_id", "prediction"]


def load_model(path=MODEL_PATH):
    return joblib.load(path)


def analyse(x: np.ndarray, bundle=None) -> dict:
    """Full breakdown for one stress series: cycles, analytic Miner term, correction, damage."""
    bundle = bundle or load_model()
    rng, mean, cnt = cycles(x)
    feats = cycle_features(rng, mean, cnt)
    s5 = miner_sum(rng, cnt, bundle["m"])
    analytic = s5 / bundle["C"]
    log_corr = 0.0
    if bundle["use_correction"]:
        X = np.array([[feats[f] for f in bundle["features"]]])
        log_corr = float(np.clip(bundle["ridge"].predict(X)[0], -bundle["clip"], bundle["clip"]))
    damage = analytic * float(np.exp(log_corr))
    contrib = cnt * rng ** bundle["m"]
    return {
        "damage": damage, "analytic": analytic, "correction_factor": float(np.exp(log_corr)),
        "n_cycles": float(cnt.sum()), "n_reversals": int(len(rng) + 1), "max_range": float(rng.max()),
        "rng": rng, "cnt": cnt, "contrib_share": contrib / contrib.sum(), "features": feats,
    }


def predict(path, bundle=None) -> float:
    return analyse(load_series(path), bundle)["damage"]


def _natural_key(p: Path):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p.name)]


def predict_many(paths, bundle=None) -> pd.DataFrame:
    bundle = bundle or load_model()
    rows = [{"file_id": Path(p).name, "prediction": predict(p, bundle)} for p in paths]
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main():
    ap = argparse.ArgumentParser(description="SHM: cumulative fatigue damage per stress file.")
    ap.add_argument("--input", required=True, help="a .csv file or a directory of them")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    inp = Path(args.input)
    paths = sorted(inp.glob("*.csv"), key=_natural_key) if inp.is_dir() else [inp]
    out = predict_many(paths)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"wrote {len(out)} rows -> {args.output}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
