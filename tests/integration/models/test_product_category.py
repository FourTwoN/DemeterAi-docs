"""Integration tests for ProductCategory model.

Tests database persistence, constraints, and query operations against a real database.
These tests require the migration to be run first to load seed data.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import ProductCategory


@pytest.mark.integration
class TestProductCategoryDatabasePersistence:
    """Test database persistence and constraints."""

    @pytest.mark.asyncio
    async def test_create_and_persist_category(self, db_session):
        """Test creating and persisting a category to database."""
        category = ProductCategory(
            code="TEST_CAT",
            name="Test Category",
            description="Integration test category",
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)

        assert category.id is not None
        assert category.code == "TEST_CAT"
        assert category.created_at is not None

    @pytest.mark.asyncio
    async def test_code_uniqueness_at_db_level(self, db_session):
        """Test duplicate code raises IntegrityError at DB level."""
        # Create first category
        category1 = ProductCategory(code="UNIQUE_TEST", name="Test Category 1", description="First")
        db_session.add(category1)
        await db_session.commit()

        # Try to create duplicate
        category2 = ProductCategory(
            code="UNIQUE_TEST", name="Test Category 2", description="Second"
        )
        db_session.add(category2)

        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_query_by_code(self, db_session):
        """Test querying category by code."""
        # Create test category
        category = ProductCategory(code="QUERY_TEST", name="Query Test", description="Test")
        db_session.add(category)
        await db_session.commit()

        # Query it back
        result = await db_session.execute(
            select(ProductCategory).where(ProductCategory.code == "QUERY_TEST")
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.code == "QUERY_TEST"
        assert found.name == "Query Test"

    @pytest.mark.asyncio
    async def test_update_category(self, db_session):
        """Test updating a category."""
        category = ProductCategory(code="UPDATE_TEST", name="Original Name", description="Test")
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)

        # Update
        category.name = "Updated Name"
        category.description = "Updated description"
        await db_session.commit()
        await db_session.refresh(category)

        assert category.name == "Updated Name"
        assert category.description == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_category(self, db_session):
        """Test deleting a category."""
        category = ProductCategory(code="DELETE_TEST", name="Delete Test", description="Test")
        db_session.add(category)
        await db_session.commit()

        category_id = category.id

        # Delete
        await db_session.delete(category)
        await db_session.commit()

        # Verify deleted
        result = await db_session.execute(
            select(ProductCategory).where(ProductCategory.id == category_id)
        )
        deleted = result.scalar_one_or_none()

        assert deleted is None

    @pytest.mark.asyncio
    async def test_order_by_name(self, db_session):
        """Test ORDER BY name query."""
        # Create test categories
        cat1 = ProductCategory(code="ZCAT", name="Zebra Category", description="Test")
        cat2 = ProductCategory(code="ACAT", name="Alpha Category", description="Test")
        cat3 = ProductCategory(code="MCAT", name="Middle Category", description="Test")

        db_session.add_all([cat1, cat2, cat3])
        await db_session.commit()

        # Query ordered by name
        result = await db_session.execute(select(ProductCategory).order_by(ProductCategory.name))
        categories = result.scalars().all()

        # Should have at least our 3 test categories
        assert len(categories) >= 3

        # Find our test categories
        test_cats = [c for c in categories if c.code in ["ZCAT", "ACAT", "MCAT"]]
        assert len(test_cats) == 3

        # Verify ordering
        assert test_cats[0].code == "ACAT"  # Alpha first
        assert test_cats[1].code == "MCAT"  # Middle second
        assert test_cats[2].code == "ZCAT"  # Zebra last

    @pytest.mark.asyncio
    async def test_count_categories(self, db_session):
        """Test COUNT query."""
        # Create a test category
        category = ProductCategory(code="COUNT_TEST", name="Count Test", description="Test")
        db_session.add(category)
        await db_session.commit()

        # Count all categories
        result = await db_session.execute(select(ProductCategory))
        count = len(result.scalars().all())

        assert count >= 1  # At least our test category
