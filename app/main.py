import pandas as pd
import streamlit as st
from take_home import TaxRate, IncomeThreshold, calculate_take_home, TakeHomeResults

TAX_RATE = TaxRate(0, 0.20, 0.40, 0.45)
THRESHOLD = IncomeThreshold(12570, 50270, 125140)

st.set_page_config(page_title="HenryWise UK", page_icon="💷")

st.title("💷 HenryWise UK ")
st.caption(f"All the calculators a Henry needs to manage their money")


tab1, tab2 = st.tabs(["Take-home pay", "Pension tapering"])
col_left, col_right = st.columns([1, 1])

with tab1:
    with col_left:
        st.subheader("Job 1 Details")
        base1 = st.number_input(
            label="Annual base salary (£)",
            key="job1_annual_base",
            min_value=0,
            value=125_000,
            step=5_000,
        )
        bonus1 = st.number_input(
            label="Annual bonus (£)",
            key="job1_annual_bonus",
            min_value=0,
            value=50_000,
            step=5_000,
        )
        pension_percentage1 = st.number_input(
            label="Pension contribution (%)",
            key="job1_pension_contribution",
            min_value=0,
            max_value=100,
            value=5,
            step=1,
        )
        tax_code1 = st.text_input(label="Tax code", key="tax_code1", value="1280L")

        job1_result: TakeHomeResults = calculate_take_home(
            base1, bonus1, THRESHOLD, TAX_RATE
        )

        st.subheader("Your take-home pay")
        c1, c2 = st.columns(2)
        c1.metric("Monthly", f"£{180000 / 12:,.0f}")
        c2.metric("Annual", f"£{180000:,.0f}")

        st.subheader("Where your salary goes")
        chart_data = pd.DataFrame(
            {
                "Amount": [
                    job1_result.taxable_income,
                    job1_result.basic_tax,
                    job1_result.higher_tax,
                    job1_result.additional_tax,
                ],
            },
            index=["Taxable Income", "Basic Tax", "Higher Tax", "Additional Tax"],
        )
    chart_data = chart_data[chart_data["Amount"] > 0]
    st.bar_chart(chart_data, horizontal=True)

    with col_right:
        st.subheader("Job 2 Details")
        base2 = st.number_input(
            label="Annual base salary (£)",
            key="job2_annual_base",
            min_value=0,
            value=125_000,
            step=5_000,
        )
        bonus1 = st.number_input(
            label="Annual bonus (£)",
            key="job2_annual_bonus",
            min_value=0,
            value=50_000,
            step=5_000,
        )
        pension_percentage1 = st.number_input(
            label="Pension contribution (%)",
            key="job2_pension_contribution",
            min_value=0,
            max_value=100,
            value=5,
            step=1,
        )
        tax_code2 = st.text_input(label="Tax code", key="tax_code2", value="1280L")

        st.subheader("Your take-home pay")
        c1, c2 = st.columns(2)
        c1.metric("Monthly", f"£{180000 / 12:,.0f}")
        c2.metric("Annual", f"£{180000:,.0f}")

with tab2:
    st.subheader("Pension")
