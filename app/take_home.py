from dataclasses import dataclass, replace


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


# Adjusted net income where the Personal Allowance starts tapering.
TAPER_START = 100_000
# £1 of allowance lost per £2 of income above the start.
TAPER_DIVISOR = 2


def effective_personal_allowance(adjusted_net_income: int, base_allowance: int) -> int:
    """Personal Allowance after the >£100k taper (£1 lost per £2 over the threshold)."""
    excess = max(adjusted_net_income - TAPER_START, 0)
    return max(base_allowance - excess // TAPER_DIVISOR, 0)


def tapered_bands(bands: TaxBands, adjusted_net_income: int) -> TaxBands:
    """Rebuild the threshold with the tapered allowance, keeping band widths fixed.

    Only the allowance moves; the basic/higher band widths are fixed by law, so
    the gross boundaries slide down with it.
    """
    pa = effective_personal_allowance(adjusted_net_income, bands.personal)
    return replace(bands, personal=pa)


def calculate_take_home(
    annual_base: int,
    annual_bonus: int,
    bands: TaxBands,
    tax_rate: TaxRate,
    reliefs: int = 0,
) -> TakeHomeResults:
    total_comp = annual_base + annual_bonus
    adjusted_net_income = total_comp - reliefs
    bands = tapered_bands(bands, adjusted_net_income)
    taxable_income = max(total_comp - bands.personal - reliefs, 0)

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
