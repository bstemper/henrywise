"""The take-home calculation itself: gross comp in, annual + monthly split out."""

from __future__ import annotations

from collections.abc import Sequence

from henrywise.tax.codes import parse_tax_code
from henrywise.tax.models import NIBands, NIRate, TakeHomeResults, TaxBands, TaxRate
from henrywise.tax.rates import (
    PERSONAL_ALLOWANCE_TAPER_DIVISOR,
    PERSONAL_ALLOWANCE_TAPER_START,
)


def effective_personal_allowance(
    adjusted_net_income: float, base_allowance: int
) -> float:
    excess = max(adjusted_net_income - PERSONAL_ALLOWANCE_TAPER_START, 0)
    return max(base_allowance - excess // PERSONAL_ALLOWANCE_TAPER_DIVISOR, 0)


def national_insurance(earnings: float, bands: NIBands, ni_rate: NIRate) -> float:
    """Class 1 employee NI on a year's earnings.

    NI knows nothing about the Personal Allowance or a tax code: it starts at
    its own threshold, and unlike income tax the rate *drops* above the upper
    limit. ``earnings`` is pay after salary sacrifice — sacrificed pay was
    never earnings, which is why sacrifice saves NI as well as tax.
    """
    above_threshold = max(earnings - bands.primary_threshold, 0)
    in_main = min(above_threshold, bands.main_band)
    above_upper_limit = max(above_threshold - bands.main_band, 0)
    return in_main * ni_rate.main + above_upper_limit * ni_rate.upper


def calculate_take_home(
    annual_base: float,
    annual_bonuses: Sequence[float],
    bands: TaxBands,
    tax_rate: TaxRate,
    ni_bands: NIBands,
    ni_rate: NIRate,
    reliefs: float = 0,
    tax_code: str | None = None,
) -> TakeHomeResults:
    """Compute annual take-home plus a per-month cash-flow split.

    ``annual_bonuses`` is the list of bonus payments made during the year, each
    paid in its own month. Tax is annual, so only their total affects it, but
    the result also exposes the take-home for a normal month and for each bonus
    month (see ``TakeHomeResults``).

    NI is charged here on the year's earnings. Real NI is worked out per pay
    period, so a lumpy bonus month is charged slightly differently in practice;
    for a full year on a steady salary the two agree.
    """
    paid_bonuses = tuple(b for b in annual_bonuses if b > 0)
    total_comp = annual_base + sum(annual_bonuses)
    adjusted_net_income = total_comp - reliefs

    if not tax_code or not tax_code.strip():  # None/blank UI field → standard allowance
        personal = effective_personal_allowance(adjusted_net_income, bands.personal)
    else:
        personal = parse_tax_code(tax_code)

    taxable_income = max(total_comp - personal - reliefs, 0)

    # The band split depends on the allowance actually applied: as it tapers,
    # the higher band widens up to the fixed additional-rate threshold.
    income_in_basic, income_in_higher, income_in_additional = bands.split(
        taxable_income, personal
    )

    return TakeHomeResults(
        total_comp,
        taxable_income,
        income_in_basic * tax_rate.basic,
        income_in_higher * tax_rate.higher,
        income_in_additional * tax_rate.additional,
        reliefs,
        # Earnings for NI are the same pay the taper looks at: gross, less what
        # was sacrificed before it ever became earnings.
        national_insurance=national_insurance(adjusted_net_income, ni_bands, ni_rate),
        annual_base=annual_base,
        bonuses=paid_bonuses,
        personal_allowance=personal,
    )
