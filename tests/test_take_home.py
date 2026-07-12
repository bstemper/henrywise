import pytest

from henrywise.tax import rates
from henrywise.tax.take_home import calculate_take_home, effective_personal_allowance

BANDS = rates.BANDS  # personal 12,570 · basic width 37,700 · higher width 74,870
RATES = rates.RATES  # 20% / 40% / 45%


def take_home(base, bonuses=(), reliefs=0, tax_code=None):
    return calculate_take_home(base, bonuses, BANDS, RATES, reliefs, tax_code)


class TestPersonalAllowanceTaper:
    @pytest.mark.parametrize(
        ("income", "expected"),
        [
            (50_000, 12_570),  # well below the taper
            (100_000, 12_570),  # exactly at the threshold — no taper yet
            (110_000, 7_570),  # £10k over → lose £5k
            (125_140, 0),  # fully tapered away
            (200_000, 0),  # clamped at zero, never negative
        ],
    )
    def test_allowance_tapers_by_one_pound_per_two_over_100k(self, income, expected):
        assert effective_personal_allowance(income, BANDS.personal) == expected

    def test_taper_rounds_down_to_whole_pounds(self):
        assert effective_personal_allowance(100_001, BANDS.personal) == 12_570

    def test_the_allowance_applied_is_reported(self):
        # The UI shows this: at £175k it's the difference between "we tapered it
        # away" and "we forgot it".
        assert take_home(50_000).personal_allowance == 12_570
        assert take_home(200_000).personal_allowance == 0
        assert take_home(60_000, tax_code="1000L").personal_allowance == 10_000

    def test_a_low_earner_keeps_an_allowance_bigger_than_their_pay(self):
        r = take_home(5_000)
        assert r.personal_allowance == 12_570  # more than they earn — not an error
        assert r.taxable_income == 0


class TestBandBoundaries:
    def test_income_below_the_allowance_is_untaxed(self):
        r = take_home(10_000)
        assert r.taxable_income == 0
        assert r.total_tax == 0
        assert r.take_home == 10_000

    def test_basic_rate_only(self):
        r = take_home(30_000)
        assert r.taxable_income == 17_430
        assert r.total_tax == pytest.approx(17_430 * 0.20)
        assert r.higher_tax == 0

    def test_exactly_at_the_top_of_the_basic_band(self):
        r = take_home(50_270)
        assert r.basic_tax == pytest.approx(37_700 * 0.20)
        assert r.higher_tax == 0
        assert r.additional_tax == 0

    def test_higher_rate(self):
        r = take_home(80_000)
        assert r.basic_tax == pytest.approx(37_700 * 0.20)
        assert r.higher_tax == pytest.approx((80_000 - 50_270) * 0.40)
        assert r.additional_tax == 0

    def test_additional_rate_with_a_fully_tapered_allowance(self):
        r = take_home(200_000)
        # Allowance is tapered to nothing, so all £200k is taxable.
        assert r.taxable_income == 200_000
        assert r.basic_tax == pytest.approx(37_700 * 0.20)
        assert r.higher_tax == pytest.approx(74_870 * 0.40)
        assert r.additional_tax == pytest.approx((200_000 - 37_700 - 74_870) * 0.45)

    def test_zero_income_is_handled(self):
        r = take_home(0)
        assert r.total_comp == 0
        assert r.take_home == 0
        assert r.keep_rate == 0.0


class TestBonuses:
    def test_tax_depends_only_on_total_comp_not_how_it_is_split(self):
        one_lump = take_home(175_000)
        split = take_home(125_000, [30_000, 20_000])
        assert split.total_tax == pytest.approx(one_lump.total_tax)

    def test_zero_bonuses_are_not_counted_as_bonus_months(self):
        r = take_home(100_000, [50_000, 0])
        assert r.bonuses == (50_000,)
        assert len(r.bonus_months) == 1

    def test_two_bonuses_give_two_bonus_months(self):
        r = take_home(100_000, [30_000, 20_000])
        assert len(r.bonus_months) == 2


class TestReliefs:
    def test_salary_sacrifice_reduces_taxable_income(self):
        without = take_home(60_000)
        with_pension = take_home(60_000, reliefs=6_000)
        assert with_pension.taxable_income == without.taxable_income - 6_000
        assert with_pension.total_tax < without.total_tax

    def test_pension_comes_out_of_take_home_as_well_as_tax(self):
        r = take_home(60_000, reliefs=6_000)
        # Take-home is spendable cash: the pension has left the pay packet.
        assert r.take_home == pytest.approx(60_000 - r.total_tax - 6_000)

    def test_relief_can_restore_a_tapered_allowance(self):
        # £110k with a £10k sacrifice drops adjusted net income back to £100k,
        # recovering the full allowance.
        r = take_home(110_000, reliefs=10_000)
        assert r.taxable_income == 110_000 - 12_570 - 10_000


class TestTaxCode:
    def test_blank_code_uses_the_tapered_standard_allowance(self):
        assert take_home(200_000, tax_code="").taxable_income == 200_000
        assert take_home(200_000, tax_code=None).taxable_income == 200_000

    def test_an_explicit_code_sets_the_allowance_directly(self):
        r = take_home(60_000, tax_code="1000L")
        assert r.taxable_income == 50_000

    def test_an_explicit_code_overrides_the_taper(self):
        # A real HMRC code already has any taper baked into its number, so we
        # take it at face value and do NOT taper it again. Consequence: entering
        # "1257L" at £200k grants the full allowance.
        r = take_home(200_000, tax_code="1257L")
        assert r.taxable_income == 200_000 - 12_570

    def test_an_unsupported_code_raises(self):
        with pytest.raises(ValueError):
            take_home(60_000, tax_code="S1257L")
