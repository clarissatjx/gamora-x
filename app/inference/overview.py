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
    done = session.results()
    theme.metrics([
        ("Overall held-out score", f"{overall:.3f}" if overall else "—", "mean of the four leaderboard scores", theme.ACCENT),
        ("Subsystems attempted", f"{len(live)} / 4", "each weighs 25% of the overall", None),
        ("Test files scored", str(sum(TEST_FILES.values())), TEST_NOTE, None),
        ("Scored this session", f"{len(done)} / 4",
         " · ".join(session.NAV[k] for k in session.ZIP_ORDER if k in done) if done else "nothing yet — try a sample",
         theme.ACCENT if done else None),
    ])
    st.markdown(
        f'<div style="font-size:12.5px;color:{theme.FAINT};margin:-8px 0 18px">'
        f'"Overall" is a plain average of the four scores — the competition\'s own rule — so ACV\'s '
        f'result on 1 workbook counts the same as Rail\'s on 68 recordings. It is not a measure of '
        f'how much track or fleet each subsystem actually covers. Open a subsystem for what it gets '
        f'wrong and how it should change what you do.</div>', unsafe_allow_html=True)

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
        f'Or pick a subsystem below — each card can also load a bundled sample file. If detection '
        f'guesses wrong, the page you land on checks the file\'s actual structure and explains why, '
        f'rather than guessing again.</div>',
        unsafe_allow_html=True)

    session.overview_panel()

    cols = st.columns(4, gap="small")
    for col, key in zip(cols, ["door", "acv", "rail", "shm"]):
        s = subs[key]
        official = s.get("official")
        cv = s.get("cv")
        score_line = "" if not official else (
            f'<div style="font-family:{theme.MONO};font-size:12px;color:{theme.FAINT};'
            f'padding-top:10px;border-top:1px solid {theme.BORDER}">'
            f'<div style="display:flex;justify-content:space-between">'
            f'<span>held-out (official)</span><span style="color:{theme.ACCENT}">{official[0]}</span></div>'
            + (f'<div style="display:flex;justify-content:space-between;margin-top:2px">'
               f'<span>cross-val (ours)</span><span style="color:{theme.FAINT}">{cv}</span></div>'
               if cv else "") + '</div>')
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
