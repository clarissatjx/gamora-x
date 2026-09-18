import streamlit as st

import theme

TASKS = {
    "door": "Segment the continuous stream into door cycles, then flag abnormal resistance.",
    "acv": "Rank every car from most to least likely to have a refrigerant leak.",
    "rail": "Classify a 1 s axle-box recording as Normal, Side I or Side II.",
    "shm": "Estimate cumulative fatigue damage from a dynamic stress series.",
}
OUTPUTS = {
    "door": "door_predictions.csv", "acv": "acv_predictions.csv",
    "rail": "rail_predictions.csv", "shm": "shm_predictions.csv",
}


def render(meta: dict, subs: dict):
    theme.page_title(meta["title"], meta["subtitle"])
    st.write("")
    live = [k for k, s in subs.items() if s["live"] and k != "overview"]
    theme.banner(
        f"{len(live)} of 4 models loaded and ready — "
        f"{', '.join(subs[k]['nav'] for k in live)}. The remaining subsystems are still in training.",
        icon="✓" if len(live) == 4 else "!",
        color=theme.ACCENT if len(live) == 4 else theme.AMBER,
    )
    theme.metrics([
        ("Subsystems attempted", f"{len(live)} / 4", "overall score weights 25% each", None),
        ("Models loaded", str(len(live)), " · ".join(live), None),
        ("Door val score", "1.00", "IoU-weighted F1, held-out cycles", theme.ACCENT),
        ("Median runtime", "1.4 s", "per uploaded file", None),
    ])

    st.markdown(
        f'<div style="background:{theme.PANEL};border:2px dashed {theme.BORDER_STRONG};'
        f'border-radius:10px;padding:34px 28px;display:flex;flex-direction:column;'
        f'align-items:center;gap:9px;text-align:center;margin-bottom:22px">'
        f'<div style="width:46px;height:46px;border-radius:10px;background:{theme.BG};'
        f'border:1px solid {theme.BORDER};display:flex;align-items:center;justify-content:center;'
        f'font-size:20px;color:{theme.ACCENT}">⬆</div>'
        f'<div style="font-size:16.5px;font-weight:600">Pick a subsystem on the left to begin</div>'
        f'<div style="font-size:13.5px;color:{theme.MUTED};max-width:52ch">'
        f'Each subsystem accepts its raw dataset format as-is — .csv and .xlsx, up to 500 MB per '
        f'file. No renaming, no pre-processing.</div></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(4, gap="small")
    for col, key in zip(cols, ["door", "acv", "rail", "shm"]):
        s = subs[key]
        with col:
            st.markdown(
                f'<div class="gx-card"><div class="gx-card-t">'
                f'<div class="gx-card-n">{s["nav"]}</div>'
                f'<div class="gx-chip">{s["tag"]}</div></div>'
                f'<div class="gx-card-task">{TASKS[key]}</div>'
                f'<div class="gx-card-out">{OUTPUTS[key]}</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open" if s["live"] else "Not wired up", key=f"card_{key}",
                         use_container_width=True, disabled=not s["live"]):
                st.session_state.view = key
                st.rerun()
