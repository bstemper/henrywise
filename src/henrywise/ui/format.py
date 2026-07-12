"""Display formatting helpers."""

from __future__ import annotations

from henrywise.tax.models import MONTHS_PER_YEAR


def money(amount: float) -> str:
    """Format pounds for display: 1234.5 -> '£1,235'."""
    return f"£{amount:,.0f}"


def monthly(annual_amount: float) -> str:
    """Format an annual figure as its even monthly share."""
    return money(annual_amount / MONTHS_PER_YEAR)
