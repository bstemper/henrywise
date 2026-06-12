from dataclasses import dataclass


@dataclass
class IncomeThreshold:
    personal: int
    basic: int
    higher: int

    def __post_init__(self):
        if self.basic < self.personal or self.higher < self.basic:
            raise ValueError(
                f"We need personal <= basic <= higher, but got {self.personal=}, {self.basic=}, {self.higher=}."
            )

    @property
    def basic_band(self) -> int:
        return self.basic - self.personal

    @property
    def higher_band(self) -> int:
        return self.higher - self.basic


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

    def __post_init__(self):
        for name in (
            "total_comp",
            "taxable_income",
            "basic_tax",
            "higher_tax",
            "additional_tax",
        ):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f"Need {name} >= 0, got {value}.")

        for name in ("taxable_income", "basic_tax", "higher_tax", "additional_tax"):
            value = getattr(self, name)
            if value > self.total_comp:
                raise ValueError(
                    f"Need {name} <= total_comp ({self.total_comp}), got {value}."
                )

        if self.higher_tax > 0 and self.basic_tax <= 0:
            raise ValueError("Cannot have higher_tax without basic_tax.")
        if self.additional_tax > 0 and (self.basic_tax <= 0 or self.higher_tax <= 0):
            raise ValueError(
                "Cannot have additional_tax without basic_tax and higher_tax."
            )

        if self.total_tax > 0 and self.taxable_income <= 0:
            raise ValueError("Cannot have tax when taxable_income <= 0.")

    @property
    def total_tax(self):
        return self.basic_tax + self.higher_tax + self.additional_tax

    @property
    def take_home(self):
        return self.total_comp - self.total_tax


def calculate_take_home(
    annual_base: int,
    annual_bonus: int,
    threshold: IncomeThreshold,
    tax_rate: TaxRate,
) -> TakeHomeResults:
    total_comp = annual_base + annual_bonus
    taxable_income = max(total_comp - threshold.personal, 0)

    # Split taxable income into the slice that falls in each band.
    income_in_basic = min(taxable_income, threshold.basic_band)
    income_in_higher = min(
        max(taxable_income - threshold.basic_band, 0), threshold.higher_band
    )
    income_in_additional = max(
        taxable_income - threshold.basic_band - threshold.higher_band, 0
    )

    return TakeHomeResults(
        total_comp,
        taxable_income,
        income_in_basic * tax_rate.basic,
        income_in_higher * tax_rate.higher,
        income_in_additional * tax_rate.additional,
    )
