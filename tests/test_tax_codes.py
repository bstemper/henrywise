import pytest

from henrywise.tax.tax_code import parse_raw_string


class TestNumericCodes:
    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            ("1257L", 12_570),
            ("1257", 12_570),  # bare number, no suffix
            ("0T", 0),  # zero allowance
            ("1000L", 10_000),
            ("500T", 5_000),
        ],
    )
    def test_allowance_is_the_number_times_ten(self, code, expected):
        assert parse_raw_string(code) == expected

    def test_is_case_insensitive_and_ignores_surrounding_space(self):
        assert parse_raw_string("  1257l  ") == 12_570

    @pytest.mark.parametrize("code", ["1257M", "1257N", "1257T"])
    def test_suffix_letter_does_not_change_the_allowance(self, code):
        # A real M/N code already has the £1,260 marriage-allowance transfer
        # baked into its number, so the suffix must not adjust it again.
        assert parse_raw_string(code) == 12_570


class TestEmergencyMarkers:
    @pytest.mark.parametrize("code", ["1257L W1", "1257LW1", "1257L M1", "1257LX"])
    def test_emergency_codes_are_rejected(self, code):
        # A non-cumulative code taxes each period alone. With a bonus in one
        # month that changes the monthly split — and the annual total — from our
        # cumulative-basis estimate, so we refuse rather than mislead.
        with pytest.raises(ValueError, match="Emergency"):
            parse_raw_string(code)

    def test_a_marriage_code_ending_in_m_is_not_mistaken_for_m1(self):
        # "1257M" ends in M, not the "M1" marker — it's a valid Marriage
        # Allowance code and must still parse.
        assert parse_raw_string("1257M") == 12_570


class TestRejectedCodes:
    def test_empty_code_is_rejected(self):
        with pytest.raises(ValueError, match="empty"):
            parse_raw_string("   ")

    @pytest.mark.parametrize("code", ["S1257L", "C1257L", "s1257l"])
    def test_region_prefixed_codes_are_rejected(self, code):
        # Refuse rather than silently taxing a Scottish/Welsh code at rUK rates.
        with pytest.raises(ValueError, match="Region-prefixed"):
            parse_raw_string(code)

    def test_k_codes_are_rejected(self):
        with pytest.raises(ValueError, match="K codes"):
            parse_raw_string("K100")

    @pytest.mark.parametrize("code", ["BR", "D0", "D1", "NT", "100K", "ABC", "L1257"])
    def test_unsupported_and_malformed_codes_are_rejected(self, code):
        with pytest.raises(ValueError):
            parse_raw_string(code)
