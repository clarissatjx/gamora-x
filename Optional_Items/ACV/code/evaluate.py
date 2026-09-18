"""
ACV subsystem -- Checkpoint A driver.

Run as a module from the repo root:

    python -m subsystems.acv.evaluate

Does three things:
1. EDA report (stdout) over all 6 labelled train files + the 1 unlabelled
   test file: shape, car IDs, column count, NaN patterns, row count, and an
   explicit flag for where the 60+-param file diverges from the ~8-param
   schema the other files share.
2. Builds the per-car feature matrix (``features.extract_features``) once
   per file (cached -- LOO CV re-fits ranking logic per fold but never
   re-extracts features).
3. Leave-one-case-out cross-validation across the 6 labelled cases,
   comparing three ranking approaches:
     - fixed-prior heuristic (no fitting -- domain-reasoned weights as-is)
     - data-tuned heuristic (weights correlation-fit on the 5 training cases)
     - supervised logistic regression (fit on the 5 training cases)
   using the exact rank-decay scoring formula from the ``acv-fault-ranking``
   skill, and recommends which to carry into Checkpoint B.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from subsystems.acv.features import CAR_COL_RE, extract_features, load_case
from subsystems.acv.rank import fit_heuristic_weights, fit_supervised, score_cars, HEURISTIC_WEIGHTS

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "ACV"
TRAIN_DIR = DATA_DIR / "Train"
TEST_DIR = DATA_DIR / "Test"
LABELS_CSV = DATA_DIR / "Train_Labels.csv"

EXPECTED_N_CARS = 8


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def rank_decay_score(true_car: str, ranked_cars: List[str]) -> float:
    """Exact linear rank-decay scoring formula (acv-fault-ranking skill).

    score = (n - (r - 1)) / n, where n = number of cars, r = 1-indexed rank
    of the true faulty car. 0 if the true car is missing from ``ranked_cars``.
    """
    n = len(ranked_cars)
    if n == 0 or true_car not in ranked_cars:
        return 0.0
    r = ranked_cars.index(true_car) + 1
    return (n - (r - 1)) / n


# ---------------------------------------------------------------------------
# EDA
# ---------------------------------------------------------------------------


def _eda_one_file(filepath: Path) -> dict:
    df = pd.read_excel(filepath)
    car_ids, params = set(), set()
    for col in df.columns:
        m = CAR_COL_RE.match(str(col))
        if m:
            car_ids.add(m.group(1))
            params.add(m.group(2).strip())

    nan_frac = df.isna().mean()
    cols_with_nan = nan_frac[nan_frac > 0]

    time_col = pd.to_datetime(df["Time"]) if "Time" in df.columns else None
    info = {
        "file": filepath.name,
        "shape": df.shape,
        "n_cars": len(car_ids),
        "car_ids": sorted(car_ids),
        "n_params_per_car": len(params),
        "n_cols_total": df.shape[1],
        "n_rows": df.shape[0],
        "n_cols_with_nan": int((cols_with_nan > 0).sum()),
        "max_nan_frac": float(cols_with_nan.max()) if len(cols_with_nan) else 0.0,
        "time_range": (time_col.min(), time_col.max()) if time_col is not None else None,
        "median_sample_interval_s": (
            time_col.sort_values().diff().dropna().dt.total_seconds().median() if time_col is not None else None
        ),
    }
    return info


def run_eda() -> None:
    print("=" * 88)
    print("ACV EDA REPORT")
    print("=" * 88)

    train_files = sorted(TRAIN_DIR.glob("acv_case_*.xlsx"))
    test_files = sorted(TEST_DIR.glob("*.xlsx"))

    rows = []
    for f in train_files + test_files:
        info = _eda_one_file(f)
        rows.append(info)
        split = "TRAIN" if f in train_files else "TEST"
        print(f"\n--- [{split}] {info['file']} ---")
        print(f"  shape (rows, cols)        : {info['shape']}")
        print(f"  rows (timestamps)         : {info['n_rows']}")
        print(f"  unique car IDs ({info['n_cars']})       : {info['car_ids']}")
        print(f"  params/car                : {info['n_params_per_car']}")
        print(f"  total columns             : {info['n_cols_total']}")
        print(f"  columns with any NaN      : {info['n_cols_with_nan']} (max NaN frac: {info['max_nan_frac']:.3f})")
        if info["time_range"]:
            print(f"  time range                : {info['time_range'][0]} -> {info['time_range'][1]}")
        if info["median_sample_interval_s"] is not None:
            print(f"  median sample interval    : {info['median_sample_interval_s']:.0f}s")
        if info["n_cars"] != EXPECTED_N_CARS:
            print(f"  ** WARNING: expected {EXPECTED_N_CARS} cars, found {info['n_cars']} **")

    schema_sizes = {r["file"]: r["n_params_per_car"] for r in rows}
    typical = pd.Series(list(schema_sizes.values()))
    mode_size = typical.mode().iloc[0]
    print("\n--- Schema divergence check ---")
    for f, n in schema_sizes.items():
        flag = "  <-- DIVERGES from the ~8-param schema" if n > mode_size * 2 else ""
        print(f"  {f:28s} {n:3d} params/car{flag}")
    print()


# ---------------------------------------------------------------------------
# Feature caching
# ---------------------------------------------------------------------------


def load_all_features(verbose: bool = True) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str], pd.DataFrame]:
    """Load + extract features for all 6 train cases and the 1 test case, once.

    Returns
    -------
    (features_by_case, labels_by_case, test_features)
        features_by_case : {case_filename -> feature_df (index=car_id)}
        labels_by_case    : {case_filename -> faulty car_id}
        test_features     : feature_df for the unlabelled test case
    """
    labels = pd.read_csv(LABELS_CSV, dtype=str).set_index("filename")["faulty_car"].to_dict()

    features_by_case = {}
    for f in sorted(TRAIN_DIR.glob("acv_case_*.xlsx")):
        if verbose:
            print(f"  extracting features: {f.name} ...")
        long_df = load_case(str(f))
        features_by_case[f.name] = extract_features(long_df)

    test_features = None
    test_files = sorted(TEST_DIR.glob("*.xlsx"))
    if test_files:
        if verbose:
            print(f"  extracting features: {test_files[0].name} (test) ...")
        test_features = extract_features(load_case(str(test_files[0])))

    return features_by_case, labels, test_features


# ---------------------------------------------------------------------------
# Leave-one-case-out CV
# ---------------------------------------------------------------------------


def loo_cv_heuristic(
    features_by_case: Dict[str, pd.DataFrame], labels: Dict[str, str], fitted_weights: bool
) -> List[dict]:
    """LOO CV for the heuristic approach.

    ``fitted_weights=False`` uses the fixed prior (HEURISTIC_WEIGHTS) as-is
    on every fold (no use of the training folds beyond membership).
    ``fitted_weights=True`` calls ``fit_heuristic_weights`` on the 5
    training folds each time (a fold-specific, data-tuned weight vector).
    """
    case_names = list(features_by_case.keys())
    results = []
    for held_out in case_names:
        train_names = [c for c in case_names if c != held_out]
        if fitted_weights:
            weights = fit_heuristic_weights(
                [features_by_case[c] for c in train_names],
                [labels[c] for c in train_names],
            )
        else:
            weights = HEURISTIC_WEIGHTS

        ranked, scores = score_cars(features_by_case[held_out], method="heuristic", weights=weights)
        true_car = labels[held_out]
        score = rank_decay_score(true_car, ranked)
        rank = ranked.index(true_car) + 1 if true_car in ranked else None
        results.append({"case": held_out, "true_car": true_car, "ranked": ranked, "rank": rank, "score": score})
    return results


def loo_cv_supervised(features_by_case: Dict[str, pd.DataFrame], labels: Dict[str, str]) -> List[dict]:
    case_names = list(features_by_case.keys())
    results = []
    for held_out in case_names:
        train_names = [c for c in case_names if c != held_out]
        model, scaler = fit_supervised(
            [features_by_case[c] for c in train_names],
            [labels[c] for c in train_names],
        )
        ranked, scores = score_cars(features_by_case[held_out], method="supervised", model=model, scaler=scaler)
        true_car = labels[held_out]
        score = rank_decay_score(true_car, ranked)
        rank = ranked.index(true_car) + 1 if true_car in ranked else None
        results.append({"case": held_out, "true_car": true_car, "ranked": ranked, "rank": rank, "score": score})
    return results


def _print_results(name: str, results: List[dict]) -> float:
    print(f"\n--- {name} ---")
    for r in results:
        print(
            f"  {r['case']:22s} true_car={r['true_car']}  rank={r['rank']!s:>3s}  "
            f"score={r['score']:.3f}  ranked={'|'.join(r['ranked'])}"
        )
    avg = float(np.mean([r["score"] for r in results]))
    print(f"  {'AVERAGE':22s} {'':28s}score={avg:.3f}")
    return avg


def run_loocv() -> None:
    print("=" * 88)
    print("ACV LEAVE-ONE-CASE-OUT CROSS-VALIDATION")
    print("=" * 88)

    print("\nExtracting features for all cases (cached, computed once)...")
    features_by_case, labels, test_features = load_all_features()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        fixed_results = loo_cv_heuristic(features_by_case, labels, fitted_weights=False)
        avg_fixed = _print_results("Heuristic (fixed prior weights)", fixed_results)

        tuned_results = loo_cv_heuristic(features_by_case, labels, fitted_weights=True)
        avg_tuned = _print_results("Heuristic (LOO-fold data-tuned weights)", tuned_results)

        supervised_results = loo_cv_supervised(features_by_case, labels)
        avg_supervised = _print_results("Supervised (logistic regression, category-level features)", supervised_results)

    print("\n" + "=" * 88)
    print("SUMMARY")
    print("=" * 88)
    print(f"  Heuristic (fixed prior)        : {avg_fixed:.3f}")
    print(f"  Heuristic (LOO data-tuned)     : {avg_tuned:.3f}")
    print(f"  Supervised (logistic regr.)    : {avg_supervised:.3f}")

    best_heuristic = max(avg_fixed, avg_tuned)
    best_heuristic_name = "fixed prior" if avg_fixed >= avg_tuned else "LOO data-tuned"

    print(
        f"\n  Best heuristic variant: {best_heuristic_name} ({best_heuristic:.3f}). "
        f"Supervised: {avg_supervised:.3f} ({'+' if avg_supervised >= best_heuristic else ''}"
        f"{avg_supervised - best_heuristic:.3f} vs. best heuristic)."
    )
    if avg_supervised > best_heuristic + 0.05:
        print(
            "  RECOMMENDATION: use the SUPERVISED approach for Checkpoint B -- it beats "
            "the best heuristic by more than the 5% margin needed to trust it at n=6 cases."
        )
    else:
        print(
            "  RECOMMENDATION: use the HEURISTIC approach "
            f"({best_heuristic_name} weights) for Checkpoint B -- the supervised model "
            "does not clearly (>5%) outperform it, and the heuristic is far less likely "
            "to overfit at n=6 training cases."
        )
    print()


def main() -> None:
    run_eda()
    run_loocv()


if __name__ == "__main__":
    main()
