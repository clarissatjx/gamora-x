"""Design system for the Gamora condition-monitoring app.

Tokens mirror the team's design comp: light industrial dashboard, dark sidebar,
indigo accent, IBM Plex Sans/Mono, red/amber/green severity scale.
"""
from contextlib import contextmanager

import streamlit as st

BG = "#f6f6f9"
PANEL = "#ffffff"
INK = "#1a1a21"
MUTED = "#686870"
FAINT = "#97979e"
LINE = "#e6e6ea"
SIDEBAR = "#13131c"
SIDEBAR_2 = "#1e1e29"
ACCENT = "#645fdf"
ACCENT_HOVER = "#4f42c9"
ACCENT_SOFT = "#eeeeff"
HIGH = "#e6424c"
MED = "#ef9d32"
LOW = "#25b27d"

SANS = "'IBM Plex Sans', system-ui, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, monospace"

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {{
    font-family: {SANS};
    background: {BG};
    color: {INK};
    font-size: 14px;
}}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stDecoration"] {{ display: none; }}
footer, #MainMenu {{ visibility: hidden; }}
.block-container {{ padding: 1.6rem 2rem 3rem 2rem; max-width: 1240px; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{ background: {SIDEBAR}; width: 254px !important; }}
[data-testid="stSidebar"] > div {{ background: {SIDEBAR}; }}
[data-testid="stSidebar"] * {{ color: #cdd3dc; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
[data-testid="stSidebarCollapsedControl"] svg {{ color: {INK}; }}

.gx-brand {{ display:flex; align-items:center; gap:11px; padding: 6px 4px 18px 4px;
    border-bottom: 1px solid rgba(255,255,255,0.07); margin-bottom: 14px; }}
.gx-mark {{ width:30px; height:30px; border-radius:7px; background:{ACCENT};
    display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
.gx-mark i {{ width:11px; height:11px; background:#fff; transform:rotate(45deg);
    border-radius:2px; display:block; }}
.gx-wordmark {{ font-weight:700; letter-spacing:0.16em; font-size:15px; color:#fff; line-height:1.15; }}
.gx-tagline {{ font-family:{MONO}; font-size:10px; letter-spacing:0.06em; color:#7c8593; }}
.gx-navlabel {{ font-family:{MONO}; font-size:10px; letter-spacing:0.1em; color:#5f6773;
    padding: 4px 4px 6px 4px; }}

/* sidebar nav buttons */
[data-testid="stSidebar"] .stButton button {{
    all: unset; box-sizing: border-box; cursor: pointer; width: 100%;
    display:flex; align-items:center; padding: 9px 12px; border-radius: 8px;
    font-family:{SANS}; font-weight:500; font-size:13.5px; color:#9aa2ad;
    position: relative; margin-bottom: 2px; transition: background 120ms ease;
}}
[data-testid="stSidebar"] .stButton button:hover {{ background: rgba(255,255,255,0.05); color:#e6e8ec; }}
[data-testid="stSidebar"] .stButton button[kind="primary"],
[data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] {{
    background: rgba(255,255,255,0.07); color: #ffffff;
    box-shadow: inset 3px 0 0 0 {ACCENT};
}}
[data-testid="stSidebar"] .stButton button p {{ font-size:13.5px; font-weight:500; margin:0; }}

.gx-sidefoot {{ border-top:1px solid rgba(255,255,255,0.07); margin-top:16px; padding:14px 4px 4px 4px;
    font-family:{MONO}; font-size:11px; color:#7c8593; line-height:1.7; }}
.gx-dot {{ width:7px; height:7px; border-radius:50%; display:inline-block; margin-right:7px; }}

/* ---------- page header ---------- */
.gx-header {{ display:flex; align-items:flex-start; justify-content:space-between;
    gap:18px; flex-wrap:wrap; padding-bottom:16px; border-bottom:1px solid {LINE}; margin-bottom:22px; }}
.gx-title {{ font-size:19px; font-weight:600; letter-spacing:-0.01em; color:{INK}; }}
.gx-sub {{ color:{MUTED}; font-size:12.5px; margin-top:3px; max-width:62ch; line-height:1.5; }}
.gx-kpis {{ display:flex; gap:10px; flex-wrap:wrap; }}
.gx-kpi {{ background:{BG}; border:1px solid {LINE}; border-radius:9px; padding:8px 14px;
    text-align:right; min-width:92px; }}
.gx-kpi.accent {{ background:{ACCENT}; border-color:{ACCENT}; }}
.gx-kpi.accent .gx-kpi-v, .gx-kpi.accent .gx-kpi-l {{ color:#fff; }}
.gx-kpi.accent .gx-kpi-l {{ opacity:0.85; }}
.gx-kpi-v {{ font-family:{MONO}; font-size:16px; font-weight:600; color:{INK}; line-height:1.3; }}
.gx-kpi-l {{ font-size:10px; color:{MUTED}; letter-spacing:0.04em; text-transform:uppercase; }}

/* ---------- cards / callouts ---------- */
/* Streamlit tags EVERY vertical block with stVerticalBlockBorderWrapper, so match the exact
   parent chain of a card heading — a loose :has() also hits the page and column wrappers. */
[data-testid="stVerticalBlockBorderWrapper"]:has(
    > div > [data-testid="stVerticalBlock"] > [data-testid="element-container"]
    > [data-testid="stMarkdown"] > [data-testid="stMarkdownContainer"] > .gx-card-h) {{
    background:{PANEL}; border:1px solid {LINE}; border-radius:14px;
    padding:16px 20px 12px 20px; margin-bottom:16px; }}
.gx-card-h {{ font-size:10.5px; letter-spacing:0.06em; color:{FAINT}; font-weight:600;
    text-transform:uppercase; margin-bottom:2px; }}
.gx-note {{ background:{ACCENT_SOFT}; border:1px solid #d7d7f5; border-radius:12px;
    padding:15px 18px; display:flex; gap:13px; align-items:flex-start; margin-bottom:16px; }}
.gx-note-i {{ width:22px; height:22px; border-radius:6px; background:{ACCENT}; flex-shrink:0;
    display:flex; align-items:center; justify-content:center; color:#fff;
    font-family:{MONO}; font-size:13px; font-weight:600; }}
.gx-note-t {{ font-size:13.5px; line-height:1.55; color:#3b3b6b; }}
.gx-badge {{ font-size:9.5px; font-weight:600; letter-spacing:0.05em; padding:3px 8px;
    border-radius:5px; text-transform:uppercase; display:inline-block; }}
.gx-sig {{ font-family:{MONO}; font-size:12px; color:{MUTED}; }}

/* ---------- streamlit widget restyling ---------- */
[data-testid="stFileUploader"] section {{
    background:{PANEL}; border:1px dashed #c9c9d6; border-radius:12px; padding:18px; }}
[data-testid="stFileUploader"] section:hover {{ border-color:{ACCENT}; }}
[data-testid="stFileUploader"] small {{ color:{FAINT}; }}
.block-container .stButton button {{ border-radius:9px; font-weight:500; font-family:{SANS}; }}
[data-testid="stDownloadButton"] button {{
    background:{ACCENT}; color:#fff; border:none; border-radius:9px;
    font-weight:500; font-size:13px; padding:9px 18px; font-family:{SANS}; }}
[data-testid="stDownloadButton"] button:hover {{ background:{ACCENT_HOVER}; color:#fff; }}
[data-testid="stDataFrame"] {{ border:1px solid {LINE}; border-radius:12px; }}
[data-testid="stAlert"] {{ border-radius:11px; font-size:13.5px; }}
hr {{ border-color:{LINE}; }}
</style>
"""


def inject():
    st.markdown(_CSS, unsafe_allow_html=True)


def brand(name: str, tagline: str):
    st.markdown(
        f'<div class="gx-brand"><div class="gx-mark"><i></i></div>'
        f'<div><div class="gx-wordmark">{name}</div>'
        f'<div class="gx-tagline">{tagline}</div></div></div>',
        unsafe_allow_html=True,
    )


def nav_label(text: str):
    st.markdown(f'<div class="gx-navlabel">{text}</div>', unsafe_allow_html=True)


def sidebar_footer(lines, dot_color=LOW):
    body = f'<div><span class="gx-dot" style="background:{dot_color}"></span>{lines[0]}</div>'
    body += "".join(f"<div>{ln}</div>" for ln in lines[1:])
    st.markdown(f'<div class="gx-sidefoot">{body}</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str, kpis=()):
    tiles = ""
    for kpi in kpis:
        value, label = kpi[0], kpi[1]
        cls = "gx-kpi accent" if len(kpi) > 2 and kpi[2] else "gx-kpi"
        color = f"color:{kpi[3]}" if len(kpi) > 3 and kpi[3] else ""
        tiles += (f'<div class="{cls}"><div class="gx-kpi-v" style="{color}">{value}</div>'
                  f'<div class="gx-kpi-l">{label}</div></div>')
    st.markdown(
        f'<div class="gx-header"><div><div class="gx-title">{title}</div>'
        f'<div class="gx-sub">{subtitle}</div></div>'
        f'<div class="gx-kpis">{tiles}</div></div>',
        unsafe_allow_html=True,
    )


def note(text: str, icon: str = "i"):
    st.markdown(
        f'<div class="gx-note"><div class="gx-note-i">{icon}</div>'
        f'<div class="gx-note-t">{text}</div></div>',
        unsafe_allow_html=True,
    )


@contextmanager
def card(heading: str = ""):
    """A bordered panel. Uses a real Streamlit container so widgets nest inside it."""
    with st.container(border=True):
        st.markdown(f'<div class="gx-card-h">{heading}</div>', unsafe_allow_html=True)
        yield


def badge(text: str, color: str, soft: str) -> str:
    return f'<span class="gx-badge" style="color:{color};background:{soft}">{text}</span>'


def style_chart(chart):
    """Apply the design system's typography and gridlines to an Altair chart."""
    return (
        chart.configure_view(strokeWidth=0, fill=PANEL)
        .configure_axis(
            grid=True, gridColor=LINE, gridDash=[2, 3], domainColor=LINE, tickColor=LINE,
            labelColor=MUTED, labelFont="IBM Plex Mono", labelFontSize=10,
            titleColor=MUTED, titleFont="IBM Plex Sans", titleFontSize=11,
            titleFontWeight=500, titlePadding=10,
        )
        .configure_legend(
            labelFont="IBM Plex Sans", labelFontSize=12, labelColor=INK,
            titleFont="IBM Plex Sans", titleFontSize=10, titleColor=FAINT,
            symbolType="square", symbolSize=110, orient="top", direction="horizontal",
            offset=6,
        )
    )
