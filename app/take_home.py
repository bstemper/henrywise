from __future__ import annotations

import re
from dataclasses import dataclass

# Adjusted net income where the Personal Allowance starts tapering.
PERSONAL_ALLOWANCE_TAPER_START = 100_000
# £1 of allowance lost per £2 of income above the start.
PERSONAL_ALLOWANCE_TAPER_DIVISOR = 2


@dataclass
class TaxBands:
    personal: int  # the Personal Allowance
    basic_band: int  # width of the basic-rate band
    higher_band: int  # width of the higher-rate band

    def __post_init__(self):
        for name in ("personal", "basic_band", "higher_band"):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"Need {name} >= 0, got {value}.")

    @classmethod
    def from_thresholds(cls, personal: int, basic: int, higher: int) -> "TaxBands":
        """Build from the published cumulative thresholds (personal <= basic <= higher)."""
        if basic < personal or higher < basic:
            raise ValueError(
                f"We need personal <= basic <= higher, but got {personal=}, {basic=}, {higher=}."
            )
        return cls(personal, basic - personal, higher - basic)


@dataclass
class TaxRate:
    personal: float
    basic: float
    higher: float
    additional: float

    def __post_init__(self):
        for name in ("personal", "basic", "higher", "additional"):
            rate = getattr(self, name)
            if rate < 0 or rate > 1:
                raise ValueError(f"Need {name} rate between 0 and 1, got {rate}.")


# Trailing "emergency" (non-cumulative) marker — irrelevant to an annual total.
_EMERGENCY = re.compile(r"\s*(W1|M1|X)$")


def parse_tax_code(raw: str) -> int:
    """Return the tax-free personal allowance (£) a UK PAYE tax code grants.

    Supports the numeric codes: ``1257L`` and friends (suffix L/M/N/T), plus
    ``0T`` (zero allowance). A trailing emergency marker (``W1``/``M1``/``X``)
    is accepted but ignored.

    Region-prefixed codes (``S`` for Scotland, ``C`` for Wales) are rejected:
    Scotland has its own bands and rates that this calculator doesn't model,
    so accepting one would silently apply the wrong (rest-of-UK) tax.

    K codes (a negative allowance) and the whole-regime codes (NT, BR, D0, D1)
    are not supported.
    """
    code = raw.strip().upper()
    if not code:
        raise ValueError("Tax code is empty.")

    # A region prefix means a tax regime we don't model — refuse rather than
    # silently taxing a Scottish/Welsh code at rest-of-UK rates.
    if code[0] in ("S", "C") and len(code) > 1:
        raise ValueError(f"Region-prefixed codes aren't supported, got {raw!r}.")
    # Drop a non-cumulative "emergency" marker; it doesn't change the year's total.
    code = _EMERGENCY.sub("", code).strip()

    if code.startswith("K"):
        raise ValueError(f"K codes aren't supported, got {raw!r}.")
    match = re.fullmatch(r"(\d+)[LMNT]?", code)  # also matches "0T"
    if match:
        return int(match.group(1)) * 10
    raise ValueError(f"Unrecognised tax code {raw!r}.")


@dataclass
class TakeHomeResults:
    total_comp: int
    taxable_income: int
    basic_tax: int
    higher_tax: int
    additional_tax: int
    reliefs: int = 0  # money diverted pre-tax, e.g. a pension contribution

    def __post_init__(self):
        if self.total_comp < 0:
            raise ValueError(f"Need total_comp >= 0, got {self.total_comp}.")

        # Every component sits between zero and total compensation.
        for name in (
            "taxable_income",
            "basic_tax",
            "higher_tax",
            "additional_tax",
            "reliefs",
        ):
            value = getattr(self, name)
            if not 0 <= value <= self.total_comp:
                raise ValueError(
                    f"Need 0 <= {name} <= total_comp ({self.total_comp}), got {value}."
                )

        # Tax bands fill from the bottom up: a band is only taxed once every
        # lower band is.
        seen_empty = False
        for name in ("basic_tax", "higher_tax", "additional_tax"):
            tax = getattr(self, name)
            if tax > 0 and seen_empty:
                raise ValueError(
                    f"Cannot have {name} unless every lower band is taxed."
                )
            seen_empty = seen_empty or tax == 0

        if self.total_tax > 0 and self.taxable_income <= 0:
            raise ValueError("Cannot have tax when taxable_income <= 0.")

    @property
    def total_tax(self):
        return self.basic_tax + self.higher_tax + self.additional_tax

    @property
    def take_home(self):
        # Spendable cash: what's left after tax and after money diverted pre-tax
        # (e.g. into a pension) has come out.
        return self.total_comp - self.total_tax - self.reliefs


def effective_personal_allowance(adjusted_net_income: int, base_allowance: int) -> int:
    excess = max(adjusted_net_income - PERSONAL_ALLOWANCE_TAPER_START, 0)
    return max(base_allowance - excess // PERSONAL_ALLOWANCE_TAPER_DIVISOR, 0)


def calculate_take_home(
    annual_base: int,
    annual_bonus: int,
    bands: TaxBands,
    tax_rate: TaxRate,
    reliefs: int = 0,
    tax_code: str | None = None,
) -> TakeHomeResults:
    total_comp = annual_base + annual_bonus
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
    )
