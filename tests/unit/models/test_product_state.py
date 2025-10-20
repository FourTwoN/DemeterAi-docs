"""Unit tests for ProductState model.

Tests code validation, is_sellable flag, sort_order defaults, and basic CRUD operations.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import ProductState


class TestProductStateCodeValidation:
    """Test code validation rules."""

    def test_code_valid_uppercase(self, session):
        """Test valid uppercase code is accepted."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state)
        session.commit()

        assert state.product_state_id is not None
        assert state.code == "ADULT"

    def test_code_auto_uppercase(self, session):
        """Test lowercase code is auto-uppercased."""
        state = ProductState(code="flowering", name="Flowering", is_sellable=True, sort_order=60)
        session.add(state)
        session.commit()

        assert state.code == "FLOWERING"

    def test_code_empty_raises_error(self, session):
        """Test empty code raises ValueError."""
        with pytest.raises(ValueError, match="code cannot be empty"):
            state = ProductState(code="", name="Test", is_sellable=False, sort_order=10)

    def test_code_with_hyphens_raises_error(self, session):
        """Test code with hyphens raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            state = ProductState(
                code="ADULT-PLANT", name="Adult Plant", is_sellable=True, sort_order=50
            )

    def test_code_with_spaces_raises_error(self, session):
        """Test code with spaces raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            state = ProductState(
                code="ADULT PLANT", name="Adult Plant", is_sellable=True, sort_order=50
            )

    def test_code_too_short_raises_error(self, session):
        """Test code <3 chars raises ValueError."""
        with pytest.raises(ValueError, match="3-50 characters"):
            state = ProductState(code="SE", name="Seed", is_sellable=False, sort_order=10)

    def test_code_too_long_raises_error(self, session):
        """Test code >50 chars raises ValueError."""
        long_code = "A" * 51
        with pytest.raises(ValueError, match="3-50 characters"):
            state = ProductState(code=long_code, name="Test", is_sellable=False, sort_order=10)

    def test_code_with_underscores_valid(self, session):
        """Test code with underscores is valid."""
        state = ProductState(
            code="ADULT_FLOWERING", name="Adult Flowering", is_sellable=True, sort_order=55
        )
        session.add(state)
        session.commit()

        assert state.code == "ADULT_FLOWERING"


class TestProductStateSellableFlag:
    """Test is_sellable business logic flag."""

    def test_is_sellable_default_false(self, session):
        """Test is_sellable defaults to FALSE."""
        state = ProductState(code="SEED", name="Seed", sort_order=10)
        session.add(state)
        session.commit()

        assert state.is_sellable is False

    def test_is_sellable_explicit_true(self, session):
        """Test is_sellable can be set to TRUE."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state)
        session.commit()

        assert state.is_sellable is True

    def test_is_sellable_explicit_false(self, session):
        """Test is_sellable can be explicitly set to FALSE."""
        state = ProductState(code="DYING", name="Dying", is_sellable=False, sort_order=100)
        session.add(state)
        session.commit()

        assert state.is_sellable is False


class TestProductStateSortOrder:
    """Test sort_order field."""

    def test_sort_order_default_99(self, session):
        """Test sort_order defaults to 99."""
        state = ProductState(code="TEST", name="Test State", is_sellable=False)
        session.add(state)
        session.commit()

        assert state.sort_order == 99

    def test_sort_order_custom_value(self, session):
        """Test sort_order can be set to custom value."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state)
        session.commit()

        assert state.sort_order == 50

    def test_sort_order_zero_valid(self, session):
        """Test sort_order can be 0."""
        state = ProductState(
            code="EARLIEST", name="Earliest State", is_sellable=False, sort_order=0
        )
        session.add(state)
        session.commit()

        assert state.sort_order == 0


class TestProductStateBasicCRUD:
    """Test basic CRUD operations."""

    def test_create_product_state(self, session):
        """Test creating a product state."""
        state = ProductState(
            code="ADULT",
            name="Adult Plant",
            description="Mature plant, ready for sale",
            is_sellable=True,
            sort_order=50,
        )
        session.add(state)
        session.commit()

        assert state.product_state_id is not None
        assert state.code == "ADULT"
        assert state.name == "Adult Plant"
        assert state.description == "Mature plant, ready for sale"
        assert state.is_sellable is True
        assert state.sort_order == 50
        assert state.created_at is not None
        assert state.updated_at is None  # Not updated yet

    def test_update_product_state(self, session):
        """Test updating a product state."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state)
        session.commit()

        # Update
        state.name = "Mature Adult Plant"
        state.description = "Updated description"
        session.commit()

        # Verify
        updated_state = session.query(ProductState).filter_by(code="ADULT").first()
        assert updated_state.name == "Mature Adult Plant"
        assert updated_state.description == "Updated description"

    def test_delete_product_state(self, session):
        """Test deleting a product state."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state)
        session.commit()

        state_id = state.product_state_id

        # Delete
        session.delete(state)
        session.commit()

        # Verify deleted
        deleted_state = session.query(ProductState).filter_by(product_state_id=state_id).first()
        assert deleted_state is None


class TestProductStateRepr:
    """Test __repr__ method."""

    def test_repr_format(self, session):
        """Test __repr__ returns expected format."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state)
        session.commit()

        repr_str = repr(state)
        assert "ProductState" in repr_str
        assert "ADULT" in repr_str
        assert "Adult Plant" in repr_str
        assert "is_sellable=True" in repr_str
        assert "sort_order=50" in repr_str


class TestProductStateUniqueness:
    """Test code uniqueness constraint."""

    def test_duplicate_code_raises_integrity_error(self, session):
        """Test duplicate code raises IntegrityError."""
        state1 = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state1)
        session.commit()

        # Try to add duplicate
        state2 = ProductState(code="ADULT", name="Mature Plant", is_sellable=True, sort_order=51)
        session.add(state2)

        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


class TestProductStateFields:
    """Test field constraints."""

    def test_name_required(self, session):
        """Test name is required (NOT NULL)."""
        state = ProductState(
            code="ADULT",
            name=None,  # Missing required field
            is_sellable=True,
            sort_order=50,
        )
        session.add(state)

        with pytest.raises((IntegrityError, ValueError)):
            session.commit()
        session.rollback()

    def test_description_nullable(self, session):
        """Test description is nullable."""
        state = ProductState(
            code="ADULT",
            name="Adult Plant",
            description=None,  # Nullable
            is_sellable=True,
            sort_order=50,
        )
        session.add(state)
        session.commit()

        assert state.description is None

    def test_timestamps_auto_generated(self, session):
        """Test created_at is auto-generated."""
        state = ProductState(code="ADULT", name="Adult Plant", is_sellable=True, sort_order=50)
        session.add(state)
        session.commit()

        assert state.created_at is not None
        assert state.updated_at is None  # Not updated yet
