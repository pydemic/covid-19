from covid.utils import fmt, pc, pm, p10k


class TestUtilityFunctions:
    def test_format_functions(self):
        assert fmt(1_000_000) == '1.0mi'
        assert fmt(42_123.0) == '42,123.0'
        assert fmt(42_123) == '42,123'
