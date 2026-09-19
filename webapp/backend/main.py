"""FastAPI backend for the React frontend prototype.

Wraps the same subsystem `predict`/`analyse` functions the Streamlit app (`app/`) calls, plus
`app/reliability.py` for the plain-language verdict/severity/reliability data — nothing about
the models changes, this is a second presentation layer. Rail is the only subsystem wired up
so far (Phase 0 prototype); Door/ACV/SHM follow the same shape once this is validated.

Run from the repo root: `uvicorn webapp.backend.main:app --reload --port 8000`
"""
import gzip
import io
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import pandas as pd

import reliability as rel  # noqa: E402
from inference.acv import DEFAULT_METHOD  # noqa: E402 - streamlit-free per app/CLAUDE.md
from subsystems.acv.features import extract_features, load_case  # noqa: E402
from subsystems.acv.rank import COOLING_MODES, MODE_PARAM, TEMP_PAIRS, heuristic_scores, physics_gap, score_cars  # noqa: E402
from subsystems.door.loader import CURRENT_COL, POSITION_COL, load_stream  # noqa: E402
from subsystems.door.predict import load_model as load_door_model, run as run_door, to_output  # noqa: E402
from subsystems.rail_corrugation import config  # noqa: E402
from subsystems.rail_corrugation.features import _channel_column_indices, load_raw_file  # noqa: E402
from subsystems.rail_corrugation.predict import load_artifact, predict_rail_detailed  # noqa: E402
from subsystems.shm.loader import load_series  # noqa: E402
from subsystems.shm.predict import analyse as analyse_shm, load_model as load_shm_model  # noqa: E402

SAMPLES_DIR = ROOT / "app" / "samples"

# Notes are the one thing in this app meant to be seen across browsers — one engineer leaves a
# note on a run, another looks at the same file later and sees it. SQLite on local disk is fine
# for a single always-on instance; it will NOT survive a Cloud Run cold restart or be shared
# across replicas if this service is ever scaled beyond one instance — swap for a real DB then.
NOTES_DB = ROOT / "webapp" / "backend" / "notes.db"

app = FastAPI(title="gamora-x API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _notes_conn():
    conn = sqlite3.connect(NOTES_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "subsystem TEXT NOT NULL, "
        "file_id TEXT NOT NULL, "
        "author TEXT NOT NULL, "
        "text TEXT NOT NULL, "
        "created_at TEXT NOT NULL)"
    )
    return conn


class NoteIn(BaseModel):
    subsystem: str
    file_id: str
    author: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=2000)


_artifact = None


def get_artifact():
    global _artifact
    if _artifact is None:
        _artifact = load_artifact()
    return _artifact


def channel_rms(arr: np.ndarray) -> list[dict]:
    rows = []
    for side, positions in (("Side I", config.SIDE_I_POSITIONS), ("Side II", config.SIDE_II_POSITIONS)):
        vib, _ = _channel_column_indices(positions)
        for col in vib:
            k = (col - 1) // 2
            car, pos = k // config.N_POSITIONS + 1, k % config.N_POSITIONS + 1
            x = arr[:, col].astype(float)
            rows.append({"channel": f"C{car}P{pos}", "order": k, "side": side, "rms": float((x - x.mean()).std())})
    return sorted(rows, key=lambda r: r["order"])


def build_rail_result(data: bytes, file_id: str) -> dict:
    try:
        res = predict_rail_detailed(io.BytesIO(data), artifact=get_artifact())
        arr = load_raw_file(io.BytesIO(data))
    except ValueError as e:
        # Same defence as subsystems/rail_corrugation/features.py::load_raw_file: a malformed
        # or wrong-subsystem file is rejected with a clear reason, never silently scored.
        raise HTTPException(422, str(e)) from e

    ch = channel_rms(arr)
    side_i = float(np.mean([c["rms"] for c in ch if c["side"] == "Side I"]))
    side_ii = float(np.mean([c["rms"] for c in ch if c["side"] == "Side II"]))
    asym = side_i - side_ii

    pred = res["prediction"]
    stationary = bool(res["stationary_rule_applied"])
    confidence_val = 0.0 if stationary else float(res["probabilities"][pred])
    tier = rel.rail_severity(pred, confidence_val, stationary)
    asym_ctx = rel.rail_asym_context(asym, pred if not stationary else None)

    if stationary:
        headline = "Inconclusive — train was stationary"
        reasoning = (
            "This recording cannot confirm or rule out corrugation: a stopped train produces no "
            "wheel-rail excitation either way. The submitted prediction defaults to Normal because "
            "every stationary recording in the labelled data happened to be healthy, not because "
            "this one was checked."
        )
    elif pred == "Normal":
        headline = "No corrugation detected"
        reasoning = (
            f"Vibration and shock across all 64 axle-box channels matched the healthy pattern at "
            f"{res['speed_mps'] * 3.6:.0f} km/h, with {res['probabilities'][pred]:.0%} model confidence. "
            + rel.RAIL_NORMAL_CAVEAT
        )
    else:
        headline = f"{pred} corrugation detected"
        reasoning = (
            f"The {pred} rail's axle boxes show a vibration signature the model separates from "
            f"the healthy pattern, {res['probabilities'][pred]:.0%} confidence. Side asymmetry "
            f"is {asym:+.3f} — {asym_ctx['detail']}"
        )

    return {
        "file_id": file_id,
        "prediction": "Inconclusive" if stationary else pred,
        "csv_prediction": pred,  # what actually gets submitted — never "Inconclusive"
        "stationary": stationary,
        "probabilities": res["probabilities"],
        "speed_kmh": res["speed_mps"] * 3.6,
        # Stationary recordings already lead with "Inconclusive", so the low-speed caveat
        # would just repeat the verdict back at them.
        "speed_context": (rel.rail_speed_context(res["speed_mps"] * 3.6) if not stationary
                          else {**rel.rail_speed_context(0.0), "caveat": None}),
        "asym": asym,
        "asym_context": asym_ctx,
        "asym_bands": list(rel.RAIL_ASYM_BANDS),
        "asym_axis": list(rel.RAIL_ASYM_AXIS),
        "channels": ch,
        "explanation": res["explanation"],
        "tier": tier,
        "tier_label": rel.TIER_LABEL[tier],
        "confidence_label": "Unmeasurable" if stationary else rel.confidence_label(confidence_val),
        "confidence_value": confidence_val,
        "headline": headline,
        "reasoning": reasoning,
        "reliability": {
            "note": rel.RAIL_RELIABILITY_NOTE,
            # The sentence that actually matters for THIS verdict — the generic one cannot
            # say that a Side I call and a Side II call are very different propositions.
            "class_line": None if stationary else rel.rail_class_line(pred),
            "normal_caveat": rel.RAIL_NORMAL_CAVEAT if (pred == "Normal" and not stationary) else None,
            "classes": [
                {"label": c, "recall": rel.RAIL_RELIABILITY[c]["recall"], "precision": rel.RAIL_RELIABILITY[c]["precision"]}
                for c in ("Side I", "Side II", "Normal")
            ],
        },
        "official_score": "0.888",
        "cv_score": "0.81",
    }


@app.get("/api/rail/meta")
def rail_meta():
    return {
        "title": "Rail Corrugation — 3-class classification",
        "subtitle": "One-second axle-box recording classified Normal, Side I or Side II from "
                    "64 vibration and shock channels.",
        "official_score": "0.888",
        "cv_score": "0.81",
    }


@app.post("/api/rail/predict")
async def rail_predict(file: UploadFile = File(...)):
    data = await file.read()
    return build_rail_result(data, file.filename)


@app.get("/api/rail/sample")
def rail_sample():
    """Same bundled sample the Streamlit app offers, so both frontends show one result."""
    path = SAMPLES_DIR / "Test33.csv.gz"
    data = gzip.decompress(path.read_bytes())
    return build_rail_result(data, "Test33.csv")


# ---------------------------------------------------------------------------------- Door ----

ABNORMAL = "Abnormal resistance"
DOOR_SAMPLE_SECONDS = 0.02
_door_model = None


def get_door_model():
    global _door_model
    if _door_model is None:
        _door_model = load_door_model()
    return _door_model


def door_cycle_evidence(i: int, out: pd.DataFrame, feats: pd.DataFrame) -> dict:
    """The "why is this cycle flagged" feature/baseline breakdown for cycle i (0-based) against
    the healthy peers of the same operation in this file — computable for any cycle, not just
    the most-confidently-flagged one."""
    op = feats.op.iloc[i]
    peers = feats[(feats.op == op) & (out.prediction == "Normal").to_numpy()]
    if peers.empty:
        peers = feats[feats.op == op]
    excess = float(feats.cur_mid.iloc[i] / max(peers.cur_mid.median(), 1e-9) - 1)
    return {
        "excess": excess,
        "confidence": float(out.confidence.iloc[i]),
        "tiles": [
            {"label": "Mid-travel current", "value": f"{feats.cur_mid.iloc[i]:.0f} mA",
             "note": f"baseline {peers.cur_mid.median():.0f} mA"},
            {"label": "Cycle duration", "value": f"{feats.n_rows.iloc[i] * DOOR_SAMPLE_SECONDS:.2f} s",
             "note": f"baseline {peers.n_rows.median() * DOOR_SAMPLE_SECONDS:.2f} s"},
            {"label": "Back-EMF, mid-travel", "value": f"{feats.emf_mid.iloc[i]:.0f}",
             "note": f"baseline {peers.emf_mid.median():.0f}"},
        ],
        "prose": (
            f"Mid-travel motor current on cycle {i + 1} sits {excess:.0%} above the healthy "
            "cycles of the same operation in this recording, while back-EMF falls — the motor "
            "is pushing harder and turning slower. Both point to added mechanical resistance "
            "rather than a control fault."
        ),
    }


def door_worst_cycle(out: pd.DataFrame, feats: pd.DataFrame):
    """Mirrors app/inference/door.py::_worst_cycle — the most confidently flagged cycle, which
    drives the headline/reasoning sentence and the evidence panel's default selection."""
    if not (out.prediction == ABNORMAL).any():
        return None
    abn = out.index[out.prediction == ABNORMAL]
    i = int(out.loc[abn, "confidence"].idxmax())
    return {"i": i, **door_cycle_evidence(i, out, feats)}


def build_door_result(data: bytes, file_id: str) -> dict:
    try:
        df = load_stream(io.BytesIO(data))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    segs, feats, p_abnormal, _ = run_door(df, get_door_model())
    out = to_output(segs, p_abnormal)
    n_abn = int((out.prediction == ABNORMAL).sum())
    worst = door_worst_cycle(out, feats)

    if n_abn == 0:
        tier, conf_label = "ok", "High"
        headline = "All cycles normal"
        reasoning = ("No cycle in this recording drew more current or less back-EMF than the "
                     "healthy range for its operation.")
    else:
        tier = rel.door_severity(ABNORMAL, worst["excess"], worst["confidence"]) if worst else "inspect"
        conf_label = rel.confidence_label(worst["confidence"]) if worst else "Medium"
        headline = f"{n_abn} of {len(out)} cycle{'s' if len(out) != 1 else ''} show abnormal resistance"
        reasoning = (
            f"The clearest case is cycle {worst['i'] + 1}, drawing {worst['excess']:.0%} more "
            "current than a healthy cycle of the same operation while turning slower — "
            "consistent with added mechanical resistance."
        ) if worst else "Cycles were flagged abnormal; not enough peer data to quantify the excess."

    # Every abnormal cycle gets its own "why was this flagged" breakdown, not just the
    # single most-confident one — an engineer should be able to check any of them.
    evidence_by_cycle = {
        int(i) + 1: door_cycle_evidence(int(i), out, feats)
        for i in out.index[out.prediction == ABNORMAL]
    }

    lengths = (segs.i1 - segs.i0 + 1) * DOOR_SAMPLE_SECONDS
    step = max(1, len(df) // 3000)
    current = df[CURRENT_COL].to_numpy()[::step]
    position = df[POSITION_COL].to_numpy()[::step]
    trace = [{"i": int(k), "current": float(c), "position": float(p)}
             for k, (c, p) in enumerate(zip(current, position))]
    bands = [{"x0": int(r.i0 // step), "x1": int(r.i1 // step), "n": k + 1,
              "status": o.prediction, "start_time": o.start_time, "end_time": o.end_time,
              "confidence": float(o.confidence)}
             for k, (r, o) in enumerate(zip(segs.itertuples(), out.itertuples(index=False)))]

    cycles = [{"n": k + 1, "start_time": r.start_time, "end_time": r.end_time,
               "prediction": r.prediction, "confidence": float(r.confidence)}
              for k, r in enumerate(out.itertuples(index=False))]

    return {
        "file_id": file_id,
        "n_rows": len(df),
        "duration_s": len(df) * DOOR_SAMPLE_SECONDS,
        "n_cycles": len(out),
        "n_abnormal": n_abn,
        "mean_cycle_length": float(lengths.mean()),
        "mean_confidence": float(out.confidence.mean()),
        "min_confidence": float(out.confidence.min()),
        "tier": tier, "tier_label": rel.TIER_LABEL[tier], "confidence_label": conf_label,
        "headline": headline, "reasoning": reasoning,
        "reliability_note": rel.DOOR_RELIABILITY_NOTE,
        "cycles": cycles,
        "chart": {"trace": trace, "bands": bands},
        "evidence_by_cycle": evidence_by_cycle,
        "worst_cycle": (worst["i"] + 1) if worst else None,
        "official_score": "1.000",
    }


@app.get("/api/door/meta")
def door_meta():
    return {
        "title": "Door — cycle detection & classification",
        "subtitle": "Continuous stream segmented into door open/close cycles, each classified "
                    "Normal or Abnormal resistance.",
        "official_score": "1.000",
    }


@app.post("/api/door/predict")
async def door_predict(file: UploadFile = File(...)):
    data = await file.read()
    return build_door_result(data, file.filename)


@app.get("/api/door/sample")
def door_sample():
    path = SAMPLES_DIR / "Test.csv"
    return build_door_result(path.read_bytes(), "Test.csv")


# ----------------------------------------------------------------------------------- ACV -----

ACV_SMOOTH = 20  # samples (~10 min at 30 s)
ACV_CHART_POINTS = 300


def acv_gap_series(case_df: pd.DataFrame):
    """Mirrors app/inference/acv_page.py::_gap_series."""
    params = set(case_df["param"].unique())
    pair = next((p for p in TEMP_PAIRS if set(p) <= params), None)
    if pair is None:
        return None

    def wide(p):
        w = case_df[case_df["param"] == p].pivot(index="Time", columns="car_id", values="value")
        return w.apply(pd.to_numeric, errors="coerce")

    gap = wide(pair[0]) - wide(pair[1])
    if MODE_PARAM in params:
        mode = case_df[case_df["param"] == MODE_PARAM].pivot(index="Time", columns="car_id", values="value")
        cool = mode.astype(str).isin(COOLING_MODES).reindex(index=gap.index, columns=gap.columns).fillna(False)
        if cool.to_numpy().any():
            gap = gap.where(cool)
    return gap


def build_acv_result(data: bytes, file_id: str) -> dict:
    try:
        case_df = load_case(io.BytesIO(data))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    feats = extract_features(case_df)
    gap = physics_gap(case_df)
    ranked, scores = score_cars(feats, method=DEFAULT_METHOD, gap=gap)
    series = acv_gap_series(case_df)

    top, runner = ranked[0], ranked[1]
    margin = float(scores.iloc[0] - scores.iloc[1])
    gap_top = float(gap.get(top, float("nan")))
    has_gap = gap_top == gap_top  # not NaN

    tier = rel.acv_severity(gap_top if has_gap else float("nan"), margin)
    conf = "Low" if margin < 0.3 else ("Medium" if margin < 1.0 else "High")

    reasoning = (
        f"Car {top} runs {gap_top:+.2f} °C above its cooling setpoint while other cars stay "
        f"near zero — the signature of lost refrigerant charge — and scores {margin:.2f} clear "
        f"of car {runner}, the next candidate."
    ) if has_gap else (
        f"No cabin-temperature reading was available for car {top} in this file; the ranking "
        f"falls back to a peer-deviation score across the other telemetry, {margin:.2f} clear "
        f"of car {runner}."
    )

    chart = None
    if series is not None:
        sm = series.rolling(ACV_SMOOTH, min_periods=1).mean()
        step = max(1, len(sm) // ACV_CHART_POINTS)
        sm = sm.iloc[::step]
        points = []
        for i, (_, row) in enumerate(sm.iterrows()):
            others = row.drop(labels=[top], errors="ignore").dropna()
            points.append({
                "i": i,
                "top": None if pd.isna(row.get(top)) else float(row[top]),
                "others_min": None if others.empty else float(others.min()),
                "others_max": None if others.empty else float(others.max()),
            })
        chart = {"top_car": top, "points": points}

    rows = [{"rank": i, "car": car, "score": float(s)} for i, (car, s) in enumerate(scores.items(), start=1)]

    return {
        "file_id": file_id,
        "ranked_cars": ranked,
        "top": top, "runner_up": runner, "margin": margin,
        "gap_top": gap_top if has_gap else None,
        "n_cars": len(ranked),
        "hours": (case_df["Time"].max() - case_df["Time"].min()).total_seconds() / 3600,
        "tier": tier, "tier_label": rel.TIER_LABEL[tier], "confidence_label": conf,
        "headline": f"Car {top} most likely faulty", "reasoning": reasoning,
        "reliability_note": rel.ACV_RELIABILITY_NOTE,
        "scores": rows,
        "chart": chart,
        "official_score": "1.000",
    }


@app.get("/api/acv/meta")
def acv_meta():
    return {
        "title": "ACV — refrigerant leak localisation",
        "subtitle": "Every car in the uploaded file ranked from most to least likely to carry "
                    "the refrigerant leak.",
        "official_score": "1.000",
    }


@app.post("/api/acv/predict")
async def acv_predict(file: UploadFile = File(...)):
    data = await file.read()
    return build_acv_result(data, file.filename)


@app.get("/api/acv/sample")
def acv_sample():
    path = SAMPLES_DIR / "acv_test_case.xlsx"
    return build_acv_result(path.read_bytes(), "acv_test_case.xlsx")


# ----------------------------------------------------------------------------------- SHM -----

SHM_N_HIST_BINS = 10
SHM_SHARE_HIGHLIGHT = 0.15
_shm_bundle = None


def get_shm_bundle():
    global _shm_bundle
    if _shm_bundle is None:
        _shm_bundle = load_shm_model()
    return _shm_bundle


def shm_top_excursions(x: np.ndarray, k: int = 8, min_gap_frac: float = 0.02) -> np.ndarray:
    """Mirrors app/inference/shm.py::_top_excursions."""
    d = np.diff(x)
    turning = np.nonzero(np.sign(d[1:]) != np.sign(d[:-1]))[0] + 1
    order = turning[np.argsort(np.abs(x[turning] - x.mean()))[::-1]]
    chosen, gap = [], int(len(x) * min_gap_frac)
    for i in order:
        if all(abs(i - j) >= gap for j in chosen):
            chosen.append(int(i))
        if len(chosen) == k:
            break
    return np.array(chosen)


def shm_histogram(res: dict) -> list[dict]:
    """Mirrors app/inference/shm.py::histogram's binning (chart itself omitted)."""
    rng, cnt, share = res["rng"], res["cnt"], res["contrib_share"]
    edges = np.linspace(0, rng.max() * 1.0001, SHM_N_HIST_BINS + 1)
    which = np.clip(np.digitize(rng, edges) - 1, 0, SHM_N_HIST_BINS - 1)
    rows = []
    for b in range(SHM_N_HIST_BINS):
        m = which == b
        share_b = float(share[m].sum())
        rows.append({"bin": f"{edges[b]:.0f}–{edges[b + 1]:.0f}", "cycles": float(cnt[m].sum()),
                     "share": share_b, "hot": share_b >= SHM_SHARE_HIGHLIGHT})
    return rows


def build_shm_result(data: bytes, file_id: str) -> dict:
    try:
        x = load_series(io.BytesIO(data))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e

    b = get_shm_bundle()
    res = analyse_shm(x, b)
    damage = res["damage"]

    peak_abs = float(np.abs(x).max())
    implausible = peak_abs > rel.SHM_PLAUSIBLE_ABS_MAX or float(x.std()) < 1e-6

    tier = rel.shm_severity(damage)
    lo, hi = damage * (1 - rel.SHM_WORST_MAPE), damage * (1 + rel.SHM_WORST_MAPE)
    reasoning = (
        f"Likely between {lo:.3f} and {hi:.3f} once model error is accounted for (typically "
        f"±{rel.SHM_TYPICAL_MAPE:.0%}, worst case observed ±{rel.SHM_WORST_MAPE:.0%}). "
        "1.0 means the fatigue life at this point is fully used up."
    )

    step = max(1, len(x) // 4000)
    peaks_idx = shm_top_excursions(x)
    trace = [{"i": int(i), "stress": float(v)} for i, v in zip(range(0, len(x), step), x[::step])]
    peaks = [{"i": int(i), "stress": float(x[i])} for i in peaks_idx]

    return {
        "file_id": file_id,
        "n_samples": len(x),
        "peak_abs": peak_abs,
        "implausible": implausible,
        "damage": damage,
        "n_cycles": res["n_cycles"],
        "n_reversals": res["n_reversals"],
        "max_range": res["max_range"],
        "tier": tier, "tier_label": rel.TIER_LABEL[tier],
        "confidence_label": "Medium" if damage < 0.8 else "High",
        "headline": f"Damage {damage:.3f} of 1.0", "reasoning": reasoning,
        "reliability_note": rel.SHM_RELIABILITY_NOTE,
        "trace": trace, "peaks": peaks, "mean": float(x.mean()),
        "histogram": shm_histogram(res),
        "correction_factor": res["correction_factor"], "analytic": res["analytic"],
        "use_correction": bool(b["use_correction"]),
        "official_score": "0.974",
    }


@app.get("/api/shm/meta")
def shm_meta():
    return {
        "title": "SHM — cumulative fatigue damage",
        "subtitle": "Dynamic stress series reduced to a single cumulative damage value via "
                    "rainflow counting and a calibrated Miner's-rule sum.",
        "official_score": "0.974",
    }


@app.post("/api/shm/predict")
async def shm_predict(file: UploadFile = File(...)):
    data = await file.read()
    return build_shm_result(data, file.filename)


@app.get("/api/shm/sample")
def shm_sample():
    path = SAMPLES_DIR / "test02.csv.gz"
    data = gzip.decompress(path.read_bytes())
    return build_shm_result(data, "test02.csv")


@app.get("/api/notes")
def list_notes(subsystem: str, file_id: str):
    conn = _notes_conn()
    try:
        rows = conn.execute(
            "SELECT id, subsystem, file_id, author, text, created_at FROM notes "
            "WHERE subsystem = ? AND file_id = ? ORDER BY created_at ASC",
            (subsystem, file_id),
        ).fetchall()
    finally:
        conn.close()
    cols = ("id", "subsystem", "file_id", "author", "text", "created_at")
    return [dict(zip(cols, row)) for row in rows]


@app.post("/api/notes")
def add_note(note: NoteIn):
    author, text = note.author.strip(), note.text.strip()
    if not author or not text:
        raise HTTPException(400, "Name and note text can't be empty")
    created_at = datetime.now(timezone.utc).isoformat()
    conn = _notes_conn()
    try:
        cur = conn.execute(
            "INSERT INTO notes (subsystem, file_id, author, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (note.subsystem, note.file_id, author, text, created_at),
        )
        conn.commit()
    finally:
        conn.close()
    return {"id": cur.lastrowid, "subsystem": note.subsystem, "file_id": note.file_id,
            "author": author, "text": text, "created_at": created_at}


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    conn = _notes_conn()
    try:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


@app.get("/api/reliability")
def reliability_detail():
    """The full, precisely-sourced reliability text from app/reliability.py — every number here
    traces back to a subsystem's PLAN.md. The main result pages show a one-line distilled
    version instead (reliabilityNotes.js on the frontend); this is the "Under the hood" page's
    single source of truth for the real methodology, so it's served live rather than copied
    into JS where it could drift out of sync."""
    return {
        "door": {"note": rel.DOOR_RELIABILITY_NOTE},
        "acv": {"note": rel.ACV_RELIABILITY_NOTE},
        "shm": {"note": rel.SHM_RELIABILITY_NOTE},
        "rail": {
            "note": rel.RAIL_RELIABILITY_NOTE,
            "classes": [
                {"label": cls, **rel.RAIL_RELIABILITY[cls], "line": rel.rail_class_line(cls)}
                for cls in rel.RAIL_RELIABILITY
            ],
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------------------------- serve the built frontend --

# In production (Docker/Cloud Run) `webapp/frontend/dist` is the `npm run build` output, built
# in an earlier container stage. In local dev it won't exist — `npm run dev` (Vite, port 5173)
# serves the frontend instead and proxies /api to this server, so this block is a no-op then.
FRONTEND_DIST = ROOT / "webapp" / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        """Any non-API route serves the built index.html, so a direct link or a refresh on
        whatever view the SPA is showing doesn't 404 — the app itself decides what to render
        client-side. A path matching an actual built file (e.g. favicon.svg) is served as-is."""
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
