import streamlit as st

import session
import theme

TASKS = {
    "door": "Segment the continuous stream into door cycles, then flag abnormal resistance.",
    "acv": "Rank every car from most to least likely to have a refrigerant leak.",
    "rail": "Classify a 1 s axle-box recording as Normal, Side I or Side II.",
    "shm": "Estimate cumulative fatigue damage from a dynamic stress series.",
}
INPUTS = {"door": "Door stream .csv", "acv": "ACV workbook .xlsx", "rail": "Axle-box .csv", "shm": "Stress .csv"}
TEST_FILES = {"door": 38, "acv": 1, "rail": 68, "shm": 16}
TEST_NOTE = "38 cycles · 1 workbook · 68 · 16"


def detect_subsystem(name: str, data: bytes):
    """Which subsystem a raw file belongs to, decided from its contents, not its name."""
    if name.lower().endswith(".xlsx") or data[:2] == b"PK":
        return "acv"
    head = data[:4096].decode("utf-8", errors="ignore")
    first = head.split("\n", 1)[0].strip()
    if "Motor current" in first or "Datetime" in first:
        return "door"
    if "Rotating speed" in first or "Vibration of bearing" in first or first.count(",") >= 100:
        return "rail"
    try:
        float(first)
        return "shm" if "," not in first else None
    except ValueError:
        return None


def render(meta: dict, subs: dict):
    theme.page_title(meta["title"], meta["subtitle"])
    st.write("")
    live = [k for k, s in subs.items() if s["live"] and k != "overview"]
    scores = [float(subs[k]["official"][0]) for k in live if "official" in subs[k]]
    overall = sum(scores) / len(scores) if scores else None

    theme.banner(
        f"All four models loaded. Held-out leaderboard scores — "
        + " · ".join(f"{subs[k]['nav']} {subs[k]['official'][0]}" for k in live if "official" in subs[k])
        + (f" · overall {overall:.3f}." if overall else "."),
    )
    theme.metrics([
        ("Subsystems attempted", f"{len(live)} / 4", "overall score weights 25% each", None),
        ("Models loaded", str(len(live)), " · ".join(live), None),
        ("Overall held-out score", f"{overall:.3f}" if overall else "—", "mean of the four leaderboard scores", theme.ACCENT),
        ("Test files scored", str(sum(TEST_FILES.values())), TEST_NOTE, None),
    ])

    file = st.file_uploader(
        "Drop any sensor file here — the app works out which subsystem it belongs to",
        type=["csv", "xlsx"], key="overview_upload",
        help="Raw dataset formats as-is: Door stream, ACV workbook, axle-box recording, or stress segment.",
    )
    if file is not None:
        key = detect_subsystem(file.name, file.getvalue())
        if key is None:
            st.error(f"{file.name} doesn't look like any of the four subsystems' raw files. Expected a Door "
                     "stream, an ACV workbook, a 129-column axle-box recording, or a single-column stress series.")
        else:
            st.session_state[f"{key}_files"] = [(file.name, file.getvalue())]
            st.session_state.pop("overview_upload", None)
            st.session_state.view = key
            st.rerun()

    st.markdown(
        f'<div style="font-size:13.5px;color:{theme.MUTED};margin:-4px 0 18px">'
        f'Detection is by content: an .xlsx is ACV, a header with <span style="font-family:{theme.MONO}">Motor '
        f'current</span> is Door, 129 columns starting with the speed pulse is Rail, one headerless column is SHM. '
        f'Or pick a subsystem below — each card can also load a bundled sample file.</div>',
        unsafe_allow_html=True)

    session.overview_panel()

    cols = st.columns(4, gap="small")
    for col, key in zip(cols, ["door", "acv", "rail", "shm"]):
        s = subs[key]
        official = s.get("official")
        score_line = (f'<div style="display:flex;justify-content:space-between;font-family:{theme.MONO};'
                      f'font-size:12px;color:{theme.FAINT};padding-top:10px;border-top:1px solid {theme.BORDER}">'
                      f'<span>held-out</span><span style="color:{theme.ACCENT}">{official[0]}</span></div>'
                      if official else "")
        with col:
            st.markdown(
                f'<div class="gx-card"><div class="gx-card-t"><div class="gx-card-n">{s["nav"]}</div>'
                f'<div class="gx-chip">{s["tag"]}</div></div>'
                f'<div class="gx-card-task">{TASKS[key]}</div>'
                f'<div class="gx-card-out">{INPUTS[key]} → {s["csv"]}</div>{score_line}</div>',
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns(2, gap="small")
            if b1.button("Open", key=f"card_{key}", use_container_width=True):
                st.session_state.view = key
                st.rerun()
            if b2.button("Sample", key=f"sample_{key}", use_container_width=True,
                         help=f"Load {session.sample_name(key)}: {session.SAMPLES[key][1]}"):
                session.use_sample(key)
