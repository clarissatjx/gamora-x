import io

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import session
import theme
from inference.acv import DEFAULT_METHOD
from subsystems.acv.features import extract_features, load_case
from subsystems.acv.rank import COOLING_MODES, MODE_PARAM, TEMP_PAIRS, heuristic_scores, physics_gap, score_cars

CHART_POINTS = 400
SMOOTH = 20  # samples (~10 min at 30 s)


def _gap_series(case_df: pd.DataFrame):
    """Per-car (cabin - setpoint) over cooling-mode timestamps, for the chart."""
    params = set(case_df["param"].unique())
    pair = next((p for p in TEMP_PAIRS if set(p) <= params), None)
    if pair is None:
        return None

    def wide(p):
        w = case_df[case_df["param"] == p].pivot(index="Time", columns="car_id", values="value")
        return w.apply(pd.to_numeric, errors="coerce")

    gap = wide(pair[0]) - wide(pair[1])
    if MODE_PARAM in params:
        mode = case_df[case_df["param"] == MODE_PARAM].pivot(index="Time", columns="car_id", values="value")
        cool = mode.astype(str).isin(COOLING_MODES).reindex(index=gap.index, columns=gap.columns).fillna(False)
        if cool.to_numpy().any():
            gap = gap.where(cool)
    return gap


def process(data: bytes, name: str) -> dict:
    case_df = load_case(io.BytesIO(data))
    feats = extract_features(case_df)
    gap = physics_gap(case_df)
    ranked, scores = score_cars(feats, method=DEFAULT_METHOD, gap=gap)
    heur = heuristic_scores(feats).reindex(feats.index)
    series = _gap_series(case_df)
    cool_frac = None
    if series is not None:
        hottest = series.eq(series.max(axis=1), axis=0) & series.notna()
        cool_frac = hottest.sum() / max(int(series.notna().any(axis=1).sum()), 1)
    return {
        "file_id": name, "ranked": ranked, "scores": scores, "gap": gap, "heuristic": heur,
        "series": series, "hottest_frac": cool_frac,
        "hours": (case_df["Time"].max() - case_df["Time"].min()).total_seconds() / 3600,
        "n_rows": int(case_df.attrs.get("n_rows_raw", 0)),
    }


def ranking_panel(res: dict):
    scores = res["scores"]
    lo, hi = float(scores.min()), float(scores.max())
    rows = ""
    for i, (car, s) in enumerate(scores.items(), start=1):
        pct = 100 * (s - lo) / (hi - lo) if hi > lo else 0
        color = theme.RED if i == 1 else (theme.ACCENT if i <= 3 else theme.BORDER_STRONG)
        rows += (
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:9px">'
            f'<div style="font-family:{theme.MONO};font-size:12px;color:{theme.FAINT};width:22px">{i:02d}</div>'
            f'<div style="font-family:{theme.MONO};font-size:14px;font-weight:600;width:28px;color:{theme.TEXT}">{car}</div>'
            f'<div style="flex:1;height:22px;background:{theme.BG};border-radius:4px;overflow:hidden">'
            f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:4px"></div></div>'
            f'<div style="font-family:{theme.MONO};font-size:13px;color:{theme.BODY};width:52px;text-align:right">{s:+.2f}</div>'
            f'</div>'
        )
    with theme.panel("Ranked cars — most to least likely leak"):
        st.markdown(rows + (
            f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid {theme.BORDER};'
            f'font-family:{theme.MONO};font-size:12.5px;color:{theme.FAINT};word-break:break-all">'
            f'ranked_cars = {"|".join(res["ranked"])}</div>'), unsafe_allow_html=True)


def gap_chart(res: dict):
    c = theme.chart_colors()
    series = res["series"]
    top = res["ranked"][0]
    sm = series.rolling(SMOOTH, min_periods=1).mean()
    step = max(1, len(sm) // CHART_POINTS)
    sm = sm.iloc[::step]
    long = sm.reset_index(drop=True).reset_index().melt(id_vars="index", var_name="car", value_name="gap").dropna()
    long["is_top"] = long.car == top
    base = alt.Chart(long).encode(x=alt.X("index:Q", title=None, axis=alt.Axis(labels=False, ticks=False, domain=False)))
    others = base.transform_filter("!datum.is_top").mark_line(strokeWidth=1.1, color=c["border_strong"], opacity=0.9).encode(
        y=alt.Y("gap:Q", title="cabin − setpoint (°C)"), detail="car:N", tooltip=["car:N", alt.Tooltip("gap:Q", format=".2f")])
    lead = base.transform_filter("datum.is_top").mark_line(strokeWidth=2.1, color=c["red"]).encode(
        y="gap:Q", tooltip=["car:N", alt.Tooltip("gap:Q", format=".2f")])
    zero = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(strokeDash=[4, 4], color=c["dim"]).encode(y="y:Q")
    return theme.style_chart(alt.layer(zero, others, lead).properties(height=190))


def render(meta: dict, batch: bool = False, evidence: bool = True):
    theme.page_title("Batch run — ACV" if batch else meta["title"],
                     "Every uploaded case workbook ranked in one pass." if batch else meta["subtitle"])
    st.write("")
    upload_key = f"acv_upload_{'batch' if batch else 'single'}"
    files = st.file_uploader("ACV telemetry workbook (.xlsx)", type=["xlsx"], accept_multiple_files=batch,
                             key=upload_key, help="One train's ACV telemetry for all 8 cars, sampled every 30 s.")
    picked = [f for f in (files if batch else [files]) if f is not None]
    if picked:
        st.session_state["acv_files"] = [(f.name, f.getvalue()) for f in picked]
    uploads = st.session_state.get("acv_files", [])
    if not uploads:
        theme.banner("Waiting for a workbook. Each car is compared with its 7 neighbours on the same train: a "
                     "unit losing refrigerant cannot pull its cabin down to the cooling setpoint, and that gap "
                     "is what the ranking is built on.", icon="⬆")
        session.sample_button("acv")
        return

    results, failures = [], []
    for name, data in uploads:
        try:
            with st.spinner(f"Ranking {name}…"):
                results.append(process(data, name))
        except ValueError as e:
            failures.append((name, str(e)))
        except Exception as e:  # noqa: BLE001
            failures.append((name, f"could not read this file: {e}"))
    for name, msg in failures:
        st.error(f"{name} — {msg}")
    if not results:
        return

    preds = pd.DataFrame({"file_id": [r["file_id"] for r in results],
                          "ranked_cars": ["|".join(r["ranked"]) for r in results]})

    if batch:
        theme.banner(f"{len(results)} of {len(uploads)} workbooks ranked.", icon="✓" if not failures else "!",
                     color=theme.ACCENT if not failures else theme.AMBER)
    r0 = results[session.inspect_picker("acv", [r["file_id"] for r in results]) if batch else 0]
    top, runner = r0["ranked"][0], r0["ranked"][1]
    margin = float(r0["scores"].iloc[0] - r0["scores"].iloc[1])
    if not batch:
        theme.banner(f"{r0['file_id']} accepted — {len(r0['ranked'])} cars, {r0['n_rows']:,} timestamps over "
                     f"{r0['hours']:.1f} h. Ranking complete: car {top} most likely faulty.")

    gap_top = r0["gap"].get(top, np.nan)
    theme.metrics([
        ("Most likely faulty", f"Car {top}", f"blend score {r0['scores'].iloc[0]:+.2f}", theme.RED),
        ("Cars evaluated", str(len(r0["ranked"])), "IDs read from column headers", None),
        ("Margin to rank 2", f"{margin:.2f}", f"car {runner} scores {r0['scores'].iloc[1]:+.2f}", None),
        ("Cabin above setpoint", "—" if np.isnan(gap_top) else f"{gap_top:+.2f} °C",
         "car " + top + ", cooling mode", theme.RED if gap_top > 0 else None),
    ])

    left, right = st.columns([1, 1.15])
    with left:
        ranking_panel(r0)
    with right:
        if r0["series"] is not None:
            with theme.panel("Cabin temperature vs setpoint, cooling mode",
                             right=f'<span style="font-family:{theme.MONO};font-size:11.5px;color:{theme.RED}">'
                                   f'car {top} — {gap_top:+.2f} °C vs setpoint</span>'):
                st.altair_chart(gap_chart(r0), use_container_width=True)
                theme.axis("start", f"{r0['hours']:.0f} h")
                st.markdown(f'<div style="font-size:12.5px;color:{theme.FAINT};margin-top:6px">Dashed line is the '
                            f'setpoint. Red is the top-ranked car; every other car is grey. Smoothed over '
                            f'{SMOOTH * 30 // 60} min.</div>', unsafe_allow_html=True)
        else:
            with theme.panel("Cabin temperature vs setpoint"):
                st.markdown(f'<p class="gx-prose" style="color:{theme.MUTED}">This workbook carries no cabin-temperature '
                            f'channel, so the ranking comes from the peer-deviation heuristic alone.</p>',
                            unsafe_allow_html=True)

    if evidence:
        fleet_gap = float(r0["gap"].median()) if r0["gap"].notna().any() else np.nan
        hot = r0["hottest_frac"].get(top, np.nan) if r0["hottest_frac"] is not None else np.nan
        h_top, h_med = float(r0["heuristic"].get(top, np.nan)), float(r0["heuristic"].median())
        tiles = [
            ("Cabin-to-fleet gap", "—" if np.isnan(gap_top) else f"{gap_top - fleet_gap:+.2f} °C",
             f"fleet median {fleet_gap:+.2f} °C" if not np.isnan(fleet_gap) else "no cabin data", theme.RED),
            ("Share of cooling time as hottest car", "—" if np.isnan(hot) else f"{hot:.0%}", "1 in 8 would be 12%", theme.RED),
            ("Peer-deviation heuristic", f"{h_top:.2f}", f"fleet median {h_med:.2f}", theme.ACCENT),
        ]
        prose = (f"Car {top} holds the largest cabin-to-setpoint gap of the eight cars while in cooling mode"
                 + (f", and is the hottest car {hot:.0%} of the time" if not np.isnan(hot) else "")
                 + " — the signature of lost refrigerant charge. The ranking averages that physical measurement "
                 f"with a peer-deviation score across all telemetry channels; car {runner} is next.")
        theme.evidence("Evidence behind the ranking", tiles, prose)

    rows = [[r["file_id"], f'<span style="font-family:{theme.MONO}">{"|".join(r["ranked"])}</span>',
             theme.pill(f"car {r['ranked'][0]}", theme.RED)] for r in results]
    theme.table(["file_id", "ranked_cars", "top pick"], rows, f"{meta['csv']} · {len(rows)} rows",
                "file_id, ranked_cars", footer="ranked_cars uses each car's ID exactly as it appears in the workbook headers.")
    csv_bytes = preds.to_csv(index=False).encode()
    session.record("acv", meta["csv"], csv_bytes, len(preds), preds.file_id)
    dl, rs, _ = st.columns([1.1, 0.6, 3])
    with dl:
        st.download_button(f"⬇  Download {meta['csv']}", csv_bytes,
                           file_name=meta["csv"], mime="text/csv", use_container_width=True)
    if rs.button("Reset", use_container_width=True, key="acv_reset"):
        st.session_state.pop("acv_files", None)
        st.session_state.pop(upload_key, None)
        st.rerun()
