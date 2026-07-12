"""One job's panel: collect the inputs, then render the take-home breakdown."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from henrywise.tax import rates
from henrywise.tax.models import TakeHomeResults
from henrywise.tax.take_home import calculate_take_home
from henrywise.ui.format import money, monthly


@dataclass
class JobInputs:
    base: float
    bonuses: list[float]
    pension_pct: float
    tax_code: str

    @property
    def pension(self) -> float:
        """Salary-sacrifice pension, applied to base only."""
        return self.base * self.pension_pct / 100


def collect_job_inputs(key_prefix: str) -> JobInputs:
    """Render this job's input widgets and return what the user entered."""
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
        help="A second bonus paid in a different month. Leave at 0 if you only get one.",
    )
    pension_pct = st.number_input(
        "Pension contribution (%)",
        key=f"{key_prefix}_pension",
        min_value=0,
        max_value=100,
        value=5,
        step=1,
        help="Modelled as salary sacrifice — taken off pay before tax. Applied to base.",
    )
    tax_code = st.text_input(
        "Tax code",
        key=f"{key_prefix}_tax_code",
        value="1257L",
        help="Leave blank for the standard allowance. Scottish/Welsh (S/C) "
        "and K codes aren't supported.",
    )
    return JobInputs(base, [bonus1, bonus2], pension_pct, tax_code)


def render_results(result: TakeHomeResults) -> None:
    """Render the metrics, breakdown table and chart for a computed result."""
    # The year splits into normal months and one month per bonus; that logic
    # lives in TakeHomeResults. Here we just label a metric for each.
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
        col.metric(label, money(value), help=help_text)

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
                {"Item": label, "Annual": money(value), "Monthly": monthly(value)}
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
    st.bar_chart(chart_data[chart_data["Amount"] > 0], horizontal=True)


def render_job(title: str, key_prefix: str) -> None:
    """Render one job end to end: inputs, calculation, results."""
    st.subheader(title)
    inputs = collect_job_inputs(key_prefix)

    try:
        result = calculate_take_home(
            inputs.base,
            inputs.bonuses,
            rates.BANDS,
            rates.RATES,
            reliefs=inputs.pension,
            tax_code=inputs.tax_code,
        )
    except ValueError as err:
        st.error(f"Couldn't calculate take-home: {err}")
        return

    render_results(result)
