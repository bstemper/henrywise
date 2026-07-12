"""Display formatting helpers."""

from __future__ import annotations


def money(amount: float) -> str:
    """Format pounds for display: 1234.5 -> '£1,235'."""
    return f"£{amount:,.0f}"


def percent(fraction: float) -> str:
    """Format a fraction as a percentage: 0.6055 -> '60.6%'."""
    return f"{fraction:.1%}"
