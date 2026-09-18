"""Validate every *_predictions.csv in predictions/ against the PS3 spec, then optionally zip.

A file that fails is disqualified for that subsystem, so every rule here is a scoring rule:
exact column names, exact label strings, one row per held-out file (or per segment for Door),
and ACV car IDs exactly as they appear in the test workbook's headers.

    python scripts/validate_submission.py          # report only
    python scripts/validate_submission.py --zip    # also write predictions/predictions.zip
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRED = ROOT / "predictions"
DATA = ROOT / "data"

RAIL_LABELS = {"Normal", "Side I", "Side II"}
DOOR_LABELS = {"Normal", "Abnormal resistance"}


def _test_files(folder: str, pattern: str = "*.csv"):
    d = DATA / folder
    return sorted(p.name for p in d.glob(pattern)) if d.exists() else None


def _parse_ts(s: str) -> pd.Timestamp:
    parts = str(s).split("-")
    if len(parts) == 7 and all(p.isdigit() for p in parts):
        y, mo, d, h, mi, sec, ms = (int(p) for p in parts)
        return pd.Timestamp(year=y, month=mo, day=d, hour=h, minute=mi, second=sec, microsecond=ms * 1000)
    return pd.Timestamp(s)


def check_columns(df, required, name, extra_ok=()):
    problems = []
    missing = [c for c in required if c not in df.columns]
    if missing:
        problems.append(f"missing columns {missing} (have {list(df.columns)})")
    unexpected = [c for c in df.columns if c not in required and c not in extra_ok]
    if unexpected:
        problems.append(f"unexpected columns {unexpected}")
    if df.isna().any().any():
        problems.append(f"{int(df.isna().sum().sum())} empty cells")
    return problems


def check_file_ids(df, expected, name):
    problems = []
    if expected is None:
        return [f"(cannot verify file_id coverage: data/ folder for {name} not present)"]
    ids = df.file_id.astype(str)
    dup = ids[ids.duplicated()].tolist()
    if dup:
        problems.append(f"duplicate file_id: {dup[:5]}")
    missing = sorted(set(expected) - set(ids))
    extra = sorted(set(ids) - set(expected))
    if missing:
        problems.append(f"{len(missing)} test files have no row, e.g. {missing[:4]}")
    if extra:
        problems.append(f"{len(extra)} file_ids are not test files, e.g. {extra[:4]} "
                        f"(must include the extension, exactly as named)")
    return problems


def validate_door(df):
    p = check_columns(df, ["start_time", "end_time", "prediction"], "Door", extra_ok=("confidence",))
    if "file_id" in df.columns:
        p.append("Door must NOT have a file_id column")
    if p:
        return p
    bad = sorted(set(df.prediction) - DOOR_LABELS)
    if bad:
        p.append(f"labels not in {sorted(DOOR_LABELS)}: {bad}")
    try:
        s = df.start_time.map(_parse_ts)
        e = df.end_time.map(_parse_ts)
    except Exception as ex:  # noqa: BLE001
        return p + [f"timestamps not parseable: {ex}"]
    if (e <= s).any():
        p.append(f"{int((e <= s).sum())} rows have end_time <= start_time")
    order = s.sort_values()
    if (order.index != df.index).any():
        p.append("segments are not in time order (allowed, but check it's intentional)")
    overlaps = int((s.iloc[1:].to_numpy() < e.iloc[:-1].to_numpy()).sum()) if len(df) > 1 else 0
    if overlaps:
        p.append(f"{overlaps} predicted segments overlap the previous one")
    return p


def validate_acv(df):
    p = check_columns(df, ["file_id", "ranked_cars"], "ACV")
    if "prediction" in df.columns:
        p.append("ACV must NOT have a prediction column (ranked_cars instead)")
    if p:
        return p
    p += check_file_ids(df, _test_files("ACV/Test", "*.xlsx"), "ACV")
    for _, r in df.iterrows():
        try:
            cols = pd.read_excel(DATA / "ACV/Test" / r.file_id, nrows=0).columns
            expected = {m.group(1) for c in cols for m in [re.match(r"\s*Car\s+(\d+)\s*-", str(c))] if m}
        except Exception as ex:  # noqa: BLE001
            p.append(f"{r.file_id}: could not read workbook headers to verify car IDs ({ex})")
            continue
        cars = str(r.ranked_cars).split("|")
        if len(cars) != len(set(cars)):
            p.append(f"{r.file_id}: duplicate car in ranked_cars")
        if set(cars) != expected:
            p.append(f"{r.file_id}: ranked_cars {cars} must be exactly the header IDs {sorted(expected)} "
                     f"(two-digit, e.g. '03', pipe-separated, every car once)")
        if " " in str(r.ranked_cars):
            p.append(f"{r.file_id}: ranked_cars contains spaces")
    return p


def validate_rail(df):
    p = check_columns(df, ["file_id", "prediction"], "Rail")
    if p:
        return p
    p += check_file_ids(df, _test_files("Rail_Corrugation/Test"), "Rail")
    bad = sorted(set(df.prediction.astype(str)) - RAIL_LABELS)
    if bad:
        p.append(f"labels not in {sorted(RAIL_LABELS)} (exact spelling and case): {bad}")
    counts = df.prediction.value_counts().to_dict()
    p.append(f"info: class mix {counts} (train prior ~86% Normal / 5% Side I / 9% Side II)")
    return p


def validate_shm(df):
    p = check_columns(df, ["file_id", "prediction"], "SHM")
    if p:
        return p
    p += check_file_ids(df, _test_files("SHM/Test"), "SHM")
    vals = pd.to_numeric(df.prediction, errors="coerce")
    if vals.isna().any():
        p.append("prediction has non-numeric values")
    elif (vals <= 0).any():
        p.append(f"{int((vals <= 0).sum())} predictions are <= 0 (damage must be positive)")
    else:
        p.append(f"info: damage range {vals.min():.4f}-{vals.max():.4f} (train labels 0.029-0.928)")
    return p


CHECKS = {
    "door_predictions.csv": validate_door,
    "acv_predictions.csv": validate_acv,
    "rail_predictions.csv": validate_rail,
    "shm_predictions.csv": validate_shm,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", action="store_true", help="write predictions/predictions.zip from the valid files")
    args = ap.parse_args()

    present, failed = [], []
    for fname, fn in CHECKS.items():
        path = PRED / fname
        if not path.exists():
            print(f"--  {fname}: not present (subsystem will simply not be scored)")
            continue
        try:
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
            df = df.replace("", pd.NA)
        except Exception as ex:  # noqa: BLE001
            print(f"XX  {fname}: cannot be read as CSV ({ex})")
            failed.append(fname)
            continue
        problems = fn(df)
        errors = [x for x in problems if not x.startswith("info:") and not x.startswith("(")]
        notes = [x for x in problems if x.startswith("info:") or x.startswith("(")]
        status = "XX" if errors else "OK"
        print(f"{status}  {fname}: {len(df)} rows")
        for e in errors:
            print(f"      ERROR  {e}")
        for n in notes:
            print(f"      {n}")
        (failed if errors else present).append(fname)

    print()
    if failed:
        print(f"FAILED: {failed} — fix these before zipping; a malformed file scores 0 for that subsystem.")
        sys.exit(1)
    if not present:
        print("no prediction files found in predictions/")
        sys.exit(1)
    print(f"valid: {present}")

    if args.zip:
        out = PRED / "predictions.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for fname in present:
                z.write(PRED / fname, arcname=fname)   # flat: no folders inside the zip
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
        assert all("/" not in n for n in names), names
        print(f"wrote {out.relative_to(ROOT)} containing {names}")


if __name__ == "__main__":
    main()
