import io
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import session
import theme
from subsystems.rail_corrugation import config
from subsystems.rail_corrugation.features import _channel_column_indices, load_raw_file
from subsystems.rail_corrugation.predict import load_artifact, predict_rail_detailed

CLASS_COLOR = {"Normal": theme.GREEN, "Side I": theme.ACCENT, "Side II": theme.AMBER}
HEADLINE = "asym_diff_vib_rms_mean"


@st.cache_resource
def _artifact():
    return load_artifact()


@st.cache_resource
def _train_reference():
    """Class medians of the headline asymmetry feature and speed, from the committed feature table."""
    df = pd.read_csv(config.ARTIFACTS_DIR / "train_features.csv")
    df = df[df.speed_mps > 0]
    return df.groupby("label")[[HEADLINE, "speed_mps"]].median()


def _channel_rms(arr: np.ndarray) -> pd.DataFrame:
    rows = []
    for side, positions in (("Side I", config.SIDE_I_POSITIONS), ("Side II", config.SIDE_II_POSITIONS)):
        vib, _ = _channel_column_indices(positions)
        for col in vib:
            k = (col - 1) // 2
            car, pos = k // config.N_POSITIONS + 1, k % config.N_POSITIONS + 1
            x = arr[:, col].astype(float)
            rows.append({"channel": f"C{car}P{pos}", "order": k, "side": side, "rms": float((x - x.mean()).std())})
    return pd.DataFrame(rows).sort_values("order")


def process(data: bytes, name: str) -> dict:
    res = predict_rail_detailed(io.BytesIO(data), artifact=_artifact())
    arr = load_raw_file(io.BytesIO(data))
    ch = _channel_rms(arr)
    side_i = ch[ch.side == "Side I"].rms.mean()
    side_ii = ch[ch.side == "Side II"].rms.mean()
    return {**res, "file_id": name, "channels": ch, "asym": float(side_i - side_ii)}


def channel_chart(res: dict):
    c = theme.chart_colors()
    df = res["channels"].copy()
    pred = res["prediction"]
    df["hot"] = (df.side == pred) if pred in ("Side I", "Side II") else False
    hot_color = c["accent"] if pred == "Side I" else c["amber"]
    bars = alt.Chart(df).mark_bar(cornerRadius=1).encode(
        x=alt.X("channel:N", sort=alt.SortField("order"), title="axle box (car, position)",
                axis=alt.Axis(labelAngle=-90, labelFontSize=8)),
        y=alt.Y("rms:Q", title="vibration RMS (m/s²)"),
        color=alt.condition("datum.hot", alt.value(hot_color), alt.value(c["idle_bar"])),
        tooltip=["channel:N", "side:N", alt.Tooltip("rms:Q", format=".3f")],
    )
    return theme.style_chart(bars.properties(height=170))


def prediction_panel(res: dict):
    pred = res["prediction"]
    with theme.panel("Prediction"):
        st.markdown(f'<div style="font-size:38px;font-weight:700;letter-spacing:-0.02em;line-height:1.05;'
                    f'color:{CLASS_COLOR[pred]};margin:6px 0 14px">{pred}</div>', unsafe_allow_html=True)
        if res["stationary_rule_applied"]:
            st.markdown(f'<p class="gx-prose" style="color:{theme.MUTED}">{res["explanation"]}</p>',
                        unsafe_allow_html=True)
            return
        rows = ""
        for cls in config.CLASSES:
            p = res["probabilities"][cls]
            rows += (f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">'
                     f'<div style="font-size:13.5px;width:64px;color:{theme.BODY}">{cls}</div>'
                     f'<div style="flex:1;height:8px;background:{theme.BG};border-radius:4px;overflow:hidden">'
                     f'<div style="width:{100 * p:.0f}%;height:100%;background:{CLASS_COLOR[cls] if cls == pred else theme.BORDER_STRONG};border-radius:4px"></div></div>'
                     f'<div style="font-family:{theme.MONO};font-size:13px;color:{theme.BODY};width:46px;text-align:right">{p:.0%}</div></div>')
        st.markdown(rows, unsafe_allow_html=True)


def render(meta: dict, batch: bool = False, evidence: bool = True):
    theme.page_title("Batch run — Rail corrugation" if batch else meta["title"],
                     "Every uploaded recording classified in one pass, with the full prediction CSV ready to "
                     "download." if batch else meta["subtitle"])
    st.write("")
    upload_key = f"rail_upload_{'batch' if batch else 'single'}"
    files = st.file_uploader("Axle-box vibration recording (.csv)", type=["csv"], accept_multiple_files=batch,
                             key=upload_key, help="One second at 10 kHz: speed pulse plus 64 axle boxes × vibration and shock.")
    picked = [f for f in (files if batch else [files]) if f is not None]
    if picked:
        st.session_state["rail_files"] = [(f.name, f.getvalue()) for f in picked]
    uploads = st.session_state.get("rail_files", [])
    if not uploads:
        theme.banner("Waiting for a recording. Positions 1/3/5/7 sit on the Side I rail and 2/4/6/8 on Side II; "
                     "corrugation shows up as a vibration signature on one side only. A stationary train is "
                     "reported Normal by rule — it cannot generate the excitation.", icon="⬆")
        session.sample_button("rail")
        return

    results, failures = [], []
    for name, data in uploads:
        try:
            with st.spinner(f"Classifying {name}…"):
                results.append(process(data, name))
        except Exception as e:  # noqa: BLE001
            failures.append((name, f"could not read this file: {e}"))
    for name, msg in failures:
        st.error(f"{name} — {msg}")
    if not results:
        return

    preds = pd.DataFrame({"file_id": [r["file_id"] for r in results], "prediction": [r["prediction"] for r in results]})

    if batch:
        mix = preds.prediction.value_counts().to_dict()
        theme.banner(f"{len(results)} of {len(uploads)} files classified — " +
                     ", ".join(f"{k}: {v}" for k, v in mix.items()) + ".",
                     icon="✓" if not failures else "!", color=theme.ACCENT if not failures else theme.AMBER)
    r0 = results[session.inspect_picker("rail", [r["file_id"] for r in results]) if batch else 0]
    pred = r0["prediction"]
    conf = "rule" if r0["stationary_rule_applied"] else f"{r0['probabilities'][pred]:.0%}"
    if not batch:
        theme.banner(f"{r0['file_id']} accepted — 129 columns, 10 kHz, 1.0 s window. "
                     + (r0["explanation"] if r0["stationary_rule_applied"] else f"Classified {pred} with {conf} confidence."),
                     color=CLASS_COLOR[pred] if pred != "Normal" else theme.ACCENT, icon="!" if pred != "Normal" else "✓")

    theme.metrics([
        ("Prediction", pred, "stationary rule" if r0["stationary_rule_applied"] else "gradient-boosted classifier", CLASS_COLOR[pred]),
        ("Confidence", conf, "class probability" if conf != "rule" else "no wheel rotation detected", None),
        ("Recording speed", f"{r0['speed_mps'] * 3.6:.0f} km/h", f"{r0['speed_mps']:.1f} m/s from the pulse channel", None),
        ("Side asymmetry", f"{r0['asym']:+.3f}", "Side I − Side II vibration RMS", CLASS_COLOR[pred] if pred != "Normal" else None),
    ])

    left, right = st.columns([1, 1.4])
    with left:
        prediction_panel(r0)
    with right:
        with theme.panel("Axle-box vibration energy, 64 channels",
                         "Per-channel RMS over the 1 s window. Highlighted channels sit on the predicted rail side."):
            st.altair_chart(channel_chart(r0), use_container_width=True)

    if evidence and not r0["stationary_rule_applied"]:
        ref = _train_reference()
        asym = r0["asym"]
        nearest = (ref[HEADLINE] - asym).abs().idxmin()
        tiles = [
            ("Side asymmetry, this file", f"{asym:+.3f}", f"train medians: Normal {ref.loc['Normal', HEADLINE]:+.3f}, "
             f"Side I {ref.loc['Side I', HEADLINE]:+.3f}, Side II {ref.loc['Side II', HEADLINE]:+.3f}", CLASS_COLOR[pred]),
            ("Closest training class on asymmetry", nearest, "by median of the headline feature", CLASS_COLOR[nearest]),
            ("Speed vs fault cases", f"{r0['speed_mps'] * 3.6:.0f} km/h",
             f"fault files trained at {ref.loc['Side I', 'speed_mps'] * 3.6:.0f}–{ref.loc['Side II', 'speed_mps'] * 3.6:.0f} km/h median", None),
        ]
        prose = ("A positive asymmetry means the Side I axle boxes vibrate harder than Side II, negative the reverse. "
                 "The classifier uses 239 time- and frequency-domain features across both sides; the asymmetry "
                 "shown here is its single strongest input and is what a human inspector would look at first.")
        theme.evidence("Why this label", tiles, prose)

    rows = [[r["file_id"], theme.pill(r["prediction"], CLASS_COLOR[r["prediction"]]),
             "rule" if r["stationary_rule_applied"] else f"{r['probabilities'][r['prediction']]:.2f}",
             f"{r['speed_mps'] * 3.6:.0f}"] for r in results]
    theme.table(["file_id", "prediction", "confidence", "speed km/h"], rows, f"{meta['csv']} · {len(rows)} rows",
                "file_id, prediction", footer="only file_id and prediction are submitted; confidence and speed are informational.")
    csv_bytes = preds.to_csv(index=False).encode()
    session.record("rail", meta["csv"], csv_bytes, len(preds), preds.file_id)
    dl, rs, _ = st.columns([1.1, 0.6, 3])
    with dl:
        st.download_button(f"⬇  Download {meta['csv']}", csv_bytes,
                           file_name=meta["csv"], mime="text/csv", use_container_width=True)
    if rs.button("Reset", use_container_width=True, key="rail_reset"):
        st.session_state.pop("rail_files", None)
        st.session_state.pop(upload_key, None)
        st.rerun()
