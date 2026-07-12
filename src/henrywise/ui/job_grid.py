"""The take-home tab: the jobs side by side, one row per field.

Both jobs answer the same questions and report the same figures, so a label is
written once, in a left-hand column, and each job gets a column of its own.
Inputs and results then line up row by row, which is what makes two jobs
comparable at a glance.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from henrywise.tax import rates
from henrywise.tax.models import TakeHomeResults
from henrywise.tax.take_home import calculate_take_home
from henrywise.ui.format import money, percent

# The label column carries the longest text on its row, so it gets more room.
LABEL_WIDTH = 1.4
# Shown wherever a job has no figure: either it failed to calculate, or it has
# fewer bonuses than the job beside it.
MISSING = "—"
# Section headings sit a step below the page title; the figures a step below
# those. Money should read clearly without shouting over the words around it.
HEADING = "####"
FIGURE = "#####"


class Job(NamedTuple):
    title: str  # what the column is called
    key: str  # prefix for this job's widget keys, so its state is its own


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


def section(title: str, blurb: str) -> None:
    """A section heading and the one line that says what you're looking at."""
    st.markdown(f"{HEADING} {title}")
    st.caption(blurb)


def row(
    label: str, jobs: list[Job], help_text: str | None = None
) -> list[DeltaGenerator]:
    """Write a row's shared label, and hand back one cell per job to fill."""
    cells = st.columns([LABEL_WIDTH] + [1] * len(jobs), vertical_alignment="center")
    cells[0].markdown(label, help=help_text)
    return cells[1:]


def header_row(jobs: list[Job]) -> None:
    """Name the columns. Worth repeating per grid — they're read far apart."""
    for cell, job in zip(row("", jobs), jobs):
        cell.markdown(f"**{job.title}**")


def number_row(
    label: str, field: str, jobs: list[Job], help_text: str | None = None, **kwargs
) -> list[float]:
    """One numeric field, asked of every job."""
    return [
        cell.number_input(
            label, key=f"{job.key}_{field}", label_visibility="collapsed", **kwargs
        )
        for cell, job in zip(row(label, jobs, help_text), jobs)
    ]


def text_row(
    label: str, field: str, jobs: list[Job], help_text: str | None = None, **kwargs
) -> list[str]:
    """One text field, asked of every job."""
    return [
        cell.text_input(
            label, key=f"{job.key}_{field}", label_visibility="collapsed", **kwargs
        )
        for cell, job in zip(row(label, jobs, help_text), jobs)
    ]


def collect_inputs(jobs: list[Job]) -> list[JobInputs]:
    """Render the input grid and return what the user entered, per job."""
    section(
        "The jobs",
        "Annual, gross figures for each offer — what's on the contract, before "
        "any tax or pension comes out. Everything below updates as you type.",
    )
    header_row(jobs)

    bases = number_row(
        "Annual base salary (£)", "base", jobs, min_value=0, value=125_000, step=5_000
    )
    first_bonuses = number_row(
        "Bonus 1 (£)", "bonus1", jobs, min_value=0, value=50_000, step=5_000
    )
    second_bonuses = number_row(
        "Bonus 2 (£)",
        "bonus2",
        jobs,
        help_text="A second bonus paid in a different month. Leave at 0 if you only get one.",
        min_value=0,
        value=0,
        step=5_000,
    )
    pension_pcts = number_row(
        "Pension contribution (%)",
        "pension",
        jobs,
        help_text="Modelled as salary sacrifice — taken off pay before tax. Applied to base.",
        min_value=0,
        max_value=100,
        value=5,
        step=1,
    )
    # Blank by default: we work the allowance out ourselves, taper included.
    # A code entered here is taken at face value (a real HMRC code already has
    # any taper baked into its number), so defaulting to "1257L" would hand a
    # full allowance to someone over £100k who never asked for one.
    tax_codes = text_row(
        "Tax code",
        "tax_code",
        jobs,
        help_text="Leave blank and we'll apply the standard allowance, tapered away "
        "above £100k. Enter a code to use it as-is. Scottish/Welsh (S/C) and "
        "K codes aren't supported.",
        value="",
        placeholder="Worked out for you",
    )

    return [
        JobInputs(base, [bonus1, bonus2], pension_pct, tax_code)
        for base, bonus1, bonus2, pension_pct, tax_code in zip(
            bases, first_bonuses, second_bonuses, pension_pcts, tax_codes
        )
    ]


def calculate(jobs: list[Job], inputs: list[JobInputs]) -> list[TakeHomeResults | None]:
    """Calculate each job, reporting — rather than raising — a bad input.

    A job that can't be calculated comes back as None, so the job beside it
    still gets its column.
    """
    results: list[TakeHomeResults | None] = []
    for job, job_inputs in zip(jobs, inputs):
        try:
            results.append(
                calculate_take_home(
                    job_inputs.base,
                    job_inputs.bonuses,
                    rates.BANDS,
                    rates.RATES,
                    reliefs=job_inputs.pension,
                    tax_code=job_inputs.tax_code,
                )
            )
        except ValueError as err:
            st.error(f"Couldn't calculate take-home for {job.title}: {err}")
            results.append(None)
    return results


def take_home_rows(
    results: list[TakeHomeResults | None],
) -> list[tuple[str, list[float | None], str | None]]:
    """The take-home figures as (label, one value per job, help) rows.

    The year splits into normal months and one month per bonus. Jobs can carry
    different numbers of bonuses, so the rows span the busiest job, and a job
    without that bonus month leaves the cell empty.
    """
    most_bonuses = max((len(r.bonus_months) for r in results if r), default=0)

    rows: list[tuple[str, list[float | None], str | None]] = [
        (
            "Monthly (no bonus)" if most_bonuses else "Monthly",
            [r.non_bonus_month if r else None for r in results],
            "A month with no bonus paid." if most_bonuses else None,
        )
    ]
    for i in range(most_bonuses):
        label = "Bonus month" if most_bonuses == 1 else f"Bonus month {i + 1}"
        months = [
            r.bonus_months[i] if r and i < len(r.bonus_months) else None
            for r in results
        ]
        rows.append((label, months, "The month this bonus lands."))
    rows.append(("Annual", [r.take_home if r else None for r in results], None))

    return rows


def render_take_home(jobs: list[Job], results: list[TakeHomeResults | None]) -> None:
    """The headline figures: one row per period, one column per job."""
    section(
        "Take-home pay",
        "What actually reaches your account, after income tax and pension. Each "
        "bonus lands whole, in a single month.",
    )
    header_row(jobs)

    for label, values, help_text in take_home_rows(results):
        for cell, value in zip(row(label, jobs, help_text), values):
            figure = money(value) if value is not None else MISSING
            cell.markdown(f"{FIGURE} {figure}")


# Annual only — a monthly column of the same numbers is noise, and the monthly
# cash flow that does matter is the take-home grid above.
BREAKDOWN: list[tuple[str, Callable[[TakeHomeResults], str]]] = [
    ("Total compensation", lambda r: money(r.total_comp)),
    ("Pension", lambda r: money(r.reliefs)),
    ("Taxable income", lambda r: money(r.taxable_income)),
    ("Personal allowance", lambda r: money(r.personal_allowance)),
    ("Income tax", lambda r: money(r.total_tax)),
    ("Take rate", lambda r: percent(r.keep_rate)),
]


def render_breakdown(jobs: list[Job], results: list[TakeHomeResults | None]) -> None:
    """How the gross figure becomes the net one, a year at a time."""
    section(
        "The breakdown",
        "Annual. The personal allowance tapers away above £100k; the take rate "
        "is the share of every gross pound you keep.",
    )

    table = []
    for label, figure_of in BREAKDOWN:
        cells = {"Item": label}
        for job, result in zip(jobs, results):
            cells[job.title] = figure_of(result) if result else MISSING
        table.append(cells)

    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")


def render_split(jobs: list[Job], results: list[TakeHomeResults | None]) -> None:
    """Where the gross comp goes — these three sum to total comp, per job."""
    split = {
        job.title: [r.take_home, r.total_tax, r.reliefs]
        for job, r in zip(jobs, results)
        if r
    }
    if not split:
        return

    section(
        "Where your salary goes",
        "Take-home, income tax and pension — together, the whole package.",
    )
    chart_data = pd.DataFrame(split, index=["Take-home", "Income tax", "Pension"])
    # Drop a row only when no job has anything in it — e.g. neither pays into a
    # pension. Grouped bars, not stacked: the jobs are alternatives, not parts.
    st.bar_chart(chart_data[chart_data.sum(axis=1) > 0], horizontal=True, stack=False)


def render_tab(jobs: list[Job]) -> None:
    """Render the take-home tab end to end: inputs, calculation, results."""
    inputs = collect_inputs(jobs)
    results = calculate(jobs, inputs)

    render_take_home(jobs, results)
    render_breakdown(jobs, results)
    render_split(jobs, results)
