"""Placeholder page for subsystems whose model isn't wired into the app yet."""
import streamlit as st

import theme


def render(meta: dict):
    theme.page_header(meta["title"], meta["subtitle"], [("—", "status"), ("0", "files scored")])
    theme.note(
        f"<strong>Not wired up yet.</strong> {meta['status']} "
        f"Once the model lands, this page takes the same upload → result → download flow as the Door page.",
        icon="!",
    )

    left, right = st.columns([1.35, 1])
    with left:
        with theme.card("What this model will do"):
            st.markdown(
                f"<div style='font-size:13.5px;line-height:1.65;color:{theme.MUTED}'>"
                f"{meta['detail']}</div>",
                unsafe_allow_html=True,
            )
    with right:
        with theme.card("Submission output"):
            rows = "".join(
                f"<div style='display:flex;justify-content:space-between;gap:12px;padding:7px 0;"
                f"border-bottom:1px solid {theme.LINE}'>"
                f"<span class='gx-sig'>{col}</span>"
                f"<span style='font-size:12.5px;color:{theme.MUTED};text-align:right'>{desc}</span></div>"
                for col, desc in meta["schema"]
            )
            st.markdown(
                f"<div class='gx-sig' style='color:{theme.INK};font-weight:600;margin-bottom:8px'>"
                f"{meta['output_file']}</div>{rows}",
                unsafe_allow_html=True,
            )

    st.file_uploader(
        meta["upload_label"], type=meta["file_types"], disabled=True,
        key=f"pending_{meta['key']}", help="Enabled once this subsystem's model is trained.",
    )
