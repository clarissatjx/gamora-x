"""
ACV subsystem -- Checkpoint B batch prediction CLI.

Regenerates ``acv_predictions.csv`` by running one file, or every ``.xlsx``
file in a directory, through the shared ranking pipeline in
``app/inference/acv.py::predict_file`` -- the same function the future
shared Streamlit app will call, so the app and this batch script can never
diverge on ranking logic (see the ``streamlit-inference-app`` skill).

Usage (from repo root, with the repo's `.venv` active):

    python -m subsystems.acv.predict \\
        --input data/ACV/Test/acv_test_case.xlsx \\
        --output predictions/acv_predictions.csv

    # or, for a directory of test files:
    python -m subsystems.acv.predict \\
        --input data/ACV/Test \\
        --output predictions/acv_predictions.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd

from app.inference.acv import DEFAULT_METHOD, predict_file


def _collect_input_files(input_path: Path) -> List[Path]:
    if input_path.is_dir():
        files = sorted(input_path.glob("*.xlsx"))
        if not files:
            raise FileNotFoundError(f"no .xlsx files found in directory: {input_path}")
        return files
    if not input_path.exists():
        raise FileNotFoundError(f"input path does not exist: {input_path}")
    return [input_path]


def run(input_path: str, output_path: str, method: str = DEFAULT_METHOD) -> pd.DataFrame:
    files = _collect_input_files(Path(input_path))

    rows = []
    for f in files:
        print(f"  ranking: {f.name} ({method}) ...")
        rows.append(predict_file(str(f), method=method))

    result = pd.concat(rows, ignore_index=True)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)
    print(f"wrote {len(result)} row(s) -> {out}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate acv_predictions.csv from raw ACV case file(s).")
    parser.add_argument("--input", required=True, help="path to one .xlsx case file, or a directory of .xlsx files")
    parser.add_argument("--output", required=True, help="path to write acv_predictions.csv")
    parser.add_argument("--method", default=DEFAULT_METHOD,
                        choices=["heuristic", "physics", "blend"], help=f"ranker (default: {DEFAULT_METHOD})")
    args = parser.parse_args()
    run(args.input, args.output, method=args.method)


if __name__ == "__main__":
    main()
