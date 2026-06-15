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
    bonus1 = st.number_input(
        "Bonus 1 (£)",
        key=f"{key_prefix}_bonus1",
        min_value=0,
        value=50_000,
        step=5_000,
    )
    bonus2 = st.number_input(
        "Bonus 2 (£)",
        key=f"{key_prefix}_bonus2",
        min_value=0,
        value=0,
        step=5_000,
        help="A second bonus paid in a different month. Leave at 0 if you only "
        "get one.",
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
            [bonus1, bonus2],
            THRESHOLD,
            TAX_RATE,
            reliefs=pension,
            tax_code=tax_code,
        )
    except ValueError as err:
        st.error(f"Couldn't calculate take-home: {err}")
        return

    # The year splits into normal months and one month per bonus; that logic
    # lives in TakeHomeResults. Here we just label a metric for each month plus
    # the annual total.
    bonus_months = result.bonus_months

    st.subheader("Your take-home pay")
    metrics = [
        (
            "Monthly (no bonus)" if bonus_months else "Monthly",
            result.non_bonus_month,
            "A month with no bonus paid." if bonus_months else None,
        )
    ]
    for i, month in enumerate(bonus_months, start=1):
        label = "Bonus month" if len(bonus_months) == 1 else f"Bonus month {i}"
        metrics.append((label, month, "The month this bonus lands."))
    metrics.append(("Annual", result.take_home, None))

    for col, (label, value, help_text) in zip(st.columns(len(metrics)), metrics):
        col.metric(label, f"£{value:,.0f}", help=help_text)

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
