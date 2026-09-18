import io

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import reliability as rel
import session
import theme
from subsystems.door.loader import CURRENT_COL, POSITION_COL, TIME_COL, load_stream
from subsystems.door.predict import load_model, run, to_output

ABNORMAL = "Abnormal resistance"
# CSS variables for HTML (follow the active mode); charts use concrete hex below.
STATUS_COLOR = {"Normal": theme.GREEN, ABNORMAL: theme.RED}
SAMPLE_SECONDS = 0.02


def _status_hex() -> dict:
    c = theme.chart_colors()
    return {"Normal": c["green"], ABNORMAL: c["red"]}


@st.cache_resource
def _model():
    return load_model()


def process(file):
    """Returns (stream, segments, predictions) for an uploaded or on-disk CSV."""
    df = load_stream(file)
    segs, feats, p_abnormal, _ = run(df, _model())
    out = to_output(segs, p_abnormal)
    out.attrs["features"] = feats.reset_index(drop=True)
    return df, segs, out


def build_chart(df: pd.DataFrame, segs: pd.DataFrame, out: pd.DataFrame) -> alt.Chart:
    alt.data_transformers.disable_max_rows()
    step = max(1, len(df) // 9000)
    trace = pd.DataFrame({
        "x": range(0, len(df), step),
        "current": df[CURRENT_COL].to_numpy()[::step],
        "position": df[POSITION_COL].to_numpy()[::step],
    })
    bands = pd.DataFrame({
        "x": segs.i0.to_numpy(), "x2": segs.i1.to_numpy(),
        "Cycle": [f"c{i + 1}" for i in range(len(out))],
        "Starts": out.start_time.to_numpy(), "Ends": out.end_time.to_numpy(),
        "Status": out.prediction.to_numpy(), "Confidence": out.confidence.to_numpy(),
    })
    c = theme.chart_colors()
    status_hex = _status_hex()
    scale = alt.Scale(domain=list(status_hex), range=list(status_hex.values()))
    rects = alt.Chart(bands).mark_rect(opacity=0.14, strokeWidth=1, strokeOpacity=0.45).encode(
        x=alt.X("x:Q", title=None, axis=alt.Axis(labels=False, ticks=False, domain=False)),
        x2="x2:Q",
        color=alt.Color("Status:N", scale=scale, legend=None),
        stroke=alt.Stroke("Status:N", scale=scale, legend=None),
        tooltip=["Cycle", "Starts", "Ends", "Status", "Confidence"],
    )
    pos = alt.Chart(trace).mark_line(
        strokeWidth=1.3, color=c["dim"], strokeDash=[3, 3], opacity=0.9,
    ).encode(
        x="x:Q",
        y=alt.Y("position:Q", axis=None,
                scale=alt.Scale(domain=[0, float(trace.position.max() or 1) * 3.4])),
    )
    line = alt.Chart(trace).mark_line(strokeWidth=1.6, color=c["accent"]).encode(
        x="x:Q", y=alt.Y("current:Q", title="motor current (mA)"),
    )
    layered = alt.layer(rects, pos, line).resolve_scale(y="independent", color="shared")
    return theme.style_chart(layered.properties(height=240))


def _worst_cycle(out: pd.DataFrame):
    """The most confidently flagged cycle, with its excess current over the healthy peers
    of the same operation in this file — the basis for both the evidence panel and the
    file-level severity tier. None if nothing was flagged."""
    feats = out.attrs.get("features")
    if feats is None or not (out.prediction == ABNORMAL).any():
        return None
    abn = out.index[out.prediction == ABNORMAL]
    i = int(out.loc[abn, "confidence"].idxmax())
    op = feats.op.iloc[i]
    peers = feats[(feats.op == op) & (out.prediction == "Normal").to_numpy()]
    if peers.empty:
        peers = feats[feats.op == op]
    excess = float(feats.cur_mid.iloc[i] / max(peers.cur_mid.median(), 1e-9) - 1)
    return {"i": i, "feats": feats, "peers": peers, "excess": excess,
            "confidence": float(out.confidence.iloc[i])}


def _evidence(out: pd.DataFrame, worst: dict):
    i, feats, peers, excess = worst["i"], worst["feats"], worst["peers"], worst["excess"]

    def tile(label, value, baseline, fmt, unit=""):
        return (label, f"{fmt.format(value)}{unit}", f"baseline {fmt.format(baseline)}{unit}",
                theme.RED)

    tiles = [
        tile("Mid-travel current", feats.cur_mid.iloc[i], peers.cur_mid.median(), "{:.0f}", " mA"),
        tile("Cycle duration", feats.n_rows.iloc[i] * SAMPLE_SECONDS,
             peers.n_rows.median() * SAMPLE_SECONDS, "{:.2f}", " s"),
        tile("Back-EMF, mid-travel", feats.emf_mid.iloc[i], peers.emf_mid.median(), "{:.0f}"),
    ]
    prose = (
        f"Mid-travel motor current on cycle {i + 1} sits {excess:.0%} above the healthy cycles of "
        f"the same operation in this recording, while back-EMF falls — the motor is pushing harder "
        f"and turning slower. Both point to added mechanical resistance rather than a control fault."
    )
    return f"Why cycle {i + 1} was flagged", tiles, prose


def _table(out: pd.DataFrame, batch: bool):
    rows = []
    for i, r in enumerate(out.itertuples(index=False), start=1):
        rows.append([
            f"{i:02d}",
            r.start_time, r.end_time,
            theme.pill(r.prediction, STATUS_COLOR[r.prediction]),
            f"{r.confidence:.2f}",
        ])
    theme.table(
        ["#", "start_time", "end_time", "prediction", "confidence"], rows,
        f"door_predictions.csv · {len(out)} rows", "start_time, end_time, prediction",
        footer="confidence is informational — only start_time, end_time and prediction are scored."
        if not batch else f"concatenated from {out.attrs.get('n_files', 1)} uploaded files.",
    )


def render(meta: dict, batch: bool = False, evidence: bool = True):
    theme.page_title(
        "Batch run — Door" if batch else meta["title"],
        "Every uploaded stream scored in one pass, with the combined prediction CSV ready to "
        "download." if batch else meta["subtitle"],
    )
    st.write("")

    # The uploader keeps its own copy of the bytes in session state: a sidebar button calls
    # st.rerun(), which aborts the script before this widget is created, and Streamlit then
    # drops state for widgets that did not render. See session.file_input.
    uploads, upload_key = session.file_input(
        "door", "Door controller recording (.csv)", ["csv"], batch,
        "A continuous recording containing many door open/close cycles back to back.")

    if not uploads:
        theme.banner(
            "Waiting for a recording. The model finds each open/close cycle on its own — you "
            "don't need to split the file up. Every cycle it finds is scored, charted and listed "
            "below, ready to download as a CSV.",
            icon="⬆", color=theme.ACCENT,
        )
        session.sample_button("door")
        return

    parsed, failures = [], []
    for name, data in uploads:
        try:
            df, segs, out = process(io.BytesIO(data))
        except ValueError as e:
            failures.append((name, str(e)))
            continue
        except Exception as e:  # noqa: BLE001
            failures.append((name, f"could not read this file: {e}"))
            continue
        parsed.append((name, df, segs, out))

    for name, msg in failures:
        st.error(f"{name} — {msg}")
    if not parsed:
        return

    frames = [p[3] for p in parsed]
    combined = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    combined.attrs["n_files"] = len(frames)
    n_abn = int((combined.prediction == ABNORMAL).sum())

    if batch:
        theme.banner(
            f"{len(frames)} of {len(uploads)} files parsed successfully — "
            f"{len(combined)} cycles detected in total, {n_abn} flagged abnormal.",
            color=theme.ACCENT if not failures else theme.AMBER,
            icon="✓" if not failures else "!",
        )
    name0, df0, segs0, out0 = parsed[session.inspect_picker("door", [p[0] for p in parsed]) if batch else 0]
    dur = len(df0) * SAMPLE_SECONDS
    if not batch:
        theme.banner(
            f"{name0} accepted — {len(df0):,} rows, {df0.shape[1] - 1} columns, "
            f"{int(dur // 60)} min {dur % 60:04.1f} s of stream. {len(out0)} cycles detected.",
        )

    worst = _worst_cycle(out0)
    if n_abn == 0:
        theme.verdict("All cycles normal", "ok", rel.TIER_LABEL["ok"], "High",
                     "No cycle in this recording drew more current or less back-EMF than the "
                     "healthy range for its operation.")
    else:
        tier = rel.door_severity(ABNORMAL, worst["excess"], worst["confidence"]) if worst else "inspect"
        conf = rel.confidence_label(worst["confidence"]) if worst else "Medium"
        theme.verdict(
            f"{n_abn} of {len(combined)} cycle{'s' if len(combined) != 1 else ''} show abnormal resistance",
            tier, rel.TIER_LABEL[tier], conf,
            (f"The clearest case is cycle {worst['i'] + 1}"
             + (f" in {name0}" if batch else "")
             + f", drawing {worst['excess']:.0%} more current than a healthy cycle of the same "
               "operation while turning slower — consistent with added mechanical resistance."
             if worst else "Cycles were flagged abnormal; open the evidence panel below for detail."),
        )
    theme.reliability_panel("How reliable is this?", rel.DOOR_RELIABILITY_NOTE)

    lengths = (segs0.i1 - segs0.i0 + 1) * SAMPLE_SECONDS
    theme.metrics([
        ("Cycles detected", str(len(combined)),
         f"across {len(frames)} files" if batch else f"in {dur / 60:.1f} min of stream", None),
        ("Abnormal resistance", str(n_abn),
         f"{n_abn / max(len(combined), 1):.1%} of cycles", theme.RED if n_abn else None),
        ("Mean cycle length", f"{lengths.mean():.2f} s", f"σ {lengths.std():.2f} s", None),
        ("Mean confidence", f"{combined.confidence.mean():.2f}",
         f"lowest {combined.confidence.min():.2f}", None),
    ])

    with theme.panel("Motor current with detected door cycles",
                     right=theme.legend([("Normal", theme.GREEN), (ABNORMAL, theme.RED)])):
        st.altair_chart(build_chart(df0, segs0, out0), use_container_width=True)
        theme.axis(str(df0[TIME_COL].iloc[0]), str(df0[TIME_COL].iloc[-1]))
        st.markdown(
            f'<div style="font-size:12.5px;color:{theme.FAINT};margin-top:8px">'
            f'Shaded bands are detected cycles, cyan is motor current, the dashed grey line is '
            f'door leaf position. Idle gaps between cycles are removed.'
            f'{f" Showing {name0}." if batch else ""}</div>',
            unsafe_allow_html=True,
        )

    if evidence and worst:
        theme.evidence(*_evidence(out0, worst))

    _table(combined, batch)
    csv_bytes = combined[["start_time", "end_time", "prediction", "confidence"]].to_csv(index=False).encode()
    session.record("door", meta["csv"], csv_bytes, len(combined), [p[0] for p in parsed])
    dl, rs, _ = st.columns([0.9, 0.6, 3.5])
    with dl:
        st.download_button(
            "⬇  Download CSV", csv_bytes,
            file_name=meta["csv"], mime="text/csv", use_container_width=True,
        )
    if rs.button("Reset", use_container_width=True):
        st.session_state.pop("door_files", None)
        st.session_state.pop(upload_key, None)
        st.rerun()
