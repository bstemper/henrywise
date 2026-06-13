import pandas as pd
import streamlit as st
from take_home import TaxRate, TaxBands, calculate_take_home

# 2026/27, rest of UK. A tax code in the UI overrides the personal allowance.
TAX_RATE = TaxRate(0, 0.20, 0.40, 0.45)
THRESHOLD = TaxBands.from_thresholds(12_570, 50_270, 125_140)

st.set_page_config(page_title="HenryWise UK", page_icon="💷")

st.title("💷 HenryWise UK ")
st.caption("All the calculators a Henry needs to manage their money")


def render_job(title: str, key_prefix: str) -> None:
    """Render one job's inputs and its take-home breakdown."""
    st.subheader(title)
    base = st.number_input(
        "Annual base salary (£)",
        key=f"{key_prefix}_base",
        min_value=0,
        value=125_000,
        step=5_000,
    )
    bonus = st.number_input(
        "Annual bonus (£)",
        key=f"{key_prefix}_bonus",
        min_value=0,
        value=50_000,
        step=5_000,
    )
    pension_pct = st.number_input(
        "Pension contribution (%)",
        key=f"{key_prefix}_pension",
        min_value=0,
        max_value=100,
        value=5,
        step=1,
        help="Modelled as salary sacrifice — taken off pay before tax. "
        "Applied to base.",
    )
    tax_code = st.text_input(
        "Tax code",
        key=f"{key_prefix}_tax_code",
        value="1257L",
        help="Leave blank for the standard allowance. Scottish/Welsh (S/C) "
        "and K codes aren't supported.",
    )

    pension = base * pension_pct / 100
    try:
        result = calculate_take_home(
            base,
            bonus,
            THRESHOLD,
            TAX_RATE,
            reliefs=pension,
            tax_code=tax_code,
        )
    except ValueError as err:
        st.error(f"Couldn't calculate take-home: {err}")
        return

    st.subheader("Your take-home pay")
    c1, c2 = st.columns(2)
    c1.metric("Monthly", f"£{result.take_home / 12:,.0f}")
    c2.metric("Annual", f"£{result.take_home:,.0f}")

    # Breakdown — annual and monthly.
    rows = [
        ("Total comp", result.total_comp),
        ("Pension", result.reliefs),
        ("Taxable income", result.taxable_income),
        ("Income tax", result.total_tax),
        ("Take-home", result.take_home),
    ]
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Item": label,
                    "Annual": f"£{value:,.0f}",
                    "Monthly": f"£{value / 12:,.0f}",
                }
                for label, value in rows
            ]
        ),
        hide_index=True,
        width="stretch",
    )

    # Where the gross comp goes — these three sum to total comp.
    st.subheader("Where your salary goes")
    chart_data = pd.DataFrame(
        {"Amount": [result.take_home, result.total_tax, result.reliefs]},
        index=["Take-home", "Income tax", "Pension"],
    )
    chart_data = chart_data[chart_data["Amount"] > 0]
    st.bar_chart(chart_data, horizontal=True)


tab1, tab2 = st.tabs(["Take-home pay", "Pension tapering"])

with tab1:
    col_left, col_right = st.columns(2)
    with col_left:
        render_job("Job 1 Details", "job1")
    with col_right:
        render_job("Job 2 Details", "job2")

with tab2:
    st.subheader("Pension tapering")
    st.info("Coming soon.")

st.caption(
    "Estimate only — income tax (incl. the £100k allowance taper) on PAYE "
    "earnings for the rest of the UK. Excludes National Insurance, student "
    "loans, and Scottish/Welsh rates."
)
