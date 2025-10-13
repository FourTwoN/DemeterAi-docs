"""Sample unit tests to verify pytest configuration.

These tests verify:
- Basic pytest functionality
- Test markers work correctly
- Fixtures are accessible
"""

import pytest


@pytest.mark.unit
def test_sample_assertion():
    """Test basic assertion works."""
    assert 1 + 1 == 2


@pytest.mark.unit
def test_sample_data_fixture(sample_warehouse):
    """Test sample data fixture works."""
    assert sample_warehouse["code"] == "WH-TEST"
    assert sample_warehouse["name"] == "Test Warehouse"
    assert sample_warehouse["active"] is True


@pytest.mark.unit
def test_multiple_fixtures(sample_warehouse, sample_product):
    """Test multiple fixtures can be used together."""
    assert sample_warehouse["code"] == "WH-TEST"
    assert sample_product["code"] == "PROD-TEST"


@pytest.mark.unit
@pytest.mark.slow
def test_slow_test():
    """Test slow marker works."""
    # This test can be skipped with: pytest -m "not slow"
    assert True
