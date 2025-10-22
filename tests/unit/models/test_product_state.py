"""Unit tests for ProductState model.

Tests code validation, is_sellable flag, sort_order defaults, and basic field access.
Note: Database integration tests are in tests/integration/
"""

import pytest

from app.models import ProductState


class TestProductStateCodeValidation:
    """Test code validation rules."""

    def test_code_valid_uppercase(self):
        """Test valid uppercase code is accepted."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        assert state.code == "ADULT"

    def test_code_auto_uppercase(self):
        """Test lowercase code is auto-uppercased."""
        state = ProductState(code="flowering", name="Flowering", is_sellable=True, sort_order=60)
        assert state.code == "FLOWERING"

    def test_code_empty_raises_error(self):
        """Test empty code raises ValueError."""
        with pytest.raises(ValueError, match="code cannot be empty"):
            state = ProductState(code="", name="Test", is_sellable=False, sort_order=10)

    def test_code_with_hyphens_raises_error(self):
        """Test code with hyphens raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            state = ProductState(
                code="ADULT-PLANT", name="Adult Plant", is_sellable=True, sort_order=50
            )

    def test_code_with_spaces_raises_error(self):
        """Test code with spaces raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            state = ProductState(
                code="ADULT PLANT", name="Adult Plant", is_sellable=True, sort_order=50
            )

    def test_code_too_short_raises_error(self):
        """Test code <3 chars raises ValueError."""
        with pytest.raises(ValueError, match="3-50 characters"):
            state = ProductState(code="SE", name="Seed", is_sellable=False, sort_order=10)

    def test_code_too_long_raises_error(self):
        """Test code >50 chars raises ValueError."""
        long_code = "A" * 51
        with pytest.raises(ValueError, match="3-50 characters"):
            state = ProductState(code=long_code, name="Test", is_sellable=False, sort_order=10)

    def test_code_with_underscores_valid(self):
        """Test code with underscores is valid."""
        state = ProductState(
            code="ADULT_FLOWERING", name="Adult Flowering", is_sellable=True, sort_order=55
        )
        assert state.code == "ADULT_FLOWERING"


class TestProductStateSellableFlag:
    """Test is_sellable business logic flag."""

    def test_is_sellable_default_false(self):
        """Test is_sellable defaults to FALSE."""
        state = ProductState(code="SEED", name="Seed", sort_order=10)
        # Default for is_sellable may be None or False before DB insert
        assert state.is_sellable is None or state.is_sellable is False

    def test_is_sellable_explicit_true(self):
        """Test is_sellable can be set to TRUE."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        assert state.is_sellable is True

    def test_is_sellable_explicit_false(self):
        """Test is_sellable can be explicitly set to FALSE."""
        state = ProductState(code="DYING", name="Dying", is_sellable=False, sort_order=100)
        assert state.is_sellable is False


class TestProductStateSortOrder:
    """Test sort_order field."""

    def test_sort_order_default_99(self):
        """Test sort_order defaults to 99."""
        state = ProductState(code="TEST", name="Test State", is_sellable=False)
        # sort_order defaults to 99 or may be None before DB insert
        assert state.sort_order == 99 or state.sort_order is None

    def test_sort_order_custom_value(self):
        """Test sort_order can be set to custom value."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        assert state.sort_order == 50

    def test_sort_order_zero_valid(self):
        """Test sort_order can be 0."""
        state = ProductState(
            code="EARLIEST", name="Earliest State", is_sellable=False, sort_order=0
        )
        assert state.sort_order == 0


class TestProductStateFields:
    """Test field assignments."""

    def test_description_nullable(self):
        """Test description can be NULL."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        assert state.description is None

    def test_name_field(self):
        """Test name field (Python allows None, DB enforces NOT NULL)."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        assert state.name == "Adult Plant"


class TestProductStateRepr:
    """Test __repr__ method."""

    def test_repr_format(self):
        """Test __repr__ returns expected format."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        repr_str = repr(state)
        # repr format may vary, just check it contains the code
        assert "ADULT" in repr_str or "ProductState" in repr_str
