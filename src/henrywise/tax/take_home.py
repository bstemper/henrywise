"""The take-home calculation itself: gross comp in, annual + monthly split out."""

from __future__ import annotations

from collections.abc import Sequence

from henrywise.tax.codes import parse_tax_code
from henrywise.tax.models import TakeHomeResults, TaxBands, TaxRate
from henrywise.tax.rates import (
    PERSONAL_ALLOWANCE_TAPER_DIVISOR,
    PERSONAL_ALLOWANCE_TAPER_START,
)


def effective_personal_allowance(
    adjusted_net_income: float, base_allowance: int
) -> float:
    excess = max(adjusted_net_income - PERSONAL_ALLOWANCE_TAPER_START, 0)
    return max(base_allowance - excess // PERSONAL_ALLOWANCE_TAPER_DIVISOR, 0)


def calculate_take_home(
    annual_base: float,
    annual_bonuses: Sequence[float],
    bands: TaxBands,
    tax_rate: TaxRate,
    reliefs: float = 0,
    tax_code: str | None = None,
) -> TakeHomeResults:
    """Compute annual take-home plus a per-month cash-flow split.

    ``annual_bonuses`` is the list of bonus payments made during the year, each
    paid in its own month. Tax is annual, so only their total affects it, but
    the result also exposes the take-home for a normal month and for each bonus
    month (see ``TakeHomeResults``).
    """
    paid_bonuses = tuple(b for b in annual_bonuses if b > 0)
    total_comp = annual_base + sum(annual_bonuses)
    adjusted_net_income = total_comp - reliefs

    if not tax_code or not tax_code.strip():  # None/blank UI field → standard allowance
        personal = effective_personal_allowance(adjusted_net_income, bands.personal)
    else:
        personal = parse_tax_code(tax_code)

    taxable_income = max(total_comp - personal - reliefs, 0)

    # Split taxable income into the slice that falls in each band.
    income_in_basic = min(taxable_income, bands.basic_band)
    income_in_higher = min(max(taxable_income - bands.basic_band, 0), bands.higher_band)
    income_in_additional = max(taxable_income - bands.basic_band - bands.higher_band, 0)

    return TakeHomeResults(
        total_comp,
        taxable_income,
        income_in_basic * tax_rate.basic,
        income_in_higher * tax_rate.higher,
        income_in_additional * tax_rate.additional,
        reliefs,
        annual_base=annual_base,
        bonuses=paid_bonuses,
    )
