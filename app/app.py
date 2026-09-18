import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st

import theme
from inference import door, overview, pending

SUBS = {
    "overview": {
        "nav": "Overview / upload", "tag": "start", "crumb": "overview", "live": True,
        "title": "Train condition monitoring",
        "subtitle": "Four onboard subsystems, one app. Pick a subsystem, drop in the raw sensor "
                    "file, read the result, download the prediction CSV.",
        "meta": [("model", "—", None), ("version", "—", None),
                 ("val score", "—", None), ("split", "—", None)],
    },
    "door": {
        "nav": "Door", "tag": "IoU-F1", "crumb": "door", "live": True,
        "title": "Door — cycle detection & classification",
        "subtitle": "Continuous stream segmented into door open/close cycles, each classified "
                    "Normal or Abnormal resistance.",
        "meta": [("model", "logreg + gap segmenter", None), ("version", "door-v1", None),
                 ("val score", "1.00 IoU-F1", theme.ACCENT),
                 ("split", "contiguous hold-out", None)],
        "csv": "door_predictions.csv",
    },
    "acv": {
        "nav": "ACV", "tag": "rank", "crumb": "acv", "live": False,
        "title": "ACV — refrigerant leak localisation",
        "subtitle": "Every car in the uploaded file ranked from most to least likely to carry "
                    "the refrigerant leak.",
        "status": "No model yet — this subsystem hasn't been started.",
        "detail": "Reads a train's air-conditioning telemetry workbook (one row every 30 seconds, "
                  "one block of parameters per car) and scores each car against its 8 peers on the "
                  "same train. A leaking unit has to run harder than its neighbours to hold the "
                  "same cabin temperature, so the signal is the difference between cars rather "
                  "than any absolute reading. Output is a ranking, not a yes/no, so a near miss "
                  "still scores.",
        "csv": "acv_predictions.csv", "schema": "file_id, ranked_cars",
        "upload": "ACV telemetry workbook (.xlsx)", "types": ["xlsx"],
        "meta": [("model", "—", None), ("version", "—", None),
                 ("val score", "—", None), ("split", "leave-one-case-out", None)],
    },
    "rail": {
        "nav": "Rail Corrugation", "tag": "macro-F1", "crumb": "rail", "live": False,
        "title": "Rail corrugation — 3-class classification",
        "subtitle": "One-second axle-box recording classified Normal, Side I or Side II from 64 "
                    "vibration and shock channels.",
        "status": "Feature extraction is built (241 features per file); the classifier is pending.",
        "detail": "Reads vibration and shock from all 64 axle boxes at 10 kHz, derives train speed "
                  "from the toothed-wheel pulse, and extracts spectral features per rail side — "
                  "positions 1/3/5/7 are Side I, 2/4/6/8 are Side II. Corrugation is a periodic "
                  "wear pattern, so the giveaway is a characteristic wavelength on one side only, "
                  "not raw vibration amplitude, which mostly tracks speed.",
        "csv": "rail_predictions.csv", "schema": "file_id, prediction",
        "upload": "Axle-box vibration recording (.csv)", "types": ["csv"],
        "meta": [("model", "—", None), ("version", "—", None),
                 ("val score", "—", None), ("split", "stratified by class", None)],
    },
    "shm": {
        "nav": "SHM", "tag": "1−MAPE", "crumb": "shm", "live": False,
        "title": "SHM — cumulative fatigue damage",
        "subtitle": "Dynamic stress series reduced to a single cumulative damage value via "
                    "rainflow counting and a calibrated regressor.",
        "status": "No model yet — this subsystem hasn't been started.",
        "detail": "Reads a dynamic-stress time series from a load-bearing structure (carbody or "
                  "bogie frame) and predicts a single cumulative-damage number. The reference "
                  "values come from rainflow cycle counting fed through Miner's rule, so the "
                  "distribution of stress cycle amplitudes — especially the rare large ones — "
                  "carries most of the signal.",
        "csv": "shm_predictions.csv", "schema": "file_id, prediction",
        "upload": "Dynamic stress segment (.csv)", "types": ["csv"],
        "meta": [("model", "—", None), ("version", "—", None),
                 ("val score", "—", None), ("split", "by file, AW0/AW4", None)],
    },
}
N_LIVE = sum(1 for k, s in SUBS.items() if s["live"] and k != "overview")

st.set_page_config(page_title="gamora · CdM", page_icon="◆", layout="wide")

st.session_state.setdefault("view", "door")
st.session_state.setdefault("batch", False)
st.session_state.setdefault("evidence", True)
st.session_state.setdefault("mode", "dark")
theme.inject()

with st.sidebar:
    theme.brand()
    theme.label("Subsystem")
    for key, meta in SUBS.items():
        active = st.session_state.view == key
        if st.button(f"{meta['nav']} `{meta['tag']}`", key=f"nav_{key}",
                     type="primary" if active else "secondary", use_container_width=True):
            st.session_state.view = key
            st.rerun()

    theme.label("Run mode")
    c1, c2 = st.columns(2)
    if c1.button("Single file", use_container_width=True,
                 type="primary" if not st.session_state.batch else "secondary"):
        st.session_state.batch = False
        st.rerun()
    if c2.button("Batch folder", use_container_width=True,
                 type="primary" if st.session_state.batch else "secondary"):
        st.session_state.batch = True
        st.rerun()
    st.session_state.evidence = st.checkbox("Show model evidence", value=st.session_state.evidence)

    theme.label("Appearance")
    d, l = st.columns(2)
    if d.button("Dark", use_container_width=True,
                type="primary" if st.session_state.mode == "dark" else "secondary"):
        st.session_state.mode = "dark"
        st.rerun()
    if l.button("Light", use_container_width=True,
                type="primary" if st.session_state.mode == "light" else "secondary"):
        st.session_state.mode = "light"
        st.rerun()

    theme.sidebar_meta(SUBS[st.session_state.view]["meta"])

meta = SUBS[st.session_state.view]
theme.topbar("batch" if st.session_state.batch and meta["live"] else meta["crumb"], N_LIVE, 4)

if st.session_state.view == "overview":
    overview.render(meta, SUBS)
elif meta["live"]:
    door.render(meta, batch=st.session_state.batch, evidence=st.session_state.evidence)
else:
    pending.render(meta)
