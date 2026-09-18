import pandas as pd

TIME_COL = "Datetime"
CURRENT_COL = "Motor current(mA)"
VOLTAGE_COL = "Motor Voltage(10mV)"
EMF_COL = "Motor electrodynamic force"
POSITION_COL = "Door leaf position"
CLOSING_FLAG_COL = "Door is closing"
OPENING_FLAG_COL = "Door is opening"

REQUIRED_COLUMNS = [
    TIME_COL, CURRENT_COL, VOLTAGE_COL, EMF_COL, POSITION_COL,
    CLOSING_FLAG_COL, OPENING_FLAG_COL,
]


def parse_ts(s: str) -> pd.Timestamp:
    """Parse the dataset's native 'Y-M-D-h-m-s-ms' (not zero-padded) format, or any ISO string."""
    parts = str(s).split("-")
    if len(parts) == 7 and all(p.isdigit() for p in parts):
        y, mo, d, h, mi, sec, ms = (int(p) for p in parts)
        return pd.Timestamp(year=y, month=mo, day=d, hour=h, minute=mi, second=sec,
                            microsecond=ms * 1000)
    return pd.Timestamp(s)


def load_stream(path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        raise ValueError("The file is empty.")
    except UnicodeDecodeError:
        raise ValueError("The file is not a plain-text CSV (is it an Excel file? Export it as .csv first).")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "This doesn't look like a Door data file. Missing columns: " + ", ".join(missing)
        )
    if len(df) == 0:
        raise ValueError("The file has a header but no data rows.")
    bad = [c for c in REQUIRED_COLUMNS if df[c].isna().any()]
    if bad:
        raise ValueError("The file has missing values in: " + ", ".join(bad))
    try:
        df["ts"] = df[TIME_COL].map(parse_ts)
    except (ValueError, TypeError):
        raise ValueError("Some timestamps in the Datetime column could not be read "
                         "(expected Year-Month-Day-Hour-Minute-Second-Millisecond, e.g. 2023-7-5-0-0-3-760).")
    if not df["ts"].is_monotonic_increasing:
        raise ValueError("Timestamps in the file are not in increasing order.")
    return df
