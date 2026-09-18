"""Session-level state shared by every page.

Three things live here so the pages don't each reinvent them:

- **Samples.** One bundled raw file per subsystem (`app/samples/`), so a first-time viewer can
  see a result without hunting for data. Big ones are gzipped; they are decompressed on load
  and presented under their original file name, so `file_id` matches the submitted CSV.
- **Results.** Each page records the prediction CSV it produced; the overview offers them all
  as one flat `predictions.zip`, laid out exactly like the submission.
- **Batch picker.** In batch mode the charts and evidence follow one chosen file rather than
  always the first. The choice is stashed in session state because sidebar buttons call
  `st.rerun()` before main-area widgets render, which makes Streamlit drop their state.
"""
import gzip
import io
import zipfile
from pathlib import Path

import streamlit as st

import theme

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"

# key -> (file in SAMPLES_DIR, what the viewer will see)
SAMPLES = {
    "door": ("Test.csv", "the held-out door stream: 38 cycles, 8 of them flagged abnormal"),
    "acv": ("acv_test_case.xlsx", "the held-out workbook: 8 cars, car 01 ranked most likely faulty"),
    "rail": ("Test33.csv.gz", "a held-out recording at 46 km/h that the model classifies Side I"),
    "shm": ("test02.csv.gz", "the held-out segment with the highest predicted damage, 0.83"),
}
NAV = {"door": "Door", "acv": "ACV", "rail": "Rail Corrugation", "shm": "SHM"}
ZIP_ORDER = ["door", "acv", "rail", "shm"]


# ---- samples -----------------------------------------------------------------------------

def sample_name(key: str) -> str:
    """The name the page will see — the original file name, without any .gz."""
    name = SAMPLES[key][0]
    return name[:-3] if name.endswith(".gz") else name


def load_sample(key: str):
    path = SAMPLES_DIR / SAMPLES[key][0]
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return sample_name(key), data


def use_sample(key: str):
    """Put the sample where the page expects an upload, open that page, rerun."""
    st.session_state[f"{key}_files"] = [load_sample(key)]
    st.session_state.view = key
    st.rerun()


def sample_button(key: str):
    """Offered on a page's empty state: one click loads the bundled file."""
    name, blurb = sample_name(key), SAMPLES[key][1]
    col, _ = st.columns([1.5, 3])
    if col.button(f"Try the sample — {name}", key=f"try_{key}", use_container_width=True):
        use_sample(key)
    st.markdown(
        f'<div style="font-size:12.5px;color:{theme.FAINT};margin-top:-6px">'
        f'Loads {blurb}. Bundled with the app, so no download is needed.</div>',
        unsafe_allow_html=True,
    )


# ---- results -----------------------------------------------------------------------------

def record(key: str, csv_name: str, csv_bytes: bytes, n_rows: int, files):
    st.session_state.setdefault("results", {})[key] = {
        "csv": csv_name, "bytes": csv_bytes, "n_rows": n_rows, "files": list(files),
    }


def results() -> dict:
    return st.session_state.get("results", {})


def clear_results():
    st.session_state.pop("results", None)


def build_zip() -> bytes:
    """Flat zip, submission file names, subsystems in the spec's order."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for key in ZIP_ORDER:
            r = results().get(key)
            if r:
                z.writestr(r["csv"], r["bytes"])
    return buf.getvalue()


def overview_panel():
    """What has been scored this session, with the combined zip. Silent until there is something."""
    res = results()
    if not res:
        return
    rows = []
    for key in ZIP_ORDER:
        r = res.get(key)
        if not r:
            continue
        files = ", ".join(r["files"][:3]) + (f" +{len(r['files']) - 3} more" if len(r["files"]) > 3 else "")
        rows.append([NAV[key], f'<span style="font-family:{theme.MONO}">{files}</span>',
                     str(r["n_rows"]), f'<span style="font-family:{theme.MONO}">{r["csv"]}</span>'])
    theme.table(
        ["subsystem", "files scored", "rows", "csv"], rows,
        f"This session · {len(rows)} of 4 subsystems scored", "predictions.zip",
        footer="One flat zip with the submission's file names — the same layout "
               "scripts/validate_submission.py checks.",
    )
    dl, cl, _ = st.columns([1.4, 0.6, 3])
    dl.download_button("⬇  Download predictions.zip", build_zip(), file_name="predictions.zip",
                       mime="application/zip", use_container_width=True)
    if cl.button("Clear", use_container_width=True, key="session_clear"):
        clear_results()
        st.rerun()


# ---- batch picker ------------------------------------------------------------------------

def inspect_picker(key: str, names) -> int:
    """Which of the batch's files the charts and evidence should follow. Returns its index."""
    if len(names) <= 1:
        return 0
    stash = f"{key}_inspect"
    default = names.index(st.session_state[stash]) if st.session_state.get(stash) in names else 0
    col, cap = st.columns([1.5, 3])
    with col:
        choice = st.selectbox("Inspect file", names, index=default, key=f"{stash}_widget",
                              label_visibility="collapsed")
    cap.markdown(
        f'<div style="font-size:12.5px;color:{theme.FAINT};padding-top:9px">Charts and evidence '
        f'below follow this file; the table and download cover all {len(names)}.</div>',
        unsafe_allow_html=True,
    )
    st.session_state[stash] = choice
    return names.index(choice)
