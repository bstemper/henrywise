import pytest

from henrywise.tax.models import MONTHS_PER_YEAR, TakeHomeResults, TaxBands, TaxRate


class TestTaxBands:
    def test_from_thresholds_keeps_basic_width_and_additional_threshold(self):
        bands = TaxBands.from_thresholds(12_570, 50_270, 125_140)
        assert bands.personal == 12_570
        assert bands.basic_band == 37_700
        # The additional-rate threshold is stored whole, not as a band width:
        # it's a fixed point of total income the tapering allowance moves under.
        assert bands.additional_threshold == 125_140

    @pytest.mark.parametrize(
        ("personal", "basic", "higher"),
        [
            (50_270, 12_570, 125_140),  # basic below personal
            (12_570, 125_140, 50_270),  # higher below basic
        ],
    )
    def test_out_of_order_thresholds_are_rejected(self, personal, basic, higher):
        with pytest.raises(ValueError, match="personal <= basic <= higher"):
            TaxBands.from_thresholds(personal, basic, higher)

    def test_negative_band_is_rejected(self):
        with pytest.raises(ValueError, match="basic_band >= 0"):
            TaxBands(12_570, -1, 125_140)

    def test_the_higher_band_widens_as_the_allowance_tapers(self):
        bands = TaxBands.from_thresholds(12_570, 50_270, 125_140)
        # £150k of taxable income, split with a full allowance vs none. Losing
        # the £12,570 allowance keeps that much out of the 45% band: the higher
        # band absorbs it instead, so less lands in additional.
        _, _, add_full = bands.split(150_000, allowance=12_570)
        _, _, add_none = bands.split(150_000, allowance=0)
        assert add_full - add_none == pytest.approx(12_570)

    def test_an_outsize_allowance_never_makes_the_higher_band_negative(self):
        bands = TaxBands.from_thresholds(12_570, 50_270, 125_140)
        # A tax code granting more allowance than the whole higher band: the
        # additional rate can't start below the basic band, so higher is empty.
        in_basic, in_higher, in_additional = bands.split(200_000, allowance=120_000)
        assert in_higher == 0
        assert in_basic + in_additional == 200_000


class TestTaxRate:
    def test_rate_outside_zero_to_one_is_rejected(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            TaxRate(0, 0.20, 1.4, 0.45)


class TestTakeHomeResultsInvariants:
    def test_component_larger_than_total_comp_is_rejected(self):
        with pytest.raises(ValueError, match="taxable_income"):
            TakeHomeResults(
                total_comp=100,
                taxable_income=200,
                basic_tax=0,
                higher_tax=0,
                additional_tax=0,
            )

    def test_higher_band_cannot_be_taxed_before_basic_is(self):
        # Bands fill bottom-up: you can't be in the higher band with an
        # untaxed basic band beneath it.
        with pytest.raises(ValueError, match="every lower band"):
            TakeHomeResults(
                total_comp=100_000,
                taxable_income=90_000,
                basic_tax=0,
                higher_tax=100,
                additional_tax=0,
            )

    def test_tax_without_taxable_income_is_rejected(self):
        with pytest.raises(ValueError, match="tax when taxable_income"):
            TakeHomeResults(
                total_comp=100,
                taxable_income=0,
                basic_tax=10,
                higher_tax=0,
                additional_tax=0,
            )

    def test_negative_bonus_is_rejected(self):
        with pytest.raises(ValueError, match="each bonus >= 0"):
            TakeHomeResults(
                total_comp=100,
                taxable_income=0,
                basic_tax=0,
                higher_tax=0,
                additional_tax=0,
                bonuses=(-1,),
            )


class TestMonthlySplit:
    def result(self, base, bonuses, tax=0.0, reliefs=0.0):
        total = base + sum(bonuses)
        return TakeHomeResults(
            total_comp=total,
            taxable_income=total,
            basic_tax=tax,
            higher_tax=0,
            additional_tax=0,
            reliefs=reliefs,
            annual_base=base,
            bonuses=tuple(bonuses),
        )

    def test_no_bonuses_means_twelve_equal_months(self):
        r = self.result(60_000, [], tax=12_000)
        assert r.bonus_months == []
        assert r.non_bonus_month == pytest.approx(r.take_home / MONTHS_PER_YEAR)

    def test_bonus_month_is_a_normal_month_plus_that_bonus_net(self):
        r = self.result(120_000, [30_000], tax=0)
        # No tax, no reliefs → keep rate is 1.
        assert r.non_bonus_month == pytest.approx(10_000)
        assert r.bonus_months == [pytest.approx(40_000)]

    @pytest.mark.parametrize(
        ("base", "bonuses", "tax", "reliefs"),
        [
            (125_000, [50_000], 57_000, 6_250),
            (80_000, [10_000, 25_000], 20_000, 4_000),
            (40_000, [], 6_000, 0),
        ],
    )
    def test_the_months_sum_back_to_the_annual_take_home(
        self, base, bonuses, tax, reliefs
    ):
        # The load-bearing invariant: normal months + bonus months == the year.
        r = self.result(base, bonuses, tax=tax, reliefs=reliefs)
        normal_months = MONTHS_PER_YEAR - len(bonuses)
        total = r.non_bonus_month * normal_months + sum(r.bonus_months)
        assert total == pytest.approx(r.take_home)

    def test_keep_rate_of_zero_comp_is_zero_not_a_crash(self):
        r = self.result(0, [])
        assert r.keep_rate == 0.0
        assert r.non_bonus_month == 0.0
