"""Smoke tests for the Streamlit app, driven through Streamlit's own AppTest."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from henrywise.tax import rates
from henrywise.tax.take_home import calculate_take_home

APP = str(Path(__file__).parent.parent / "src" / "henrywise" / "ui" / "app.py")


@pytest.fixture
def app():
    return AppTest.from_file(APP, default_timeout=30).run()


def test_app_renders_without_error(app):
    assert not app.exception
    assert app.title[0].value == "💷 HenryWise UK"
    assert not app.error


def test_both_job_panels_render(app):
    subheaders = [s.value for s in app.subheader]
    assert "Job 1 Details" in subheaders
    assert "Job 2 Details" in subheaders


def test_default_view_applies_the_100k_taper(app):
    # Regression guard. The tax-code box used to default to "1257L", which is
    # taken at face value and so skipped the taper — at the default £175k of
    # comp that understated tax by £5,656. Blank means "work it out for me".
    assert app.text_input[0].value == ""

    expected = calculate_take_home(
        125_000,  # the default base
        [50_000, 0],  # the default bonuses
        rates.BANDS,
        rates.RATES,
        reliefs=6_250,  # the default 5% pension on base
        tax_code="",
    )
    assert expected.taxable_income == 168_750  # allowance fully tapered away
    assert app.metric[2].label == "Annual"
    assert app.metric[2].value == f"£{expected.take_home:,.0f}"


def test_an_unsupported_tax_code_shows_an_error_rather_than_crashing(app):
    app.text_input[0].set_value("S1257L").run()
    assert not app.exception
    assert "Couldn't calculate take-home" in app.error[0].value
