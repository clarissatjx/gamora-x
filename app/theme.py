"""Design system for the Gamora CdM app.

Ported from the team's design comp (`Gamora CdM App.dc.html`): dark industrial
dashboard, cyan accent, Source Sans 3 + IBM Plex Mono.
"""
from contextlib import contextmanager

import streamlit as st

# --- palette, taken verbatim from the comp ---
BG = "#0E1117"
PANEL = "#161A23"
BORDER = "#262730"
BORDER_SOFT = "#1E222C"
BORDER_STRONG = "#3E4351"
BORDER_HOVER = "#6B7283"
TEXT = "#FAFAFA"
BODY = "#D6D9E3"
MUTED = "#A3A8B8"
FAINT = "#8B90A0"
DIM = "#5A6070"
GRID = "#363945"
IDLE_BAR = "#39404F"
ACCENT = "#2DBFCF"
ACCENT_HOVER = "#6FDCE8"
ACCENT_INK = "#08222A"
GREEN = "#2F9E68"
RED = "#E8595B"
AMBER = "#E0A22C"

SANS = "'Source Sans 3', system-ui, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, monospace"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {{
    background: {BG}; color: {TEXT};
    font-family: {SANS}; font-size: 15px; line-height: 1.45;
}}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stDecoration"] {{ display: none; }}
footer, #MainMenu {{ visibility: hidden; }}
.block-container {{ padding: 0 28px 56px 28px; max-width: 1320px; }}
::-webkit-scrollbar {{ width: 9px; height: 9px; }}
::-webkit-scrollbar-thumb {{ background: {GRID}; border-radius: 6px; }}
a {{ color: {ACCENT}; text-decoration: none; }}
a:hover {{ color: {ACCENT_HOVER}; text-decoration: underline; }}

/* ---------------- sidebar ---------------- */
[data-testid="stSidebar"] {{
    background: {PANEL}; border-right: 1px solid {BORDER}; width: 300px !important; }}
[data-testid="stSidebar"] > div {{ background: {PANEL}; }}
[data-testid="stSidebar"] .block-container {{ padding: 0; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.55rem; }}

.gx-brand {{ display:flex; align-items:center; gap:10px; margin-bottom:20px; }}
.gx-mark {{ width:30px; height:30px; border-radius:7px; background:{ACCENT}; flex-shrink:0;
    display:flex; align-items:center; justify-content:center;
    color:{BG}; font-weight:700; font-size:15px; }}
.gx-name {{ font-weight:700; font-size:16px; letter-spacing:-0.01em; color:{TEXT}; }}
.gx-kicker {{ font-size:10.5px; color:{FAINT}; font-family:{MONO}; white-space:nowrap; }}
.gx-label {{ font-size:12px; font-weight:600; color:{MUTED}; text-transform:uppercase;
    letter-spacing:0.07em; margin:14px 0 8px 0; }}

/* nav buttons: label left, mono metric tag right, status dot before */
[data-testid="stSidebar"] .stButton button {{
    all: unset; box-sizing:border-box; width:100%; cursor:pointer;
    padding:9px 12px; border-radius:7px; border:1px solid {BORDER};
    background:transparent; color:#C2C6D2; font-family:{SANS}; font-size:14px;
    margin-bottom:2px; transition:border-color 120ms ease; }}
[data-testid="stSidebar"] .stButton button:hover {{ border-color:{BORDER_STRONG}; }}
[data-testid="stSidebar"] .stButton button p {{
    display:flex; align-items:center; justify-content:space-between; gap:10px;
    margin:0; font-size:14px; width:100%; }}
[data-testid="stSidebar"] .stButton button p::before {{
    content:""; width:7px; height:7px; border-radius:50%; background:#4A4F5E;
    flex-shrink:0; margin-right:-4px; }}
[data-testid="stSidebar"] .stButton button code {{
    font-family:{MONO}; font-size:10.5px; color:{BORDER_HOVER};
    background:transparent; padding:0; flex-shrink:0; }}
[data-testid="stSidebar"] .stButton button[kind="primary"],
[data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] {{
    background:{BG}; border-color:{ACCENT}99; color:{TEXT}; }}
[data-testid="stSidebar"] .stButton button[kind="primary"] p::before,
[data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] p::before {{
    background:{ACCENT}; }}
[data-testid="stSidebar"] .stButton button[kind="primary"] code,
[data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] code {{
    color:{ACCENT}; }}

[data-testid="stSidebar"] [data-testid="stCheckbox"] label {{
    color:{BODY}; font-size:13.5px; }}
.gx-meta {{ margin-top:18px; padding-top:18px; border-top:1px solid {BORDER};
    font-family:{MONO}; font-size:11.5px; color:{FAINT}; }}
.gx-meta div {{ display:flex; justify-content:space-between; gap:12px; padding:3px 0; }}

/* ---------------- top bar ---------------- */
.gx-topbar {{ height:46px; border-bottom:1px solid {BORDER}; display:flex; align-items:center;
    justify-content:space-between; margin:0 -28px 26px -28px; padding:0 28px; background:{BG}; }}
.gx-crumb {{ font-family:{MONO}; font-size:12px; color:{FAINT}; }}
.gx-status {{ display:flex; align-items:center; gap:14px; font-size:12.5px; color:{FAINT}; }}
.gx-dot {{ width:7px; height:7px; border-radius:50%; display:inline-block; margin-right:6px; }}

/* ---------------- page header ---------------- */
.gx-h1 {{ margin:0 0 4px; font-size:27px; font-weight:700; letter-spacing:-0.02em; color:{TEXT}; }}
.gx-sub {{ margin:0; color:{MUTED}; font-size:14.5px; max-width:64ch; }}

/* ---------------- banner ---------------- */
.gx-banner {{ display:flex; gap:14px; align-items:center; background:{PANEL};
    border:1px solid {BORDER}; border-left:3px solid {ACCENT}; border-radius:8px;
    padding:13px 16px; margin-bottom:22px; }}
.gx-banner-i {{ font-family:{MONO}; font-size:13px; color:{ACCENT}; flex-shrink:0; }}
.gx-banner-t {{ font-size:13.5px; color:{BODY}; }}

/* ---------------- metric cards ---------------- */
.gx-metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
    gap:14px; margin-bottom:22px; }}
.gx-metric {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:8px; padding:15px 17px; }}
.gx-metric-l {{ font-size:12.5px; color:{MUTED}; text-transform:uppercase; letter-spacing:0.06em;
    font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.gx-metric-v {{ font-family:{MONO}; font-size:25px; font-weight:600; letter-spacing:-0.01em;
    margin:4px 0 2px; }}
.gx-metric-n {{ font-size:12.5px; color:{FAINT}; font-family:{MONO}; }}

/* ---------------- panels ---------------- */
[data-testid="stVerticalBlockBorderWrapper"]:has(
    > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"]
    > [data-testid="stMarkdown"] > [data-testid="stMarkdownContainer"] > .gx-panel-h) {{
    background:{PANEL}; border:1px solid {BORDER}; border-radius:9px;
    padding:18px 20px 14px 20px; margin-bottom:22px; }}
.gx-panel-h {{ font-size:15.5px; font-weight:600; color:{TEXT}; }}
.gx-panel-s {{ font-size:13px; color:{MUTED}; margin-top:2px; }}
.gx-axis {{ display:flex; justify-content:space-between; font-family:{MONO};
    font-size:11.5px; color:{FAINT}; }}

/* evidence tiles (nested inside a panel) */
.gx-ev {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:12px; }}
.gx-ev-card {{ background:{BG}; border:1px solid {BORDER}; border-radius:8px; padding:13px 15px; }}
.gx-ev-l {{ font-size:13px; color:{MUTED}; }}
.gx-ev-v {{ font-family:{MONO}; font-size:19px; font-weight:600; margin:3px 0; }}
.gx-ev-b {{ font-size:12.5px; color:{FAINT}; font-family:{MONO}; }}
.gx-prose {{ margin:0; font-size:13.5px; color:{BODY}; }}

/* ---------------- data table ---------------- */
.gx-table-wrap {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:9px;
    overflow:hidden; margin-bottom:14px; }}
.gx-table-head {{ padding:15px 20px; border-bottom:1px solid {BORDER}; display:flex;
    flex-wrap:wrap; justify-content:space-between; gap:10px; align-items:center; }}
.gx-table-scroll {{ overflow:auto; max-height:420px; }}
table.gx {{ width:100%; border-collapse:collapse; font-family:{MONO}; font-size:13px; }}
table.gx thead th {{ position:sticky; top:0; background:{BG}; color:{MUTED}; text-align:left;
    font-weight:600; padding:10px 14px; border-bottom:1px solid {BORDER}; }}
table.gx thead th:first-child, table.gx tbody td:first-child {{ padding-left:20px; }}
table.gx thead th:last-child, table.gx tbody td:last-child {{ padding-right:20px; text-align:right; }}
table.gx tbody td {{ padding:9px 14px; color:{BODY}; border-bottom:1px solid {BORDER_SOFT}; }}
.gx-foot {{ padding:13px 20px; border-top:1px solid {BORDER}; font-size:12.5px;
    color:{FAINT}; font-family:{MONO}; }}

/* ---------------- dropzone + subsystem cards ---------------- */
.gx-card {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:9px; padding:18px;
    display:flex; flex-direction:column; gap:10px; height:100%; box-sizing:border-box; }}
.gx-card-t {{ display:flex; align-items:center; justify-content:space-between; gap:10px; }}
.gx-card-n {{ font-size:16px; font-weight:700; color:{TEXT}; }}
.gx-chip {{ font-family:{MONO}; font-size:11.5px; color:{ACCENT}; background:{BG};
    border:1px solid {BORDER}; border-radius:20px; padding:3px 9px; white-space:nowrap; }}
.gx-card-task {{ font-size:13.5px; color:{MUTED}; flex:1; }}
.gx-card-out {{ font-family:{MONO}; font-size:12px; color:{FAINT}; padding-top:10px;
    border-top:1px solid {BORDER}; }}

/* ---------------- streamlit widgets ---------------- */
[data-testid="stFileUploader"] section {{
    background:{PANEL}; border:2px dashed {BORDER_STRONG}; border-radius:10px; padding:26px; }}
[data-testid="stFileUploader"] section:hover {{ border-color:{ACCENT}; }}
[data-testid="stFileUploader"] small {{ color:{MUTED}; }}
[data-testid="stFileUploaderDropzoneInstructions"] span {{ color:{TEXT}; font-weight:600; }}
[data-testid="stDownloadButton"] button {{
    background:{ACCENT}; border:1px solid {ACCENT}; color:{ACCENT_INK}; border-radius:7px;
    padding:9px 16px; font-family:{SANS}; font-size:13.5px; font-weight:600; }}
[data-testid="stDownloadButton"] button:hover {{
    background:{ACCENT_HOVER}; border-color:{ACCENT_HOVER}; color:{ACCENT_INK}; }}
.block-container .stButton button {{
    background:transparent; border:1px solid {BORDER_STRONG}; color:{BODY};
    border-radius:7px; padding:9px 15px; font-family:{SANS}; font-size:13.5px; }}
.block-container .stButton button:hover {{ border-color:{BORDER_HOVER}; color:{TEXT}; }}
[data-testid="stAlert"] {{ border-radius:8px; font-size:13.5px; }}
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)


def brand():
    st.markdown(
        f'<div class="gx-brand"><div class="gx-mark">g</div><div>'
        f'<div class="gx-name">gamora · CdM</div>'
        f'<div class="gx-kicker">PS3 · Train Condition Monitoring</div></div></div>',
        unsafe_allow_html=True,
    )


def label(text: str):
    st.markdown(f'<div class="gx-label">{text}</div>', unsafe_allow_html=True)


def sidebar_meta(rows):
    body = "".join(
        f'<div><span>{k}</span><span style="color:{c or BODY}">{v}</span></div>'
        for k, v, c in rows
    )
    st.markdown(f'<div class="gx-meta">{body}</div>', unsafe_allow_html=True)


def topbar(crumb: str, models_loaded: int, total: int):
    ok = models_loaded > 0
    st.markdown(
        f'<div class="gx-topbar"><div class="gx-crumb">gamora-x / app / {crumb}</div>'
        f'<div class="gx-status"><span><span class="gx-dot" '
        f'style="background:{GREEN if ok else AMBER}"></span>'
        f'{models_loaded} of {total} models loaded</span>'
        f'<span style="font-family:{MONO}">⋮</span></div></div>',
        unsafe_allow_html=True,
    )


def page_title(title: str, subtitle: str):
    st.markdown(
        f'<h1 class="gx-h1">{title}</h1><p class="gx-sub">{subtitle}</p>',
        unsafe_allow_html=True,
    )


def banner(text: str, icon: str = "✓", color: str = ACCENT):
    st.markdown(
        f'<div class="gx-banner" style="border-left-color:{color}">'
        f'<span class="gx-banner-i" style="color:{color}">{icon}</span>'
        f'<span class="gx-banner-t">{text}</span></div>',
        unsafe_allow_html=True,
    )


def metrics(items):
    """items: iterable of (label, value, note, color|None)."""
    cards = "".join(
        f'<div class="gx-metric"><div class="gx-metric-l">{lab}</div>'
        f'<div class="gx-metric-v" style="color:{col or TEXT}">{val}</div>'
        f'<div class="gx-metric-n">{note}</div></div>'
        for lab, val, note, col in items
    )
    st.markdown(f'<div class="gx-metrics">{cards}</div>', unsafe_allow_html=True)


@contextmanager
def panel(heading: str, sub: str = "", right: str = ""):
    with st.container(border=True):
        s = f'<div class="gx-panel-s">{sub}</div>' if sub else ""
        head = (f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;'
                f'align-items:baseline;gap:12px"><div class="gx-panel-h">{heading}</div>'
                f'{right}</div>{s}')
        st.markdown(head, unsafe_allow_html=True)
        yield


def legend(items):
    """Static legend for a panel header: iterable of (label, color)."""
    dots = "".join(
        f'<span style="display:flex;align-items:center;gap:6px">'
        f'<span style="width:10px;height:10px;border-radius:2px;background:{c};'
        f'display:inline-block"></span>{lab}</span>'
        for lab, c in items
    )
    return f'<div style="display:flex;gap:16px;font-size:12.5px;color:{MUTED}">{dots}</div>'


def axis(left: str, right: str):
    st.markdown(
        f'<div class="gx-axis"><span>{left}</span><span>{right}</span></div>',
        unsafe_allow_html=True,
    )


def pill(text: str, color: str) -> str:
    return (f'<span style="font-family:{MONO};font-size:12px;font-weight:600;color:{color};'
            f'border:1px solid {color}44;background:{color}1a;border-radius:20px;'
            f'padding:3px 9px;white-space:nowrap">{text}</span>')


def evidence(title: str, tiles, prose: str):
    """tiles: iterable of (label, value, baseline, color)."""
    cards = "".join(
        f'<div class="gx-ev-card"><div class="gx-ev-l">{lab}</div>'
        f'<div class="gx-ev-v" style="color:{col}">{val}</div>'
        f'<div class="gx-ev-b">{base}</div></div>'
        for lab, val, base, col in tiles
    )
    with panel(title):
        st.markdown(f'<div class="gx-ev">{cards}</div>'
                    f'<p class="gx-prose" style="margin-top:12px">{prose}</p>',
                    unsafe_allow_html=True)


def table(headers, rows, title: str, schema: str, footer: str = ""):
    """rows: list of lists; cells may contain HTML (e.g. pill())."""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    foot = f'<div class="gx-foot">{footer}</div>' if footer else ""
    st.markdown(
        f'<div class="gx-table-wrap"><div class="gx-table-head">'
        f'<div class="gx-panel-h">{title}</div>'
        f'<div style="font-family:{MONO};font-size:12px;color:{FAINT}">{schema}</div></div>'
        f'<div class="gx-table-scroll"><table class="gx"><thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody></table></div>{foot}</div>',
        unsafe_allow_html=True,
    )


def style_chart(chart):
    return (
        chart.configure_view(strokeWidth=0, fill=PANEL)
        .configure(background=PANEL)
        .configure_axis(
            grid=False, domainColor=GRID, tickColor=GRID,
            labelColor=FAINT, labelFont="IBM Plex Mono", labelFontSize=11,
            titleColor=MUTED, titleFont="Source Sans 3", titleFontSize=12,
            titleFontWeight=400, titlePadding=10,
        )
        .configure_legend(
            labelFont="Source Sans 3", labelFontSize=12.5, labelColor=MUTED,
            titleColor=FAINT, symbolType="square", symbolSize=110,
            orient="top-right", direction="horizontal", offset=2,
        )
    )
