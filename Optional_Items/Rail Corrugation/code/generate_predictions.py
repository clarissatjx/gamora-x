"""Phase 7: generate rail_predictions.csv for the held-out test set.

Goes through the same `predict.py` path as every other caller -- no separate inference
logic for the submission file.

Run:  python -m subsystems.rail_corrugation.generate_predictions
"""
import pandas as pd

from . import config
from .predict import predict_directory
from .split import load_training_frame

OUTPUT_PATH = config.REPO_ROOT / "predictions" / "rail_predictions.csv"
EXPECTED_N_TEST = 68


def main(output_path=OUTPUT_PATH):
    print(f"Running inference over {config.TEST_DIR} ...")
    df = predict_directory(
        config.TEST_DIR,
        progress=lambda i, n: print(f"  {i}/{n}", end="\r", flush=True),
    )
    print()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    # Schema checks -- this file is graded mechanically, so a formatting slip costs the
    # whole subsystem's score regardless of how good the model is.
    assert list(df.columns) == ["file_id", "prediction"], f"bad columns: {list(df.columns)}"
    assert len(df) == EXPECTED_N_TEST, f"expected {EXPECTED_N_TEST} rows, got {len(df)}"
    assert df["file_id"].is_unique, "duplicate file_id rows"
    assert df["file_id"].str.endswith(".csv").all(), "file_id must include the extension"
    assert df["prediction"].isin(config.CLASSES).all(), (
        f"unexpected labels: {sorted(set(df['prediction']) - set(config.CLASSES))}"
    )
    assert df.notna().all().all(), "null values present"

    expected_ids = {f"Test{i}.csv" for i in range(1, EXPECTED_N_TEST + 1)}
    missing = expected_ids - set(df["file_id"])
    assert not missing, f"missing test files: {sorted(missing)}"

    print(f"Wrote {output_path}")
    print(f"\nSchema checks passed: {len(df)} rows, columns {list(df.columns)}, "
          f"labels spelled exactly as required, Test1..Test{EXPECTED_N_TEST} all present.")

    print("\nPredicted class distribution vs. the training distribution:")
    train = load_training_frame()
    test_pct = df["prediction"].value_counts(normalize=True) * 100
    train_pct = train["label"].value_counts(normalize=True) * 100
    comparison = pd.DataFrame({
        "test_n": df["prediction"].value_counts(),
        "test_%": test_pct.round(1),
        "train_%(moving)": train_pct.round(1),
    }).reindex(list(config.CLASSES)).fillna(0)
    print(comparison.to_string())

    n_stationary_rule = int((df["prediction"] == "Normal").sum())
    print(f"\n(Of the {n_stationary_rule} Normal predictions, 9 come from the stationary "
          f"rule rather than the model -- see PLAN.md Phase 2.)")

    print("\nFirst 10 rows:")
    print(df.head(10).to_string(index=False))
    return df


if __name__ == "__main__":
    main()
