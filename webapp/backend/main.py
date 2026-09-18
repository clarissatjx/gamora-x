"""FastAPI backend for the React frontend prototype.

Wraps the same subsystem `predict`/`analyse` functions the Streamlit app (`app/`) calls, plus
`app/reliability.py` for the plain-language verdict/severity/reliability data — nothing about
the models changes, this is a second presentation layer. Rail is the only subsystem wired up
so far (Phase 0 prototype); Door/ACV/SHM follow the same shape once this is validated.

Run from the repo root: `uvicorn webapp.backend.main:app --reload --port 8000`
"""
import gzip
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import reliability as rel  # noqa: E402
from subsystems.rail_corrugation import config  # noqa: E402
from subsystems.rail_corrugation.features import _channel_column_indices, load_raw_file  # noqa: E402
from subsystems.rail_corrugation.predict import load_artifact, predict_rail_detailed  # noqa: E402

SAMPLES_DIR = ROOT / "app" / "samples"

app = FastAPI(title="gamora-x API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

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
            f"{res['speed_mps'] * 3.6:.0f} km/h, with {res['probabilities'][pred]:.0%} model confidence."
        )
    else:
        headline = f"{pred} corrugation detected"
        reasoning = (
            f"The {pred} rail's axle boxes show a vibration signature distinct from the healthy "
            f"pattern, {res['probabilities'][pred]:.0%} confidence — side asymmetry "
            f"{asym:+.3f} vs a healthy median near zero."
        )

    return {
        "file_id": file_id,
        "prediction": "Inconclusive" if stationary else pred,
        "csv_prediction": pred,  # what actually gets submitted — never "Inconclusive"
        "stationary": stationary,
        "probabilities": res["probabilities"],
        "speed_kmh": res["speed_mps"] * 3.6,
        "asym": asym,
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
