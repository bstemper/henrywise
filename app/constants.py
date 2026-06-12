from dataclasses import dataclass


@dataclass
class IncomeThresholds:
    personal: int
    basic: int
    higher: int


@dataclass
class TaxRate:
    personal: int
    basic: int
    higher: int
    additional: int


threshold_2027 = IncomeThresholds(12_570, 50_270, 125_140)
tax_rates_2027 = TaxRate(0, 20, 40, 45)
