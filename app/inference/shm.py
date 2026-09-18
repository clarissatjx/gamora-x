import io

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import theme
from subsystems.shm.loader import load_series
from subsystems.shm.predict import analyse, load_model

N_HIST_BINS = 10
SHARE_HIGHLIGHT = 0.15


@st.cache_resource
def bundle():
    return load_model()


def meta_rows():
    """Sidebar model metadata, read from the trained bundle."""
    try:
        b = bundle()
    except Exception:  # noqa: BLE001 - bundle missing until train.py has run
        return [("model", "—", None), ("version", "—", None), ("val score", "—", None),
                ("split", "leave-one-out", None)]
    use = b["use_correction"]
    score = b["loo_corrected"] if use else b["loo_analytic"]
    return [
        ("model", "Miner m=5" + (" + ridge" if use else ""), None),
        ("version", "shm-v1", None),
        ("val score", f"{score:.3f} (1−MAPE)", theme.ACCENT),
        ("split", "leave-one-out, 64", None),
    ]


def process(file):
    x = load_series(file)
    return x, analyse(x, bundle())


def _top_excursions(x: np.ndarray, k: int = 8, min_gap_frac: float = 0.02) -> np.ndarray:
    """Indices of the k largest excursions from the mean, taken at distinct turning points
    at least `min_gap_frac` of the series apart, so the rings don't pile up in one trough."""
    d = np.diff(x)
    turning = np.nonzero(np.sign(d[1:]) != np.sign(d[:-1]))[0] + 1
    order = turning[np.argsort(np.abs(x[turning] - x.mean()))[::-1]]
    chosen, gap = [], int(len(x) * min_gap_frac)
    for i in order:
        if all(abs(i - j) >= gap for j in chosen):
            chosen.append(int(i))
        if len(chosen) == k:
            break
    return np.array(chosen)


def series_chart(x: np.ndarray, res: dict):
    alt.data_transformers.disable_max_rows()
    c = theme.chart_colors()
    step = max(1, len(x) // 6000)
    trace = pd.DataFrame({"i": np.arange(0, len(x), step), "stress": x[::step]})
    peaks = pd.DataFrame({"i": _top_excursions(x), "stress": x[_top_excursions(x)]})
    line = alt.Chart(trace).mark_line(strokeWidth=1.0, color=c["accent"]).encode(
        x=alt.X("i:Q", title="sample", axis=alt.Axis(labels=False, ticks=False, domain=False)),
        y=alt.Y("stress:Q", title="stress"),
    )
    mean = alt.Chart(pd.DataFrame({"y": [float(x.mean())]})).mark_rule(
        strokeDash=[3, 3], color=c["grid"]).encode(y="y:Q")
    dots = alt.Chart(peaks).mark_point(size=60, strokeWidth=1.6, color=c["amber"], fill="transparent").encode(
        x="i:Q", y="stress:Q", tooltip=[alt.Tooltip("stress:Q", format=".1f")])
    return theme.style_chart(alt.layer(mean, line, dots).properties(height=200))


def histogram(res: dict):
    c = theme.chart_colors()
    rng, cnt, share = res["rng"], res["cnt"], res["contrib_share"]
    edges = np.linspace(0, rng.max() * 1.0001, N_HIST_BINS + 1)
    which = np.clip(np.digitize(rng, edges) - 1, 0, N_HIST_BINS - 1)
    rows = []
    for b in range(N_HIST_BINS):
        m = which == b
        rows.append({"bin": f"{edges[b]:.0f}–{edges[b + 1]:.0f}", "order": b,
                     "cycles": float(cnt[m].sum()), "share": float(share[m].sum())})
    df = pd.DataFrame(rows)
    df["hot"] = df.share >= SHARE_HIGHLIGHT
    bars = alt.Chart(df).mark_bar(cornerRadius=2).encode(
        x=alt.X("bin:N", sort=alt.SortField("order"), title="stress range", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("share:Q", title="share of damage", axis=alt.Axis(format="%")),
        color=alt.condition("datum.hot", alt.value(c["amber"]), alt.value(c["idle_bar"])),
        tooltip=[alt.Tooltip("bin:N", title="range"), alt.Tooltip("cycles:Q", format=",.0f"),
                 alt.Tooltip("share:Q", format=".1%", title="damage share")],
    )
    return theme.style_chart(bars.properties(height=190)), df


def steps_panel(res: dict, b: dict):
    rows = [
        ("Rainflow cycles counted", f"{res['n_cycles']:,.0f}"),
        (f"Analytic Miner sum, S₅ / C", f"{res['analytic']:.4f}"),
        ("Regressor correction", f"×{res['correction_factor']:.3f}" if b["use_correction"] else "off"),
        ("Reported damage", f"{res['damage']:.4f}"),
    ]
    body = "".join(
        f'<div style="display:flex;justify-content:space-between;gap:12px;padding:9px 0;'
        f'border-bottom:1px solid {theme.BORDER_SOFT}">'
        f'<span style="font-size:13.5px;color:{theme.BODY}">{k}</span>'
        f'<span style="font-family:{theme.MONO};font-size:13.5px;color:{theme.ACCENT}">{v}</span></div>'
        for k, v in rows
    )
    with theme.panel("How the damage value was built"):
        st.markdown(body + (
            f'<p class="gx-prose" style="margin-top:12px;color:{theme.MUTED}">Palmgren–Miner '
            f'summation over rainflow-counted stress ranges with S-N exponent m = 5, the exponent '
            f'recovered from the 64 labelled training files (log-log slope 0.997). The scale C is '
            f'fitted once; the ridge term corrects small residual differences and is capped at ±20%.'
            f'</p>'), unsafe_allow_html=True)


def render(meta: dict, batch: bool = False, evidence: bool = True):
    theme.page_title(
        "Batch run — SHM" if batch else meta["title"],
        "Every uploaded stress segment scored in one pass, with the combined prediction CSV ready "
        "to download." if batch else meta["subtitle"],
    )
    st.write("")
    upload_key = f"shm_upload_{'batch' if batch else 'single'}"
    files = st.file_uploader(
        "Dynamic stress segment (.csv, one headerless column)", type=["csv"],
        accept_multiple_files=batch, key=upload_key,
        help="One measurement point's stress time series. Upload several in Batch mode.",
    )
    picked = [f for f in (files if batch else [files]) if f is not None]
    if picked:
        st.session_state["shm_files"] = [(f.name, f.getvalue()) for f in picked]
    uploads = st.session_state.get("shm_files", [])

    if not uploads:
        theme.banner(
            "Waiting for a stress segment. The model counts every load cycle in the recording "
            "with rainflow counting, sums their fatigue contribution, and reports a single "
            "cumulative-damage number — 1.0 would mean the fatigue life is used up.",
            icon="⬆",
        )
        return

    b = bundle()
    results, failures = [], []
    for name, data in uploads:
        try:
            x, res = process(io.BytesIO(data))
        except ValueError as e:
            failures.append((name, str(e)))
            continue
        except Exception as e:  # noqa: BLE001
            failures.append((name, f"could not read this file: {e}"))
            continue
        results.append((name, x, res))
    for name, msg in failures:
        st.error(f"{name} — {msg}")
    if not results:
        return

    name0, x0, r0 = results[0]
    preds = pd.DataFrame({"file_id": [n for n, _, _ in results],
                          "prediction": [r["damage"] for _, _, r in results]})
    if batch:
        theme.banner(f"{len(results)} of {len(uploads)} files parsed successfully — damage "
                     f"{preds.prediction.min():.4f} to {preds.prediction.max():.4f}.",
                     icon="✓" if not failures else "!", color=theme.ACCENT if not failures else theme.AMBER)
    else:
        theme.banner(f"{name0} accepted — {len(x0):,} samples, {r0['n_reversals']:,} reversals, "
                     f"{r0['n_cycles']:,.0f} rainflow cycles. Damage estimated.")

    train_d = b["train_damage"]
    pct = float((train_d < r0["damage"]).mean())
    theme.metrics([
        ("Cumulative damage", f"{r0['damage']:.4f}", "Palmgren–Miner, dimensionless", theme.ACCENT),
        ("Rainflow cycles", f"{r0['n_cycles']:,.0f}", f"{r0['n_reversals']:,} reversals", None),
        ("Peak stress range", f"{r0['max_range']:.1f}", "largest single cycle", None),
        ("Vs training set", f"P{pct * 100:.0f}", f"{'above' if pct > 0.5 else 'below'} median of 64 files",
         theme.AMBER if pct > 0.9 else None),
    ])

    with theme.panel("Dynamic stress time series",
                     right=f'<span style="font-family:{theme.MONO};font-size:12px;color:{theme.FAINT}">'
                           f'{name0} · {len(x0):,} samples</span>'):
        st.altair_chart(series_chart(x0, r0), use_container_width=True)
        theme.axis("0", f"{len(x0):,} samples")
        st.markdown(f'<div style="font-size:12.5px;color:{theme.FAINT};margin-top:8px">Amber rings mark '
                    f'the eight largest excursions from the mean — with an S-N exponent of 5, a handful '
                    f'of such cycles carries most of the damage.{" Showing the first uploaded file." if batch else ""}'
                    f'</div>', unsafe_allow_html=True)

    if evidence:
        left, right = st.columns([1.15, 1])
        with left:
            with theme.panel("Rainflow cycle histogram", "Share of total damage by stress-range bin."):
                chart, df = histogram(r0)
                st.altair_chart(chart, use_container_width=True)
                hot = df[df.hot]
                st.markdown(f'<div style="font-size:12.5px;color:{theme.FAINT}">Amber bins each carry '
                            f'≥{SHARE_HIGHLIGHT:.0%} of the damage: {", ".join(hot.bin)} — '
                            f'{hot.cycles.sum():,.0f} of {df.cycles.sum():,.0f} cycles.</div>',
                            unsafe_allow_html=True)
        with right:
            steps_panel(r0, b)

    rows = [[n, f"{r['damage']:.6f}"] for n, _, r in results]
    theme.table(["file_id", "prediction"], rows, f"{meta['csv']} · {len(rows)} rows",
                "file_id, prediction",
                footer="prediction is the cumulative fatigue damage; 1.0 = fatigue life consumed.")
    dl, rs, _ = st.columns([1.1, 0.6, 3])
    with dl:
        st.download_button(f"⬇  Download {meta['csv']}", preds.to_csv(index=False).encode(),
                           file_name=meta["csv"], mime="text/csv", use_container_width=True)
    if rs.button("Reset", use_container_width=True, key="shm_reset"):
        st.session_state.pop("shm_files", None)
        st.session_state.pop(upload_key, None)
        st.rerun()
