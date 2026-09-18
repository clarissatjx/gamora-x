import streamlit as st

import theme


def render(meta: dict):
    theme.page_title(meta["title"], meta["subtitle"])
    st.write("")
    theme.banner(
        f"<strong>Not wired up yet.</strong> {meta['status']} Once the model lands, this page takes "
        f"the same upload → result → download flow as the Door page.",
        icon="!", color=theme.AMBER,
    )
    theme.metrics([
        ("Status", "pending", "model not yet trained", theme.AMBER),
        ("Files scored", "0", "nothing submitted yet", None),
        ("Output", meta["csv"].replace("_predictions.csv", ""), meta["csv"], None),
        ("Metric", meta["tag"], "held-out test set", None),
    ])

    left, right = st.columns([1.4, 1])
    with left:
        with theme.panel("What this model will do"):
            st.markdown(f'<p class="gx-prose" style="color:{theme.MUTED}">{meta["detail"]}</p>',
                        unsafe_allow_html=True)
    with right:
        with theme.panel("Submission output", meta["csv"]):
            st.markdown(
                f'<div style="font-family:{theme.MONO};font-size:12.5px;color:{theme.FAINT};'
                f'padding-top:6px">{meta["schema"]}</div>',
                unsafe_allow_html=True,
            )

    st.file_uploader(meta["upload"], type=meta["types"], disabled=True,
                     key=f"pending_{meta['crumb']}",
                     help="Enabled once this subsystem's model is trained.")
