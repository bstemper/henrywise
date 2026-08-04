"""HenryWise — Streamlit entry point. Wiring only; no tax numbers, no maths.

Run with:  streamlit run src/henrywise/ui/app.py
"""

from __future__ import annotations

import streamlit as st

from henrywise.tax import rates
from henrywise.ui.job_grid import Job, render_tab

JOBS = [Job("Job 1", "job1"), Job("Job 2", "job2")]

st.set_page_config(page_title="HenryWise UK", page_icon="💷")

st.title("💷 HenryWise UK")
st.caption("All the calculators a Henry needs to manage their money")

tab_take_home, tab_pension = st.tabs(["Take-home pay", "Pension tapering"])

with tab_take_home:
    render_tab(JOBS)

with tab_pension:
    st.subheader("Pension tapering")
    st.info("Coming soon.")

st.caption(
    f"Estimate only — tax year {rates.LABEL}. Income tax (incl. the £100k allowance "
    "taper) and Class 1 employee National Insurance, on PAYE earnings for the rest "
    "of the UK. Excludes student loans and Scottish/Welsh rates."
)
