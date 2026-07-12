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
    total_comp: float
    taxable_income: float
    basic_tax: float
    higher_tax: float
    additional_tax: float
    reliefs: float = 0  # money diverted pre-tax, e.g. a pension contribution
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
        # Spendable cash: what's left after tax and after money diverted pre-tax
        # (e.g. into a pension) has come out.
        return self.total_comp - self.total_tax - self.reliefs

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
