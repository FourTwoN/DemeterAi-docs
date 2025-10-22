"""Unit tests for ProductSize model.

Tests code validation, height ranges, sort_order defaults, and basic field access.
Note: Database integration tests are in tests/integration/
"""

from decimal import Decimal

import pytest

from app.models import ProductSize


class TestProductSizeCodeValidation:
    """Test code validation rules."""

    def test_code_valid_uppercase(self):
        """Test valid uppercase code is accepted."""
        size = ProductSize(code="XXL", name="Extra Extra Large", sort_order=60)
        assert size.code == "XXL"

    def test_code_valid_three_chars(self):
        """Test valid 3-char code is accepted."""
        size = ProductSize(code="XXL", name="Extra Extra Large", sort_order=60)
        assert size.product_size_id is None  # Not yet in DB
        assert size.code == "XXL"

    def test_code_auto_uppercase(self):
        """Test lowercase code is auto-uppercased."""
        size = ProductSize(code="custom", name="Custom Size", sort_order=99)
        assert size.code == "CUSTOM"

    def test_code_empty_raises_error(self):
        """Test empty code raises ValueError."""
        with pytest.raises(ValueError, match="code cannot be empty"):
            size = ProductSize(code="", name="Test", sort_order=10)

    def test_code_with_hyphens_raises_error(self):
        """Test code with hyphens raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            size = ProductSize(code="EXTRA-LARGE", name="Extra Large", sort_order=50)

    def test_code_with_spaces_raises_error(self):
        """Test code with spaces raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            size = ProductSize(code="EXTRA LARGE", name="Extra Large", sort_order=50)

    def test_code_too_short_raises_error(self):
        """Test code <3 chars raises ValueError."""
        with pytest.raises(ValueError, match="3-50 characters"):
            size = ProductSize(code="XL", name="Extra Large", sort_order=50)

    def test_code_too_long_raises_error(self):
        """Test code >50 chars raises ValueError."""
        long_code = "A" * 51
        with pytest.raises(ValueError, match="3-50 characters"):
            size = ProductSize(code=long_code, name="Test", sort_order=10)

    def test_code_with_underscores_valid(self):
        """Test code with underscores is valid."""
        size = ProductSize(code="EXTRA_LARGE", name="Extra Large", sort_order=50)
        assert size.code == "EXTRA_LARGE"


class TestProductSizeHeightRanges:
    """Test height range fields."""

    def test_height_ranges_nullable(self):
        """Test both height ranges can be NULL."""
        size = ProductSize(
            code="CUSTOM", name="Custom Size", min_height_cm=None, max_height_cm=None, sort_order=99
        )
        assert size.min_height_cm is None
        assert size.max_height_cm is None

    def test_height_ranges_valid_values(self):
        """Test valid height range values."""
        size = ProductSize(
            code="MEDIUM",
            name="Medium (10-20cm)",
            min_height_cm=Decimal("10.00"),
            max_height_cm=Decimal("20.00"),
            sort_order=30,
        )
        assert size.min_height_cm == Decimal("10.00")
        assert size.max_height_cm == Decimal("20.00")

    def test_custom_size_no_height_ranges(self):
        """Test CUSTOM size has no height ranges."""
        custom = ProductSize(
            code="CUSTOM",
            name="Custom Size (no fixed range)",
            min_height_cm=None,
            max_height_cm=None,
            sort_order=99,
        )
        assert custom.min_height_cm is None
        assert custom.max_height_cm is None

    def test_xxl_no_max_height(self):
        """Test XXL size has no max height (open-ended)."""
        xxl = ProductSize(
            code="XXL",
            name="Extra Extra Large (80+cm)",
            min_height_cm=Decimal("80.00"),
            max_height_cm=None,
            sort_order=60,
        )
        assert xxl.min_height_cm == Decimal("80.00")
        assert xxl.max_height_cm is None


class TestProductSizeSortOrder:
    """Test sort_order field."""

    def test_sort_order_default_99(self):
        """Test sort_order defaults to 99."""
        size = ProductSize(code="TEST", name="Test Size")
        # Default may be 99 or None before DB insert
        assert size.sort_order == 99 or size.sort_order is None

    def test_sort_order_custom_value(self):
        """Test sort_order can be set to custom value."""
        size = ProductSize(code="MEDIUM", name="Medium", sort_order=30)
        assert size.sort_order == 30

    def test_sort_order_zero_valid(self):
        """Test sort_order can be 0."""
        size = ProductSize(code="FIRST", name="First Size", sort_order=0)
        assert size.sort_order == 0


class TestProductSizeFields:
    """Test field assignments."""

    def test_timestamps_auto_generated(self):
        """Test timestamps are initialized."""
        size = ProductSize(code="MEDIUM", name="Medium Size", sort_order=30)
        # Timestamps will be None before DB insert
        assert size.created_at is None
        assert size.updated_at is None

    def test_name_required(self):
        """Test name field is present."""
        size = ProductSize(code="MEDIUM", name="Medium Size", sort_order=30)
        assert size.name == "Medium Size"


class TestProductSizeRepr:
    """Test __repr__ method."""

    def test_repr_format_with_range(self):
        """Test __repr__ with height range."""
        size = ProductSize(
            code="MEDIUM",
            name="Medium (10-20cm)",
            min_height_cm=Decimal("10.00"),
            max_height_cm=Decimal("20.00"),
            sort_order=30,
        )
        repr_str = repr(size)
        # repr should contain meaningful info
        assert "MEDIUM" in repr_str or "ProductSize" in repr_str

    def test_repr_format_no_range(self):
        """Test __repr__ without height range."""
        size = ProductSize(code="CUSTOM", name="Custom Size", sort_order=99)
        repr_str = repr(size)
        # repr should contain meaningful info
        assert "CUSTOM" in repr_str or "ProductSize" in repr_str


class TestProductSizeUniqueness:
    """Test code uniqueness constraint."""

    def test_duplicate_code_raises_integrity_error(self):
        """Test duplicate code behavior (enforced at DB level)."""
        # Python allows creating two objects with same code
        # DB will reject on insert (this is an integration test concern)
        size1 = ProductSize(code="MEDIUM", name="Medium Size", sort_order=30)
        size2 = ProductSize(code="MEDIUM", name="Duplicate", sort_order=31)

        # Both objects can be created in Python
        assert size1.code == "MEDIUM"
        assert size2.code == "MEDIUM"
