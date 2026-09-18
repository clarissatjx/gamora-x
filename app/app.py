import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st

from inference import door

SUBSYSTEMS = {
    "Door": door.render,
    "ACV": None,
    "Rail Corrugation": None,
    "SHM": None,
}

st.set_page_config(page_title="Train Condition Monitoring", layout="wide")
st.title("Train Condition Monitoring")
choice = st.sidebar.selectbox("Subsystem", list(SUBSYSTEMS))
render = SUBSYSTEMS[choice]
if render is None:
    st.info(f"{choice} is not wired up yet.")
else:
    render()
