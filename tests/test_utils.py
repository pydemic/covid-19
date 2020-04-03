import locale

import pytest

from covid.utils import fmt


class TestUtilityFunctions:
    def test_format_functions_en_US(self):
        try:
            locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
        except locale.Error:
            return pytest.skip()

        assert fmt(0.10) == "0.1"
        assert fmt(0.12) == "0.12"
        assert fmt(0.01) == "0.01"
        assert fmt(0.012) == "0.012"
        assert fmt(0.0123) == "0.012"
        assert fmt(0.00123) == "1.23e-03"
        assert fmt(0.0012) == "1.2e-03"
        assert fmt(1.2341) == "1.23"
        assert fmt(12.341) == "12.34"
        assert fmt(123.41) == "123.4"
        assert fmt(1234) == "1,234"
        assert fmt(1234.5) == "1,234"
        assert fmt(42_123.1) == "42,123"
        assert fmt(42_123) == "42,123"
        assert fmt(1_000_000) == "1M"
        assert fmt(10_000_000) == "10M"
        assert fmt(12_000_000) == "12M"
        assert fmt(12_300_000) == "12.3M"
        assert fmt(12_340_000) == "12.34M"
        assert fmt(12_341_000) == "12.34M"
        assert fmt(-12_341_000) == "-12.34M"
        assert fmt(123_456_000) == "123.5M"
        assert fmt(1_234_567_000) == "1.23B"

    def test_format_functions_pt_BR(self):
        try:
            locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
        except locale.Error:
            return pytest.skip()

        assert fmt(0.10) == "0,1"
        assert fmt(0.12) == "0,12"
        assert fmt(0.01) == "0,01"
        assert fmt(0.012) == "0,012"
        assert fmt(0.0123) == "0,012"
        assert fmt(0.00123) == "1,23e-03"
        assert fmt(0.0012) == "1,2e-03"
        assert fmt(1.2341) == "1,23"
        assert fmt(12.341) == "12,34"
        assert fmt(123.41) == "123,4"
        assert fmt(1234) == "1.234"
        assert fmt(1234.5) == "1.234"
        assert fmt(42_123.1) == "42.123"
        assert fmt(42_123) == "42.123"
        assert fmt(1_000_000) == "1M"
        assert fmt(10_000_000) == "10M"
        assert fmt(12_000_000) == "12M"
        assert fmt(12_300_000) == "12,3M"
        assert fmt(12_340_000) == "12,34M"
        assert fmt(12_341_000) == "12,34M"
        assert fmt(-12_341_000) == "-12,34M"
        assert fmt(123_456_000) == "123,5M"
        assert fmt(1_234_567_000) == "1,23B"
