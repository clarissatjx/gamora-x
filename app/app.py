import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st

import theme
from inference import door, pending

SUBSYSTEMS = {
    "door": {
        "key": "door", "nav": "Door", "live": True,
        "title": "Door · abnormal resistance",
        "subtitle": "Finds every door open/close cycle in a continuous controller recording and flags "
                    "cycles where the motor worked unusually hard — obstructions, jammed seals, or a "
                    "deformed door leaf.",
    },
    "acv": {
        "key": "acv", "nav": "ACV", "live": False,
        "title": "ACV · refrigerant leak localisation",
        "subtitle": "Ranks all 8 cars of a train from most to least likely to be losing refrigerant.",
        "status": "No model yet — this subsystem hasn't been started.",
        "detail": "Reads a train's air-conditioning telemetry workbook (one row every 30 seconds, one "
                  "block of parameters per car) and scores each car against its 8 peers on the same "
                  "train. A leaking unit has to run harder than its neighbours to hold the same cabin "
                  "temperature, so the signal is the <em>difference</em> between cars rather than any "
                  "absolute reading. Output is a ranking, not a yes/no, so a near miss still scores.",
        "output_file": "acv_predictions.csv",
        "schema": [("file_id", "source workbook name"), ("ranked_cars", "8 car IDs, most likely first")],
        "upload_label": "ACV telemetry workbook (.xlsx)", "file_types": ["xlsx"],
    },
    "rail": {
        "key": "rail", "nav": "Rail corrugation", "live": False,
        "title": "Rail corrugation · side classification",
        "subtitle": "Classifies a one-second axle-box vibration recording as Normal, Side I, or Side II "
                    "corrugation.",
        "status": "Feature extraction is built (241 features per file); the classifier is still pending.",
        "detail": "Reads vibration and shock from all 64 axle boxes at 10 kHz, derives train speed from "
                  "the toothed-wheel pulse, and extracts spectral features per rail side — positions "
                  "1/3/5/7 are Side I, 2/4/6/8 are Side II. Corrugation is a periodic wear pattern, so "
                  "the giveaway is a characteristic wavelength on one side only, not raw vibration "
                  "amplitude, which mostly tracks speed.",
        "output_file": "rail_predictions.csv",
        "schema": [("file_id", "source file name"), ("prediction", "Normal · Side I · Side II")],
        "upload_label": "Axle-box vibration recording (.csv)", "file_types": ["csv"],
    },
    "shm": {
        "key": "shm", "nav": "Structural health", "live": False,
        "title": "SHM · cumulative fatigue damage",
        "subtitle": "Estimates how much fatigue damage a structural measurement point accumulated over a "
                    "recorded segment.",
        "status": "No model yet — this subsystem hasn't been started.",
        "detail": "Reads a dynamic-stress time series from a load-bearing structure (carbody or bogie "
                  "frame) and predicts a single cumulative-damage number. The reference values come from "
                  "rainflow cycle counting fed through Miner's rule, so the distribution of stress cycle "
                  "amplitudes — especially the rare large ones — carries most of the signal.",
        "output_file": "shm_predictions.csv",
        "schema": [("file_id", "source file name"), ("prediction", "cumulative damage (numeric)")],
        "upload_label": "Dynamic stress segment (.csv)", "file_types": ["csv"],
    },
}

st.set_page_config(page_title="Gamora · Condition Monitoring", page_icon="◆", layout="wide")
theme.inject()

if "view" not in st.session_state:
    st.session_state.view = "door"

with st.sidebar:
    theme.brand("GAMORA", "CONDITION&nbsp;MONITORING")
    theme.nav_label("SUBSYSTEMS")
    for i, (key, meta) in enumerate(SUBSYSTEMS.items(), start=1):
        active = st.session_state.view == key
        if st.button(f"0{i}   {meta['nav']}", key=f"nav_{key}",
                     type="primary" if active else "secondary", use_container_width=True):
            st.session_state.view = key
            st.rerun()
    n_live = sum(m["live"] for m in SUBSYSTEMS.values())
    theme.sidebar_footer(
        [f"{n_live} of {len(SUBSYSTEMS)} models live", "Door · 148 cycles scored", "NebulaX PS3"],
        dot_color=theme.LOW if n_live else theme.MED,
    )

meta = SUBSYSTEMS[st.session_state.view]
if meta["live"]:
    door.render(meta)
else:
    pending.render(meta)
