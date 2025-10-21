"""Integration tests for ProductSize model.

Tests seed data loading, DB-level constraints, and query operations.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import ProductSize


class TestProductSizeSeedData:
    """Test seed data loaded correctly."""

    async def test_seed_data_loaded(self, session):
        """Verify all 7 seed sizes exist after migration."""
        result = await session.execute(select(ProductSize).order_by(ProductSize.sort_order))
        sizes = result.scalars().all()
        assert len(sizes) >= 7  # At least 7 seed sizes

        codes = [s.code for s in sizes]
        expected_codes = ["XS", "S", "M", "L", "XL", "XXL", "CUSTOM"]

        for expected_code in expected_codes:
            assert expected_code in codes

    async def test_seed_data_height_ranges(self, session):
        """Verify height ranges are correct for seed data."""
        # XS: 0-5cm
        result = await session.execute(select(ProductSize).where(ProductSize.code == "XS"))
        xs = result.scalars().first()
        assert xs.min_height_cm == Decimal("0.00")
        assert xs.max_height_cm == Decimal("5.00")

        # S: 5-10cm
        result = await session.execute(select(ProductSize).where(ProductSize.code == "S"))
        s = result.scalars().first()
        assert s.min_height_cm == Decimal("5.00")
        assert s.max_height_cm == Decimal("10.00")

        # M: 10-20cm
        result = await session.execute(select(ProductSize).where(ProductSize.code == "M"))
        m = result.scalars().first()
        assert m.min_height_cm == Decimal("10.00")
        assert m.max_height_cm == Decimal("20.00")

        # XXL: 80+cm (no max)
        result = await session.execute(select(ProductSize).where(ProductSize.code == "XXL"))
        xxl = result.scalars().first()
        assert xxl.min_height_cm == Decimal("80.00")
        assert xxl.max_height_cm is None

        # CUSTOM: No range
        result = await session.execute(select(ProductSize).where(ProductSize.code == "CUSTOM"))
        custom = result.scalars().first()
        assert custom.min_height_cm is None
        assert custom.max_height_cm is None


class TestProductSizeDBConstraints:
    """Test database-level constraints."""

    async def test_code_unique_constraint_db_level(self, session):
        """Test code uniqueness at database level."""
        # Create first size
        size1 = ProductSize(code="TEST_SIZE", name="Test Size", sort_order=50)
        session.add(size1)
        await session.commit()

        # Try to create duplicate (should fail at DB level)
        size2 = ProductSize(code="TEST_SIZE", name="Another Test", sort_order=51)
        session.add(size2)

        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_code_check_constraint_min_length(self, session):
        """Test CHECK constraint for minimum code length (DB-level)."""
        size = ProductSize(
            code="AB",  # Too short (< 3 chars)
            name="Test",
            sort_order=10,
        )

        with pytest.raises(ValueError):  # Caught by validator before DB
            session.add(size)
            await session.flush()


class TestProductSizeQueries:
    """Test query operations."""

    async def test_order_by_sort_order(self, session):
        """Test ordering by sort_order."""
        result = await session.execute(select(ProductSize).order_by(ProductSize.sort_order))
        sizes = result.scalars().all()

        # Verify sort_order is ascending
        previous_order = -1
        for size in sizes:
            assert size.sort_order >= previous_order
            previous_order = size.sort_order

        # Verify CUSTOM is last (sort_order=99)
        assert sizes[-1].code == "CUSTOM"

    async def test_query_by_code(self, session):
        """Test querying by code (UK index)."""
        result = await session.execute(select(ProductSize).where(ProductSize.code == "M"))
        medium = result.scalars().first()

        assert medium is not None
        assert medium.code == "M"
        assert medium.min_height_cm == Decimal("10.00")
        assert medium.max_height_cm == Decimal("20.00")

    async def test_filter_with_height_range(self, session):
        """Test filtering sizes with complete height range."""
        # Sizes with both min and max defined
        result = await session.execute(
            select(ProductSize).where(
                ProductSize.min_height_cm.isnot(None), ProductSize.max_height_cm.isnot(None)
            )
        )
        complete_ranges = result.scalars().all()

        assert len(complete_ranges) >= 5  # XS, S, M, L, XL have complete ranges
        for size in complete_ranges:
            assert size.min_height_cm is not None
            assert size.max_height_cm is not None

    async def test_filter_without_height_range(self, session):
        """Test filtering sizes without height range (CUSTOM)."""
        result = await session.execute(
            select(ProductSize).where(
                ProductSize.min_height_cm.is_(None), ProductSize.max_height_cm.is_(None)
            )
        )
        no_range = result.scalars().all()

        assert len(no_range) >= 1  # At least CUSTOM
        custom = next((s for s in no_range if s.code == "CUSTOM"), None)
        assert custom is not None
        assert custom.min_height_cm is None
        assert custom.max_height_cm is None
