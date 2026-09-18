import altair as alt
import pandas as pd
import streamlit as st

import theme
from subsystems.door.loader import CURRENT_COL, load_stream
from subsystems.door.predict import load_model, run, to_output

ABNORMAL = "Abnormal resistance"
COLORS = {"Normal": theme.LOW, ABNORMAL: theme.HIGH}


@st.cache_resource
def _model():
    return load_model()


def process(file):
    """Returns (stream, segments, predictions) for an uploaded or on-disk CSV."""
    df = load_stream(file)
    segs, _, p_abnormal, _ = run(df, _model())
    return df, segs, to_output(segs, p_abnormal)


def build_chart(df: pd.DataFrame, segs: pd.DataFrame, out: pd.DataFrame) -> alt.Chart:
    alt.data_transformers.disable_max_rows()
    step = max(1, len(df) // 12000)
    trace = pd.DataFrame({
        "position": range(0, len(df), step),
        "current_mA": df[CURRENT_COL].values[::step],
    })
    bands = pd.DataFrame({
        "x": segs.i0.values, "x2": segs.i1.values,
        "Cycle": [f"#{i + 1}" for i in range(len(out))],
        "Starts": out.start_time.values, "Ends": out.end_time.values,
        "Status": out.prediction.values, "Confidence": out.confidence.values,
    })
    rects = alt.Chart(bands).mark_rect(opacity=0.26).encode(
        x=alt.X("x:Q", title="Position in recording"),
        x2="x2:Q",
        color=alt.Color(
            "Status:N",
            scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())),
            legend=alt.Legend(title=None),
        ),
        tooltip=["Cycle", "Starts", "Ends", "Status", "Confidence"],
    )
    line = alt.Chart(trace).mark_line(strokeWidth=0.7, color=theme.INK, opacity=0.75).encode(
        x="position:Q", y=alt.Y("current_mA:Q", title="Motor current (mA)"),
    )
    return theme.style_chart((rects + line).properties(height=300))


def _styled_table(out: pd.DataFrame):
    view = out.rename(columns={
        "start_time": "Starts", "end_time": "Ends",
        "prediction": "Status", "confidence": "Confidence",
    })
    view.insert(0, "Cycle", [f"#{i + 1}" for i in range(len(view))])

    def colour(col):
        return [
            f"color: {theme.HIGH}; font-weight: 600" if v == ABNORMAL else f"color: {theme.MUTED}"
            for v in col
        ]

    return view.style.apply(colour, subset=["Status"]).format({"Confidence": "{:.1%}"})


def render(meta: dict):
    file = st.session_state.get("door_upload")
    result = None
    if file is not None:
        try:
            result = process(file)
        except ValueError as e:
            result = e
        except Exception as e:  # noqa: BLE001 - surface anything else as a readable message
            result = ValueError(f"Could not read this file: {e}")

    if isinstance(result, tuple):
        _, _, out = result
        n_abn = int((out.prediction == ABNORMAL).sum())
        kpis = [
            (len(out), "cycles found"),
            (n_abn, "abnormal", False, theme.HIGH if n_abn else None),
            (len(out) - n_abn, "normal"),
            (f"{out.confidence.mean():.0%}", "mean confidence", True),
        ]
    else:
        kpis = [("—", "cycles found"), ("—", "abnormal"), ("—", "normal")]
    theme.page_header(meta["title"], meta["subtitle"], kpis)

    st.file_uploader(
        "Door controller recording (.csv)", type=["csv"], key="door_upload",
        help="A continuous recording containing many door open/close cycles back to back.",
    )

    if result is None:
        theme.note(
            "<strong>Drop in a recording to begin.</strong> The model finds each open/close cycle on its "
            "own — you don't need to split the file up. Every cycle it finds is scored, charted, and "
            "listed below, ready to download as a CSV.",
        )
        return
    if isinstance(result, ValueError):
        st.error(str(result))
        return

    df, segs, out = result
    n_abn = int((out.prediction == ABNORMAL).sum())
    if n_abn:
        avg = out.loc[out.prediction == ABNORMAL, "confidence"].mean()
        theme.note(
            f"<strong>{n_abn} of {len(out)} cycles show abnormal resistance</strong>, flagged with "
            f"{avg:.0%} average confidence and shaded red below. Inspect the slide rails, rubber seals "
            f"and door leaf alignment on this door before the fault worsens into a jam.",
            icon="!",
        )
    else:
        theme.note(
            f"<strong>All {len(out)} cycles look normal.</strong> Motor effort stayed within the healthy "
            f"range across every open and close in this recording — no action needed.",
            icon="✓",
        )

    with theme.card("Motor current across the recording"):
        st.altair_chart(build_chart(df, segs, out), use_container_width=True)
        st.markdown(
            f"<div style='font-size:12px;color:{theme.FAINT};margin-top:-8px'>"
            f"Each shaded band is one door cycle. The line is motor current — higher, broader humps mean "
            f"the motor fought more resistance. Idle gaps between cycles are removed.</div>",
            unsafe_allow_html=True,
        )

    with theme.card("Cycle by cycle"):
        st.dataframe(_styled_table(out), use_container_width=True, hide_index=True)
        st.download_button(
            "Download door_predictions.csv",
            out.to_csv(index=False).encode(),
            file_name="door_predictions.csv",
            mime="text/csv",
        )
