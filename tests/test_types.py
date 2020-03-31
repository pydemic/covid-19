from covid import types as tt

import pytest


class TestDescriptors:
    @pytest.fixture(scope="class")
    def cls(self):
        class Cls:
            cached = tt.cached(lambda x: 42)

        return Cls

    def test_cached_descriptors(self, cls):
        obj = cls()
        assert obj.cached == 42
        obj.cached = 0
        assert obj.cached == 0
