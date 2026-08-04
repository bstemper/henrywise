"""Smoke tests for the Streamlit app, driven through Streamlit's own AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from henrywise.tax import rates
from henrywise.tax.take_home import calculate_take_home
from henrywise.ui.format import money, percent
from henrywise.ui.job_grid import FIGURE

APP = str(Path(__file__).parent.parent / "src" / "henrywise" / "ui" / "app.py")


def figures(app):
    """Every take-home figure on the page, as rendered."""
    return [m.value for m in app.markdown if m.value.startswith(FIGURE)]


def breakdown(app, job):
    """One job's column of the breakdown table, keyed by row label."""
    return app.dataframe[0].value.set_index("Item")[job]


@pytest.fixture
def app():
    return AppTest.from_file(APP, default_timeout=30).run()


def test_app_renders_without_error(app):
    assert not app.exception
    assert app.title[0].value == "💷 HenryWise UK"
    assert not app.error


def test_both_jobs_get_a_full_set_of_inputs(app):
    keys = {w.key for w in app.number_input} | {w.key for w in app.text_input}
    for job in ("job1", "job2"):
        assert {f"{job}_base", f"{job}_bonus1", f"{job}_bonus2"} <= keys
        assert {f"{job}_pension", f"{job}_tax_code"} <= keys


def test_a_shared_label_is_written_once_for_both_jobs(app):
    # The point of the grid: the label sits in its own column, so the two jobs
    # share it rather than each repeating it above their own box.
    labels = [m.value for m in app.markdown]
    assert labels.count("Annual base salary (£)") == 1
    assert labels.count("Tax code") == 1


@pytest.fixture
def default_result():
    return calculate_take_home(
        125_000,  # the default base
        [50_000, 0],  # the default bonuses
        rates.BANDS,
        rates.RATES,
        rates.NI_BANDS,
        rates.NI_RATES,
        reliefs=6_250,  # the default 5% pension on base
        tax_code="",
    )


def test_default_view_applies_the_100k_taper(app, default_result):
    # Regression guard. The tax-code box used to default to "1257L", which is
    # taken at face value and so skipped the taper — at the default £175k of
    # comp that understated tax by £5,656. Blank means "work it out for me".
    assert app.text_input[0].value == ""
    assert default_result.taxable_income == 168_750  # allowance fully tapered away

    # Both jobs default to the same package, so both columns show the figure.
    annual = f"{FIGURE} {money(default_result.take_home)}"
    assert figures(app).count(annual) == 2


def test_the_breakdown_is_annual_only(app):
    table = app.dataframe[0].value
    assert list(table.columns) == ["Item", "Job 1", "Job 2"]  # no monthly column
    assert list(table["Item"]) == [
        "Total compensation",
        "Pension",
        "Taxable income",
        "Personal allowance",
        "Income tax",
        "National Insurance",
        "Take rate",
    ]


def test_the_breakdown_reports_the_tapered_allowance_and_the_take_rate(
    app, default_result
):
    job1 = breakdown(app, "Job 1")
    # At £175k of comp the allowance is gone; showing it is the point of the row.
    assert job1["Personal allowance"] == "£0"
    assert job1["Take rate"] == percent(default_result.keep_rate)
    assert job1["Income tax"] == money(default_result.total_tax)
    assert job1["National Insurance"] == money(default_result.national_insurance)


@pytest.mark.parametrize("code", ["S1257L", "1257L M1"])
def test_an_unsupported_tax_code_shows_an_error_rather_than_crashing(app, code):
    app.text_input[0].set_value(code).run()
    assert not app.exception
    assert "Couldn't calculate take-home" in app.error[0].value


def test_the_tax_code_help_names_the_unsupported_kinds(app):
    help_text = app.text_input[0].help
    for kind in ("S/C", "K", "W1/M1/X"):
        assert kind in help_text
