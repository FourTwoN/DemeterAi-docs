"""Integration tests for ProductState model.

Tests seed data loading, DB-level constraints, and query operations.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import ProductState


class TestProductStateSeedData:
    """Test seed data loaded correctly."""

    async def test_seed_data_loaded(self, session):
        """Verify all 11 seed states exist after migration."""
        result = await session.execute(select(ProductState).order_by(ProductState.sort_order))
        states = result.scalars().all()
        assert len(states) >= 11  # At least 11 seed states

        codes = [s.code for s in states]
        expected_codes = [
            "SEED",
            "GERMINATING",
            "SEEDLING",
            "JUVENILE",
            "ADULT",
            "FLOWERING",
            "FRUITING",
            "DORMANT",
            "PROPAGATING",
            "DYING",
            "DEAD",
        ]

        for expected_code in expected_codes:
            assert expected_code in codes

    async def test_seed_data_is_sellable_logic(self, session):
        """Verify is_sellable logic is correct for seed data."""
        # Sellable states
        result = await session.execute(select(ProductState).where(ProductState.code == "ADULT"))
        adult = result.scalars().first()
        result = await session.execute(select(ProductState).where(ProductState.code == "FLOWERING"))
        flowering = result.scalars().first()
        result = await session.execute(select(ProductState).where(ProductState.code == "FRUITING"))
        fruiting = result.scalars().first()
        result = await session.execute(select(ProductState).where(ProductState.code == "DORMANT"))
        dormant = result.scalars().first()

        assert adult.is_sellable is True
        assert flowering.is_sellable is True
        assert fruiting.is_sellable is True
        assert dormant.is_sellable is True

        # Not sellable states
        result = await session.execute(select(ProductState).where(ProductState.code == "SEED"))
        seed = result.scalars().first()
        result = await session.execute(select(ProductState).where(ProductState.code == "DYING"))
        dying = result.scalars().first()
        result = await session.execute(select(ProductState).where(ProductState.code == "DEAD"))
        dead = result.scalars().first()

        assert seed.is_sellable is False
        assert dying.is_sellable is False
        assert dead.is_sellable is False


class TestProductStateDBConstraints:
    """Test database-level constraints."""

    async def test_code_unique_constraint_db_level(self, session):
        """Test code uniqueness at database level."""
        # Create first state
        state1 = ProductState(
            code="TEST_STATE", name="Test State", is_sellable=False, sort_order=50
        )
        session.add(state1)
        await session.commit()

        # Try to create duplicate (should fail at DB level)
        state2 = ProductState(
            code="TEST_STATE", name="Another Test", is_sellable=True, sort_order=51
        )
        session.add(state2)

        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_code_check_constraint_min_length(self, session):
        """Test CHECK constraint for minimum code length (DB-level)."""
        state = ProductState(
            code="AB",  # Too short (< 3 chars)
            name="Test",
            is_sellable=False,
            sort_order=10,
        )

        with pytest.raises(ValueError):  # Caught by validator before DB
            session.add(state)
            await session.flush()


class TestProductStateQueries:
    """Test query operations."""

    async def test_filter_by_is_sellable_true(self, session):
        """Test filtering by is_sellable=TRUE."""
        result = await session.execute(select(ProductState).where(ProductState.is_sellable == True))
        sellable_states = result.scalars().all()

        assert len(sellable_states) >= 4  # At least ADULT, FLOWERING, FRUITING, DORMANT
        for state in sellable_states:
            assert state.is_sellable is True

    async def test_filter_by_is_sellable_false(self, session):
        """Test filtering by is_sellable=FALSE."""
        result = await session.execute(
            select(ProductState).where(ProductState.is_sellable == False)
        )
        non_sellable_states = result.scalars().all()

        assert (
            len(non_sellable_states) >= 7
        )  # SEED, GERMINATING, SEEDLING, JUVENILE, PROPAGATING, DYING, DEAD
        for state in non_sellable_states:
            assert state.is_sellable is False

    async def test_order_by_sort_order(self, session):
        """Test ordering by sort_order."""
        result = await session.execute(
            select(ProductState).order_by(ProductState.sort_order).limit(5)
        )
        states = result.scalars().all()

        # Verify sort_order is ascending
        previous_order = -1
        for state in states:
            assert state.sort_order >= previous_order
            previous_order = state.sort_order

    async def test_query_by_code(self, session):
        """Test querying by code (UK index)."""
        result = await session.execute(select(ProductState).where(ProductState.code == "ADULT"))
        adult = result.scalars().first()

        assert adult is not None
        assert adult.code == "ADULT"
        assert adult.is_sellable is True
