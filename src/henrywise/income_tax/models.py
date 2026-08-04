"""Value types for a take-home calculation.

Pure data + invariants. Nothing here knows about Streamlit, or about any
particular tax year — the year's numbers live in :mod:`henrywise.tax.rates`.
"""

from __future__ import annotations

from dataclasses import dataclass

# Pay is modelled as twelve equal months, with each bonus landing in one month.
MONTHS_PER_YEAR = 12


@dataclass
class TaxBands:
    personal: int  # the statutory Personal Allowance, before any taper
    basic_band: int  # width of the basic-rate band (the "basic rate limit")
    additional_threshold: int  # total income at which the additional rate begins

    def __post_init__(self):
        for name in ("personal", "basic_band", "additional_threshold"):
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
        return cls(personal, basic - personal, higher)

    def split(
        self, taxable_income: float, allowance: float
    ) -> tuple[float, float, float]:
        """Slice taxable income into the basic / higher / additional bands.

        ``allowance`` is the Personal Allowance actually applied — tapered, or
        read off a tax code. It matters because the additional-rate threshold is
        a fixed point of *total* income (``additional_threshold``, £125,140): as
        the allowance tapers away above £100k the threshold stays put while
        taxable income rises to meet it, so the higher-rate band widens to fill
        the gap. Treating that band as a fixed width instead tips income into the
        additional rate too early and overtaxes everyone past the taper.
        """
        # The additional rate starts at a fixed total income; in taxable-income
        # terms that point sits `allowance` lower. Never below the basic band.
        additional_start = max(self.additional_threshold - allowance, self.basic_band)
        in_basic = min(taxable_income, self.basic_band)
        in_higher = min(
            max(taxable_income - self.basic_band, 0),
            additional_start - self.basic_band,
        )
        in_additional = max(taxable_income - additional_start, 0)
        return in_basic, in_higher, in_additional


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
class NIBands:
    """National Insurance earnings bands. Nothing to do with the tax bands.

    NI ignores the Personal Allowance and has its own threshold, so it can't
    reuse :class:`TaxBands`.
    """

    primary_threshold: int  # earnings below this pay no NI at all
    main_band: int  # width of the band charged at the main rate

    def __post_init__(self):
        for name in ("primary_threshold", "main_band"):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"Need {name} >= 0, got {value}.")

    @classmethod
    def from_thresholds(cls, primary: int, upper: int) -> "NIBands":
        """Build from the published thresholds: the PT and the UEL."""
        if upper < primary:
            raise ValueError(f"We need primary <= upper, but got {primary=}, {upper=}.")
        return cls(primary, upper - primary)


@dataclass
class NIRate:
    main: float  # between the primary threshold and the upper earnings limit
    upper: float  # above the upper earnings limit

    def __post_init__(self):
        for name in ("main", "upper"):
            rate = getattr(self, name)
            if rate < 0 or rate > 1:
                raise ValueError(f"Need {name} rate between 0 and 1, got {rate}.")


@dataclass
class TakeHomeResults:
    total_comp: float
    taxable_income: float
    basic_tax: float
    higher_tax: float
    additional_tax: float
    reliefs: float = 0  # money diverted pre-tax, e.g. a pension contribution
    national_insurance: float = 0  # Class 1 employee NI on earnings after reliefs
    annual_base: float = 0  # gross base salary, before reliefs
    bonuses: tuple[float, ...] = ()  # individual bonuses actually paid, in order
    # The allowance actually applied: tapered, or read off a tax code. Not
    # bounded by total_comp — someone earning £5k still has the full allowance,
    # they just can't use all of it.
    personal_allowance: float = 0

    def __post_init__(self):
        if self.total_comp < 0:
            raise ValueError(f"Need total_comp >= 0, got {self.total_comp}.")
        if self.personal_allowance < 0:
            raise ValueError(
                f"Need personal_allowance >= 0, got {self.personal_allowance}."
            )

        # Every component sits between zero and total compensation.
        for name in (
            "taxable_income",
            "basic_tax",
            "higher_tax",
            "additional_tax",
            "reliefs",
            "national_insurance",
            "annual_base",
        ):
            value = getattr(self, name)
            if not 0 <= value <= self.total_comp:
                raise ValueError(
                    f"Need 0 <= {name} <= total_comp ({self.total_comp}), got {value}."
                )

        for bonus in self.bonuses:
            if bonus < 0:
                raise ValueError(f"Need each bonus >= 0, got {bonus}.")

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
    def total_tax(self) -> float:
        return self.basic_tax + self.higher_tax + self.additional_tax

    @property
    def take_home(self) -> float:
        # Spendable cash: what's left after income tax and National Insurance,
        # and after money diverted pre-tax (e.g. into a pension) has come out.
        return self.total_comp - self.total_tax - self.national_insurance - self.reliefs

    @property
    def keep_rate(self) -> float:
        """Fraction of each gross pound kept, after tax and pre-tax diversions."""
        return self.take_home / self.total_comp if self.total_comp else 0.0

    @property
    def non_bonus_month(self) -> float:
        """Take-home in a month with no bonus paid.

        We apply the overall keep rate to every pound, so a normal month
        reflects the true tax bracket rather than taxing the base alone at the
        low bands it would occupy on its own.
        """
        return self.annual_base * self.keep_rate / MONTHS_PER_YEAR

    @property
    def bonus_months(self) -> list[float]:
        """Take-home for each bonus month: a normal month plus that bonus's net.

        One entry per bonus paid, in order. A bonus lands in a single month, so
        its whole net is added there; with the remaining normal months these sum
        to the annual take-home.
        """
        return [self.non_bonus_month + bonus * self.keep_rate for bonus in self.bonuses]
