"""
UK Take-Home Pay Calculator — tax year 2026/27.

A small Streamlit app: enter a salary and a few options, get take-home pay.
All the tax figures live in the TAX_YEAR dict below so you only have one
place to edit each April when rates change.

Run locally:   streamlit run app.py
Deploy free:   push to a GitHub repo, then deploy at share.streamlit.io
"""

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# All rates/thresholds for the year in one place. Update this each April.
# Figures are for the 2026/27 UK tax year.
# ---------------------------------------------------------------------------
TAX_YEAR = {
    "label": "2026/27",
    "personal_allowance": 12_570,
    "pa_taper_start": 100_000,  # PA reduced £1 for every £2 above this
    # Income tax — England, Wales & Northern Ireland ("rest of UK")
    "ruk_bands": [
        # (band width on TAXABLE income, rate). Last band width None = "rest".
        (37_700, 0.20),  # basic rate
        (125_140 - 12_570 - 37_700, 0.40),  # higher rate, up to £125,140 gross
        (None, 0.45),  # additional rate
    ],
    # Income tax — Scotland (non-savings, non-dividend)
    # Band widths on taxable income assuming the standard £12,570 allowance.
    "scotland_bands": [
        (16_537 - 12_570, 0.19),  # starter
        (29_526 - 16_537, 0.20),  # basic
        (43_662 - 29_526, 0.21),  # intermediate
        (75_000 - 43_662, 0.42),  # higher
        (125_140 - 75_000, 0.45),  # advanced
        (None, 0.48),  # top
    ],
    # National Insurance — Class 1 employee (same across the whole UK)
    "ni_primary_threshold": 12_570,
    "ni_upper_earnings_limit": 50_270,
    "ni_main_rate": 0.08,
    "ni_upper_rate": 0.02,
    # Student loans — annual thresholds, 9% above (6% for postgrad)
    "student_loans": {
        "Plan 1": (26_900, 0.09),
        "Plan 2": (29_385, 0.09),
        "Plan 4 (Scotland)": (33_795, 0.09),
        "Plan 5": (25_000, 0.09),
    },
    "postgrad_loan": (21_000, 0.06),
}


# ---------------------------------------------------------------------------
# Calculation functions — pure Python, no Streamlit. Easy to test.
# ---------------------------------------------------------------------------
def personal_allowance(gross: float, cfg: dict) -> float:
    """Personal allowance after the £100k taper."""
    pa = cfg["personal_allowance"]
    over = gross - cfg["pa_taper_start"]
    if over > 0:
        pa = max(0.0, pa - over / 2)
    return pa


def _tax_from_bands(taxable: float, bands: list) -> float:
    """Apply a list of (width, rate) bands to a taxable amount."""
    tax = 0.0
    remaining = taxable
    for width, rate in bands:
        if remaining <= 0:
            break
        slice_ = remaining if width is None else min(remaining, width)
        tax += slice_ * rate
        remaining -= slice_
    return tax


def income_tax(gross: float, region: str, cfg: dict) -> float:
    pa = personal_allowance(gross, cfg)
    taxable = max(0.0, gross - pa)
    bands = cfg["scotland_bands"] if region == "Scotland" else cfg["ruk_bands"]
    return _tax_from_bands(taxable, bands)


def national_insurance(gross: float, cfg: dict) -> float:
    pt = cfg["ni_primary_threshold"]
    uel = cfg["ni_upper_earnings_limit"]
    ni = 0.0
    if gross > pt:
        ni += (min(gross, uel) - pt) * cfg["ni_main_rate"]
    if gross > uel:
        ni += (gross - uel) * cfg["ni_upper_rate"]
    return ni


def student_loan(gross: float, plan: str, has_postgrad: bool, cfg: dict) -> float:
    repay = 0.0
    if plan in cfg["student_loans"]:
        threshold, rate = cfg["student_loans"][plan]
        repay += max(0.0, gross - threshold) * rate
    if has_postgrad:
        threshold, rate = cfg["postgrad_loan"]
        repay += max(0.0, gross - threshold) * rate
    return repay


def calculate(gross, region, pension_pct, plan, has_postgrad, cfg):
    """Return a dict of all the annual figures.

    Pension is modelled as salary sacrifice: it comes off gross *before*
    tax and NI are worked out. (Other pension methods give slightly
    different results — see the note in the app.)
    """
    pension = gross * pension_pct / 100
    taxable_gross = gross - pension
    tax = income_tax(taxable_gross, region, cfg)
    ni = national_insurance(taxable_gross, cfg)
    sl = student_loan(taxable_gross, plan, has_postgrad, cfg)
    take_home = taxable_gross - tax - ni - sl
    return {
        "Gross salary": gross,
        "Pension (salary sacrifice)": pension,
        "Income tax": tax,
        "National Insurance": ni,
        "Student loan": sl,
        "Take-home pay": take_home,
    }


# ---------------------------------------------------------------------------
# The user interface
# ---------------------------------------------------------------------------
st.set_page_config(page_title="UK Take-Home Pay", page_icon="💷")

st.title("💷 UK Take-Home Pay Calculator")
st.caption(
    f"Tax year {TAX_YEAR['label']} · England, Wales, NI & Scotland · estimate only"
)

col_in, col_out = st.columns([1, 1.3])

with col_in:
    st.subheader("Your details")
    gross = st.number_input(
        "Annual gross salary (£)",
        min_value=0,
        max_value=2_000_000,
        value=35_000,
        step=1_000,
    )
    region = st.selectbox(
        "Where do you live?",
        ["England / Wales / NI", "Scotland"],
    )
    region_key = "Scotland" if region == "Scotland" else "rUK"
    pension_pct = st.slider(
        "Pension contribution (%)",
        0.0,
        30.0,
        0.0,
        step=0.5,
        help="Modelled as salary sacrifice — taken off before tax and NI.",
    )
    plan = st.selectbox(
        "Student loan plan",
        ["None", "Plan 1", "Plan 2", "Plan 4 (Scotland)", "Plan 5"],
    )
    has_postgrad = st.checkbox("Also have a postgraduate loan")

result = calculate(gross, region_key, pension_pct, plan, has_postgrad, TAX_YEAR)

with col_out:
    st.subheader("Your take-home pay")
    annual_th = result["Take-home pay"]
    c1, c2 = st.columns(2)
    c1.metric("Monthly", f"£{annual_th / 12:,.0f}")
    c2.metric("Annual", f"£{annual_th:,.0f}")

    # Breakdown table (annual + monthly)
    rows = []
    for label, value in result.items():
        rows.append(
            {
                "Item": label,
                "Annual": f"£{value:,.0f}",
                "Monthly": f"£{value / 12:,.0f}",
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    if gross > 0:
        deductions = (
            result["Income tax"] + result["National Insurance"] + result["Student loan"]
        )
        eff = deductions / gross * 100
        st.caption(f"Effective deduction rate (tax + NI + student loan): {eff:.1f}%")

# Where the money goes — a simple bar chart
if gross > 0:
    st.subheader("Where your salary goes")
    chart_data = pd.DataFrame(
        {
            "Amount": [
                result["Take-home pay"],
                result["Income tax"],
                result["National Insurance"],
                result["Student loan"],
                result["Pension (salary sacrifice)"],
            ],
        },
        index=["Take-home", "Income tax", "NI", "Student loan", "Pension"],
    )
    chart_data = chart_data[chart_data["Amount"] > 0]
    st.bar_chart(chart_data, horizontal=True)

with st.expander("What this does and doesn't cover"):
    st.markdown(
        """
        This is an **estimate** for a standard employee paid through PAYE.

        **Included:** income tax (incl. the £100k personal-allowance taper),
        Class 1 employee National Insurance, student loan repayments, and a
        salary-sacrifice pension.

        **Not included:** marriage allowance, blind person's allowance,
        benefits in kind / company cars, taxable benefits, the Scottish
        personal-allowance taper edge cases above £100k, and non-salary
        income (dividends, savings, self-employment).

        Pension here is modelled as **salary sacrifice**. *Net pay* and
        *relief-at-source* schemes give slightly different results.

        Always check your own figures against GOV.UK. Not financial advice.
        """
    )
