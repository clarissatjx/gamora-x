import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st

st.set_page_config(page_title="gamora · CdM", page_icon="◆", layout="wide")

import theme  # noqa: E402
from inference import acv_page, door, overview, pending, rail_page, shm  # noqa: E402

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
        "official": ("1.000", "IoU-weighted F1, held-out"),
    },
    "acv": {
        "nav": "ACV", "tag": "rank", "crumb": "acv", "live": True,
        "title": "ACV — refrigerant leak localisation",
        "subtitle": "Every car in the uploaded file ranked from most to least likely to carry "
                    "the refrigerant leak.",
        "csv": "acv_predictions.csv",
        "official": ("0.875", "rank-decay, v1 ranking · v2 pending"),
        "meta": [("model", "physics gap + heuristic", None), ("version", "acv-v2", None),
                 ("val score", "1.000 rank-decay", theme.ACCENT), ("split", "leave-one-case-out, 6", None)],
    },
    "rail": {
        "nav": "Rail Corrugation", "tag": "macro-F1", "crumb": "rail", "live": True,
        "title": "Rail corrugation — 3-class classification",
        "subtitle": "One-second axle-box recording classified Normal, Side I or Side II from 64 "
                    "vibration and shock channels.",
        "csv": "rail_predictions.csv",
        "official": ("0.888", "macro F1, held-out"),
        "meta": [("model", "HGB + stationary rule", None), ("version", "rail-v1", None),
                 ("val score", "0.81 macro-F1 (CV)", theme.ACCENT), ("split", "stratified 5-fold ×5", None)],
    },
    "shm": {
        "nav": "SHM", "tag": "1−MAPE", "crumb": "shm", "live": True,
        "title": "SHM — cumulative fatigue damage",
        "subtitle": "Dynamic stress series reduced to a single cumulative damage value via "
                    "rainflow counting and a calibrated Miner's-rule sum.",
        "csv": "shm_predictions.csv",
        "official": ("0.974", "1 − MAPE, held-out"),
        "meta": shm.meta_rows(),
    },
}
N_LIVE = sum(1 for k, s in SUBS.items() if s["live"] and k != "overview")
PAGES = {"door": door.render, "shm": shm.render, "acv": acv_page.render, "rail": rail_page.render}

st.session_state.setdefault("view", "overview")
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
    PAGES[st.session_state.view](meta, batch=st.session_state.batch, evidence=st.session_state.evidence)
else:
    pending.render(meta)
