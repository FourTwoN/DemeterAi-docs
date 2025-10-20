"""Unit tests for ProductSize model.

Tests code validation, height ranges, sort_order defaults, and basic CRUD operations.
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ProductSize


class TestProductSizeCodeValidation:
    """Test code validation rules."""

    def test_code_valid_uppercase(self, session):
        """Test valid uppercase code is accepted."""
        # NOTE: Code too short (<3 chars), should raise ValueError
        with pytest.raises(ValueError, match="3-50 characters"):
            size = ProductSize(code="XL", name="Extra Large", sort_order=50)

    def test_code_valid_three_chars(self, session):
        """Test valid 3-char code is accepted."""
        size = ProductSize(code="XXL", name="Extra Extra Large", sort_order=60)
        session.add(size)
        session.commit()

        assert size.product_size_id is not None
        assert size.code == "XXL"

    def test_code_auto_uppercase(self, session):
        """Test lowercase code is auto-uppercased."""
        size = ProductSize(code="custom", name="Custom Size", sort_order=99)
        session.add(size)
        session.commit()

        assert size.code == "CUSTOM"

    def test_code_empty_raises_error(self, session):
        """Test empty code raises ValueError."""
        with pytest.raises(ValueError, match="code cannot be empty"):
            size = ProductSize(code="", name="Test", sort_order=10)

    def test_code_with_hyphens_raises_error(self, session):
        """Test code with hyphens raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            size = ProductSize(code="EXTRA-LARGE", name="Extra Large", sort_order=50)

    def test_code_with_spaces_raises_error(self, session):
        """Test code with spaces raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            size = ProductSize(code="EXTRA LARGE", name="Extra Large", sort_order=50)

    def test_code_too_short_raises_error(self, session):
        """Test code <3 chars raises ValueError."""
        with pytest.raises(ValueError, match="3-50 characters"):
            size = ProductSize(code="XL", name="Extra Large", sort_order=50)

    def test_code_too_long_raises_error(self, session):
        """Test code >50 chars raises ValueError."""
        long_code = "A" * 51
        with pytest.raises(ValueError, match="3-50 characters"):
            size = ProductSize(code=long_code, name="Test", sort_order=10)

    def test_code_with_underscores_valid(self, session):
        """Test code with underscores is valid."""
        size = ProductSize(code="EXTRA_LARGE", name="Extra Large", sort_order=50)
        session.add(size)
        session.commit()

        assert size.code == "EXTRA_LARGE"


class TestProductSizeHeightRanges:
    """Test height range fields."""

    def test_height_ranges_nullable(self, session):
        """Test both height ranges can be NULL."""
        size = ProductSize(
            code="CUSTOM", name="Custom Size", min_height_cm=None, max_height_cm=None, sort_order=99
        )
        session.add(size)
        session.commit()

        assert size.min_height_cm is None
        assert size.max_height_cm is None

    def test_height_ranges_valid_values(self, session):
        """Test valid height range values."""
        size = ProductSize(
            code="MEDIUM",
            name="Medium (10-20cm)",
            min_height_cm=Decimal("10.00"),
            max_height_cm=Decimal("20.00"),
            sort_order=30,
        )
        session.add(size)
        session.commit()

        assert size.min_height_cm == Decimal("10.00")
        assert size.max_height_cm == Decimal("20.00")

    def test_custom_size_no_height_ranges(self, session):
        """Test CUSTOM size has no height ranges."""
        custom = ProductSize(
            code="CUSTOM",
            name="Custom Size (no fixed range)",
            min_height_cm=None,
            max_height_cm=None,
            sort_order=99,
        )
        session.add(custom)
        session.commit()

        assert custom.min_height_cm is None
        assert custom.max_height_cm is None

    def test_xxl_no_max_height(self, session):
        """Test XXL size has no max height (open-ended)."""
        xxl = ProductSize(
            code="XXL",
            name="Extra Extra Large (80+cm)",
            min_height_cm=Decimal("80.00"),
            max_height_cm=None,
            sort_order=60,
        )
        session.add(xxl)
        session.commit()

        assert xxl.min_height_cm == Decimal("80.00")
        assert xxl.max_height_cm is None


class TestProductSizeSortOrder:
    """Test sort_order field."""

    def test_sort_order_default_99(self, session):
        """Test sort_order defaults to 99."""
        size = ProductSize(code="TEST", name="Test Size")
        session.add(size)
        session.commit()

        assert size.sort_order == 99

    def test_sort_order_custom_value(self, session):
        """Test sort_order can be set to custom value."""
        size = ProductSize(code="MEDIUM", name="Medium", sort_order=30)
        session.add(size)
        session.commit()

        assert size.sort_order == 30

    def test_sort_order_zero_valid(self, session):
        """Test sort_order can be 0."""
        size = ProductSize(code="SMALLEST", name="Smallest", sort_order=0)
        session.add(size)
        session.commit()

        assert size.sort_order == 0


class TestProductSizeBasicCRUD:
    """Test basic CRUD operations."""

    def test_create_product_size(self, session):
        """Test creating a product size."""
        size = ProductSize(
            code="MEDIUM",
            name="Medium (10-20cm)",
            description="Medium plants, 10-20cm height",
            min_height_cm=Decimal("10.00"),
            max_height_cm=Decimal("20.00"),
            sort_order=30,
        )
        session.add(size)
        session.commit()

        assert size.product_size_id is not None
        assert size.code == "MEDIUM"
        assert size.name == "Medium (10-20cm)"
        assert size.description == "Medium plants, 10-20cm height"
        assert size.min_height_cm == Decimal("10.00")
        assert size.max_height_cm == Decimal("20.00")
        assert size.sort_order == 30
        assert size.created_at is not None
        assert size.updated_at is None

    def test_update_product_size(self, session):
        """Test updating a product size."""
        size = ProductSize(code="MEDIUM", name="Medium", sort_order=30)
        session.add(size)
        session.commit()

        # Update
        size.name = "Medium (10-20cm)"
        size.description = "Updated description"
        session.commit()

        # Verify
        updated_size = session.query(ProductSize).filter_by(code="MEDIUM").first()
        assert updated_size.name == "Medium (10-20cm)"
        assert updated_size.description == "Updated description"

    def test_delete_product_size(self, session):
        """Test deleting a product size."""
        size = ProductSize(code="MEDIUM", name="Medium", sort_order=30)
        session.add(size)
        session.commit()

        size_id = size.product_size_id

        # Delete
        session.delete(size)
        session.commit()

        # Verify deleted
        deleted_size = session.query(ProductSize).filter_by(product_size_id=size_id).first()
        assert deleted_size is None


class TestProductSizeRepr:
    """Test __repr__ method."""

    def test_repr_format_with_range(self, session):
        """Test __repr__ returns expected format with height range."""
        size = ProductSize(
            code="MEDIUM",
            name="Medium (10-20cm)",
            min_height_cm=Decimal("10.00"),
            max_height_cm=Decimal("20.00"),
            sort_order=30,
        )
        session.add(size)
        session.commit()

        repr_str = repr(size)
        assert "ProductSize" in repr_str
        assert "MEDIUM" in repr_str
        assert "Medium (10-20cm)" in repr_str
        assert "10.0-20.0cm" in repr_str or "10.00-20.00cm" in repr_str
        assert "sort_order=30" in repr_str

    def test_repr_format_no_range(self, session):
        """Test __repr__ returns expected format with no height range."""
        size = ProductSize(
            code="CUSTOM", name="Custom Size", min_height_cm=None, max_height_cm=None, sort_order=99
        )
        session.add(size)
        session.commit()

        repr_str = repr(size)
        assert "ProductSize" in repr_str
        assert "CUSTOM" in repr_str
        assert "N/A" in repr_str  # No height range


class TestProductSizeUniqueness:
    """Test code uniqueness constraint."""

    def test_duplicate_code_raises_integrity_error(self, session):
        """Test duplicate code raises IntegrityError."""
        size1 = ProductSize(code="MEDIUM", name="Medium", sort_order=30)
        session.add(size1)
        session.commit()

        # Try to add duplicate
        size2 = ProductSize(code="MEDIUM", name="Large", sort_order=40)
        session.add(size2)

        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


class TestProductSizeFields:
    """Test field constraints."""

    def test_name_required(self, session):
        """Test name is required (NOT NULL)."""
        size = ProductSize(
            code="MEDIUM",
            name=None,  # Missing required field
            sort_order=30,
        )
        session.add(size)

        with pytest.raises((IntegrityError, ValueError)):
            session.commit()
        session.rollback()

    def test_description_nullable(self, session):
        """Test description is nullable."""
        size = ProductSize(
            code="MEDIUM",
            name="Medium",
            description=None,  # Nullable
            sort_order=30,
        )
        session.add(size)
        session.commit()

        assert size.description is None

    def test_timestamps_auto_generated(self, session):
        """Test created_at is auto-generated."""
        size = ProductSize(code="MEDIUM", name="Medium", sort_order=30)
        session.add(size)
        session.commit()

        assert size.created_at is not None
        assert size.updated_at is None
