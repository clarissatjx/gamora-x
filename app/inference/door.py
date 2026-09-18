import altair as alt
import pandas as pd
import streamlit as st

from subsystems.door.loader import CURRENT_COL, load_stream
from subsystems.door.predict import load_model, run, to_output

ABNORMAL = "Abnormal resistance"
COLORS = {"Normal": "#4C9F70", ABNORMAL: "#D9534F"}


@st.cache_resource
def _model():
    return load_model()


def process(file) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Returns (stream, segments, predictions) for an uploaded or on-disk CSV."""
    df = load_stream(file)
    segs, _, p_abnormal, _ = run(df, _model())
    return df, segs, to_output(segs, p_abnormal)


def build_chart(df: pd.DataFrame, segs: pd.DataFrame, out: pd.DataFrame) -> alt.Chart:
    alt.data_transformers.disable_max_rows()
    trace = pd.DataFrame({"sample": range(len(df)), "current_mA": df[CURRENT_COL].values})
    bands = pd.DataFrame({
        "x": segs.i0.values, "x2": segs.i1.values,
        "start": out.start_time.values, "end": out.end_time.values,
        "prediction": out.prediction.values, "confidence": out.confidence.values,
    })
    rects = alt.Chart(bands).mark_rect(opacity=0.3).encode(
        x=alt.X("x:Q", title="sample index (20 ms per sample)"), x2="x2:Q",
        color=alt.Color("prediction:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values())), title="Cycle status"),
        tooltip=["start", "end", "prediction", "confidence"],
    )
    line = alt.Chart(trace).mark_line(strokeWidth=0.8, color="#333").encode(
        x="sample:Q", y=alt.Y("current_mA:Q", title="motor current (mA)")
    )
    return (rects + line).properties(height=320).interactive(bind_y=False)


def render():
    st.header("Door: abnormal resistance detection")
    st.write(
        "Upload a door controller recording (`.csv`). The app finds every door open/close cycle in the "
        "recording and flags cycles where the motor had to work unusually hard, which points to "
        "obstructions, jammed seals or a deformed door leaf."
    )
    file = st.file_uploader("Door data file", type=["csv"], key="door_upload")
    if file is None:
        return
    try:
        df, segs, out = process(file)
    except ValueError as e:
        st.error(str(e))
        return
    except Exception as e:
        st.error(f"Could not process this file: {e}")
        return

    n_abn = int((out.prediction == ABNORMAL).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Cycles found", len(out))
    c2.metric("Flagged: abnormal resistance", n_abn)
    c3.metric("Normal", len(out) - n_abn)
    if n_abn:
        st.warning(f"{n_abn} cycle(s) show abnormal resistance. Shaded red in the chart below.")
    else:
        st.success("No abnormal-resistance cycles detected.")

    st.altair_chart(build_chart(df, segs, out), use_container_width=True)
    st.dataframe(out, use_container_width=True, hide_index=True)
    st.download_button(
        "Download door_predictions.csv",
        out.to_csv(index=False).encode(),
        file_name="door_predictions.csv",
        mime="text/csv",
    )
