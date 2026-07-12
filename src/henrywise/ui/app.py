"""HenryWise — Streamlit entry point. Wiring only; no tax numbers, no maths.

Run with:  streamlit run src/henrywise/ui/app.py
"""

from __future__ import annotations

import streamlit as st

from henrywise.tax import rates
from henrywise.ui.job_panel import render_job

st.set_page_config(page_title="HenryWise UK", page_icon="💷")

st.title("💷 HenryWise UK")
st.caption("All the calculators a Henry needs to manage their money")

tab_take_home, tab_pension = st.tabs(["Take-home pay", "Pension tapering"])

with tab_take_home:
    col_left, col_right = st.columns(2)
    with col_left:
        render_job("Job 1 Details", "job1")
    with col_right:
        render_job("Job 2 Details", "job2")

with tab_pension:
    st.subheader("Pension tapering")
    st.info("Coming soon.")

st.caption(
    f"Estimate only — tax year {rates.LABEL}. Income tax (incl. the £100k allowance "
    "taper) on PAYE earnings for the rest of the UK. Excludes National Insurance, "
    "student loans, and Scottish/Welsh rates."
)
