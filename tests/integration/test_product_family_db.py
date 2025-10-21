"""Integration tests for ProductFamily model with database.

Tests ProductFamily model CRUD operations, relationships, and constraints
against a real test database.

Test Coverage:
    - Create family with valid category FK
    - Query families by category_id
    - CASCADE delete: Delete category deletes families
    - Create multiple families for same category
    - Query with joins (family.category.name)
    - FK constraint violation (invalid category_id)
    - NOT NULL constraint (missing name)

Architecture:
    - Layer: Integration Tests (database interaction)
    - Dependencies: pytest, PostgreSQL test database, ProductFamily, ProductCategory
    - Pattern: AAA (Arrange-Act-Assert) with database fixtures

Usage:
    pytest tests/integration/test_product_family_db.py -v
    pytest tests/integration/test_product_family_db.py::test_create_family_with_category -v
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product_category import ProductCategory
from app.models.product_family import ProductFamily


class TestProductFamilyDatabaseOperations:
    """Test suite for ProductFamily CRUD operations."""

    async def test_create_family_with_category(self, db_session: Session):
        """Test creating family with valid category FK."""
        # Arrange - Create category first
        category = ProductCategory(code="CACTUS", name="Cactus", description="Cacti family")
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)

        # Act - Create family
        family = ProductFamily(
            category_id=category.id,
            name="Echeveria",
            scientific_name="Echeveria",
            description="Small rosette-forming succulents",
        )
        db_session.add(family)
        await db_session.commit()
        await db_session.refresh(family)

        # Assert
        assert family.family_id is not None
        assert family.category_id == category.id
        assert family.name == "Echeveria"

    async def test_create_family_minimal_fields(self, db_session: Session):
        """Test creating family with only required fields."""
        # Arrange - Create category
        category = ProductCategory(code="SUCCULENT", name="Succulent")
        db_session.add(category)
        await db_session.commit()

        # Act - Create family with minimal fields
        family = ProductFamily(category_id=category.id, name="Aloe")
        db_session.add(family)
        await db_session.commit()
        await db_session.refresh(family)

        # Assert
        assert family.family_id is not None
        assert family.name == "Aloe"
        assert family.scientific_name is None
        assert family.description is None

    async def test_query_families_by_category(self, db_session: Session):
        """Test querying all families for a specific category."""
        # Arrange - Create category and multiple families
        category = ProductCategory(code="BROMELIAD", name="Bromeliad")
        db_session.add(category)
        await db_session.commit()

        families_data = [
            ("Tillandsia", "Tillandsia", "Air plants"),
            ("Guzmania", "Guzmania", "Colorful bromeliads"),
            ("Aechmea", "Aechmea", "Spiky bromeliads"),
        ]

        for name, sci_name, desc in families_data:
            family = ProductFamily(
                category_id=category.id,
                name=name,
                scientific_name=sci_name,
                description=desc,
            )
            db_session.add(family)

        await db_session.commit()

        # Act - Query families by category_id
        stmt = select(ProductFamily).where(
            ProductFamily.category_id == category.id
        )
        result = await db_session.execute(stmt)
        families = result.scalars().all()

        # Assert
        assert len(families) == 3
        family_names = {f.name for f in families}
        assert family_names == {"Tillandsia", "Guzmania", "Aechmea"}

    async def test_query_family_with_category_join(self, db_session: Session):
        """Test querying family with category relationship join."""
        # Arrange - Create category and family
        category = ProductCategory(code="ORCHID", name="Orchid")
        db_session.add(category)
        await db_session.commit()

        family = ProductFamily(
            category_id=category.id,
            name="Phalaenopsis",
            scientific_name="Phalaenopsis",
        )
        db_session.add(family)
        await db_session.commit()
        await db_session.refresh(family)

        # Act - Query family and access category via relationship
        stmt = select(ProductFamily).where(ProductFamily.name == "Phalaenopsis")
        result = await db_session.execute(stmt)
        queried_family = result.scalar_one()

        # Assert - Access category through relationship
        assert queried_family.category is not None
        assert queried_family.category.code == "ORCHID"
        assert queried_family.category.name == "Orchid"

    async def test_create_multiple_families_same_category(self, db_session: Session):
        """Test creating multiple families for the same category."""
        # Arrange - Create category
        category = ProductCategory(code="CARNIVOROUS", name="Carnivorous Plant")
        db_session.add(category)
        await db_session.commit()

        # Act - Create multiple families
        family1 = ProductFamily(category_id=category.id, name="Nepenthes")
        family2 = ProductFamily(category_id=category.id, name="Dionaea")
        db_session.add(family1)
        db_session.add(family2)
        await db_session.commit()

        # Assert - Both families exist
        stmt = select(ProductFamily).where(
            ProductFamily.category_id == category.id
        )
        result = await db_session.execute(stmt)
        families = result.scalars().all()
        assert len(families) == 2


class TestProductFamilyConstraints:
    """Test suite for ProductFamily database constraints."""

    async def test_cascade_delete_category_deletes_families(self, db_session: Session):
        """Test that deleting category CASCADE deletes families."""
        # Arrange - Create category and families
        category = ProductCategory(code="FERN", name="Fern")
        db_session.add(category)
        await db_session.commit()

        family1 = ProductFamily(category_id=category.id, name="Nephrolepis")
        family2 = ProductFamily(category_id=category.id, name="Adiantum")
        db_session.add_all([family1, family2])
        await db_session.commit()

        category_id = category.id

        # Verify families exist
        stmt = select(ProductFamily).where(ProductFamily.category_id == category_id)
        result = await db_session.execute(stmt)
        families_before = result.scalars().all()
        assert len(families_before) == 2

        # Act - Delete category
        db_session.delete(category)
        await db_session.commit()

        # Assert - Families should be CASCADE deleted
        result = await db_session.execute(stmt)
        families_after = result.scalars().all()
        assert len(families_after) == 0

    async def test_foreign_key_constraint_invalid_category(self, db_session: Session):
        """Test FK constraint violation with non-existent category_id."""
        # Arrange - Create family with invalid category_id
        family = ProductFamily(
            category_id=99999,  # Non-existent category
            name="Invalid Family",
        )
        db_session.add(family)

        # Act & Assert - Should raise IntegrityError
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.commit()

        # Verify error is FK constraint violation
        assert "foreign key constraint" in str(exc_info.value).lower()

    async def test_not_null_constraint_name(self, db_session: Session):
        """Test NOT NULL constraint on name field."""
        # Arrange - Create category
        category = ProductCategory(code="TROPICAL", name="Tropical Plant")
        db_session.add(category)
        await db_session.commit()

        # Act - Create family without name
        family = ProductFamily(
            category_id=category.id,
            name=None,  # NULL name
        )
        db_session.add(family)

        # Assert - Should raise IntegrityError
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.commit()

        assert (
            "not-null constraint" in str(exc_info.value).lower()
            or "null value" in str(exc_info.value).lower()
        )

    async def test_not_null_constraint_category_id(self, db_session: Session):
        """Test NOT NULL constraint on category_id field."""
        # Act - Create family without category_id
        family = ProductFamily(
            category_id=None,  # NULL category_id
            name="No Category Family",
        )
        db_session.add(family)

        # Assert - Should raise IntegrityError
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.commit()

        assert (
            "not-null constraint" in str(exc_info.value).lower()
            or "null value" in str(exc_info.value).lower()
        )


class TestProductFamilyUpdateDelete:
    """Test suite for ProductFamily update and delete operations."""

    async def test_update_family_name(self, db_session: Session):
        """Test updating family name."""
        # Arrange - Create category and family
        category = ProductCategory(code="HERB", name="Herb")
        db_session.add(category)
        await db_session.commit()

        family = ProductFamily(category_id=category.id, name="Menta")
        db_session.add(family)
        await db_session.commit()
        family_id = family.family_id

        # Act - Update name
        family.name = "Mentha"
        await db_session.commit()

        # Assert - Verify update
        stmt = select(ProductFamily).where(ProductFamily.family_id == family_id)
        result = await db_session.execute(stmt)
        updated_family = result.scalar_one()
        assert updated_family.name == "Mentha"

    async def test_delete_family(self, db_session: Session):
        """Test deleting a family (without deleting category)."""
        # Arrange - Create category and family
        category = ProductCategory(code="CACTUS", name="Cactus")
        db_session.add(category)
        await db_session.commit()

        family = ProductFamily(category_id=category.id, name="Mammillaria")
        db_session.add(family)
        await db_session.commit()
        family_id = family.family_id
        category_id = category.id

        # Act - Delete family
        db_session.delete(family)
        await db_session.commit()

        # Assert - Family deleted, category still exists
        stmt_family = select(ProductFamily).where(ProductFamily.family_id == family_id)
        result = await db_session.execute(stmt_family)
        deleted_family = result.scalar_one_or_none()
        assert deleted_family is None

        stmt_category = select(ProductCategory).where(
            ProductCategory.id == category_id
        )
        result = await db_session.execute(stmt_category)
        category_still_exists = result.scalar_one_or_none()
        assert category_still_exists is not None
