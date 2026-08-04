"""The tax year's numbers. THIS IS THE FILE YOU EDIT EACH APRIL.

Nothing else in the codebase should contain a number that means pounds or a
tax rate. If you find one elsewhere, it belongs here.

Figures are for the 2026/27 UK tax year, rest of UK (England, Wales, NI).
"""

from __future__ import annotations

from henrywise.tax.models import NIBands, NIRate, TaxBands, TaxRate

LABEL = "2026/27"

# Income tax — rest of UK. Published cumulative thresholds.
BANDS = TaxBands.from_thresholds(
    personal=12_570,
    basic=50_270,
    higher=125_140,
)
RATES = TaxRate(personal=0.0, basic=0.20, higher=0.40, additional=0.45)

# National Insurance — Class 1 employee, category A (the ordinary case).
# The Primary Threshold and Upper Earnings Limit, both frozen since 2022.
NI_BANDS = NIBands.from_thresholds(
    primary=12_570,
    upper=50_270,
)
# 8% between the two thresholds, 2% on everything above the UEL.
NI_RATES = NIRate(main=0.08, upper=0.02)

# Adjusted net income where the Personal Allowance starts tapering.
PERSONAL_ALLOWANCE_TAPER_START = 100_000
# £1 of allowance lost per £2 of income above the start.
PERSONAL_ALLOWANCE_TAPER_DIVISOR = 2
