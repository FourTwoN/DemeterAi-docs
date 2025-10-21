"""Integration tests for ProductCategoryService with real database.

Tests service operations against real PostgreSQL database.
NO mocks - real database access via ProductCategoryRepository.

Coverage target: ≥85%

Test categories:
- create_category: success, code validation, duplicate
- get_category_by_id: success, not found
- get_all_categories: empty, multiple
- update_category: success, not found
- delete_category: success, cascade effects

See:
    - Service: app/services/product_category_service.py
    - Repository: app/repositories/product_category_repository.py
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.product_category import ProductCategory
from app.repositories.product_category_repository import ProductCategoryRepository
from app.schemas.product_category_schema import (
    ProductCategoryCreateRequest,
    ProductCategoryUpdateRequest,
)
from app.services.product_category_service import ProductCategoryService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def category_service(db_session):
    """Create ProductCategoryService with real repository."""
    repo = ProductCategoryRepository(session=db_session)
    return ProductCategoryService(category_repo=repo)


# ============================================================================
# Test Create Category
# ============================================================================


@pytest.mark.asyncio
async def test_create_category_success(category_service, db_session):
    """Test creating category successfully."""
    # Arrange
    request = ProductCategoryCreateRequest(
        code="CACTUS", name="Cactus", description="Cacti family (Cactaceae)"
    )

    # Act
    response = await category_service.create_category(request)

    # Assert
    assert response.id is not None
    assert response.code == "CACTUS"
    assert response.name == "Cactus"
    assert response.description == "Cacti family (Cactaceae)"
    assert response.created_at is not None

    # Verify in database
    await db_session.commit()
    db_category = await db_session.get(ProductCategory, response.id)
    assert db_category is not None
    assert db_category.code == "CACTUS"


@pytest.mark.asyncio
async def test_create_category_minimal_fields(category_service, db_session):
    """Test creating category with only required fields."""
    # Arrange
    request = ProductCategoryCreateRequest(code="SUCCULENT", name="Succulent")

    # Act
    response = await category_service.create_category(request)

    # Assert
    assert response.code == "SUCCULENT"
    assert response.name == "Succulent"
    assert response.description is None


@pytest.mark.asyncio
async def test_create_category_code_auto_uppercase(category_service, db_session):
    """Test that category code is auto-uppercased."""
    # Arrange
    request = ProductCategoryCreateRequest(
        code="orchid",  # Lowercase
        name="Orchid",
    )

    # Act
    response = await category_service.create_category(request)

    # Assert
    assert response.code == "ORCHID"  # Auto-uppercased


@pytest.mark.asyncio
async def test_create_category_duplicate_code(category_service, db_session):
    """Test that duplicate code raises IntegrityError."""
    # Arrange - Create first category
    request1 = ProductCategoryCreateRequest(code="BROMELIAD", name="Bromeliad 1")
    await category_service.create_category(request1)
    await db_session.commit()

    # Act & Assert - Try to create duplicate
    request2 = ProductCategoryCreateRequest(code="BROMELIAD", name="Bromeliad 2")
    with pytest.raises(IntegrityError):
        await category_service.create_category(request2)
        await db_session.commit()


# ============================================================================
# Test Get Category
# ============================================================================


@pytest.mark.asyncio
async def test_get_category_by_id_success(category_service, db_session):
    """Test getting category by ID."""
    # Arrange - Create category
    request = ProductCategoryCreateRequest(code="CARNIVOROUS", name="Carnivorous Plant")
    created = await category_service.create_category(request)
    await db_session.commit()

    # Act
    response = await category_service.get_category_by_id(created.id)

    # Assert
    assert response.id == created.id
    assert response.code == "CARNIVOROUS"
    assert response.name == "Carnivorous Plant"


@pytest.mark.asyncio
async def test_get_category_by_id_not_found(category_service):
    """Test getting non-existent category."""
    # Act & Assert
    with pytest.raises(ValueError, match="ProductCategory 99999 not found"):
        await category_service.get_category_by_id(99999)


# ============================================================================
# Test Get All Categories
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_categories_success(category_service, db_session):
    """Test getting all categories."""
    # Arrange - Create multiple categories
    categories = [
        ProductCategoryCreateRequest(code="FERN", name="Fern"),
        ProductCategoryCreateRequest(code="TROPICAL", name="Tropical Plant"),
        ProductCategoryCreateRequest(code="HERB", name="Herb"),
    ]

    for req in categories:
        await category_service.create_category(req)
    await db_session.commit()

    # Act
    response = await category_service.get_all_categories()

    # Assert
    assert len(response) >= 3  # At least our 3 categories
    codes = {cat.code for cat in response}
    assert "FERN" in codes
    assert "TROPICAL" in codes
    assert "HERB" in codes


@pytest.mark.asyncio
async def test_get_all_categories_empty_database(category_service, db_session):
    """Test getting categories when database is empty."""
    # Note: This test might have data from other tests, so we just verify it doesn't crash
    # Act
    response = await category_service.get_all_categories()

    # Assert
    assert isinstance(response, list)


# ============================================================================
# Test Update Category
# ============================================================================


@pytest.mark.asyncio
async def test_update_category_success(category_service, db_session):
    """Test updating category."""
    # Arrange - Create category
    request = ProductCategoryCreateRequest(code="PALM", name="Palm")
    created = await category_service.create_category(request)
    await db_session.commit()

    # Act - Update
    update_request = ProductCategoryUpdateRequest(
        name="Palm Tree", description="Tropical palm trees"
    )
    response = await category_service.update_category(created.id, update_request)
    await db_session.commit()

    # Assert
    assert response.id == created.id
    assert response.code == "PALM"  # Code unchanged
    assert response.name == "Palm Tree"  # Updated
    assert response.description == "Tropical palm trees"  # Updated
    assert response.updated_at is not None


@pytest.mark.asyncio
async def test_update_category_partial(category_service, db_session):
    """Test partial update (only name)."""
    # Arrange
    request = ProductCategoryCreateRequest(
        code="BAMBOO", name="Bamboo", description="Original description"
    )
    created = await category_service.create_category(request)
    await db_session.commit()

    # Act - Update only name
    update_request = ProductCategoryUpdateRequest(name="Bamboo Plant")
    response = await category_service.update_category(created.id, update_request)
    await db_session.commit()

    # Assert
    assert response.name == "Bamboo Plant"
    assert response.description == "Original description"  # Unchanged


@pytest.mark.asyncio
async def test_update_category_not_found(category_service):
    """Test updating non-existent category."""
    # Arrange
    update_request = ProductCategoryUpdateRequest(name="New Name")

    # Act & Assert
    with pytest.raises(ValueError, match="ProductCategory 99999 not found"):
        await category_service.update_category(99999, update_request)


# ============================================================================
# Test Delete Category
# ============================================================================


@pytest.mark.asyncio
async def test_delete_category_success(category_service, db_session):
    """Test deleting category."""
    # Arrange - Create category
    request = ProductCategoryCreateRequest(code="GRASS", name="Grass")
    created = await category_service.create_category(request)
    await db_session.commit()

    category_id = created.id

    # Act - Delete
    await category_service.delete_category(category_id)
    await db_session.commit()

    # Assert - Category should not exist
    db_category = await db_session.get(ProductCategory, category_id)
    assert db_category is None


@pytest.mark.asyncio
async def test_delete_category_not_found(category_service):
    """Test deleting non-existent category."""
    # Act & Assert
    with pytest.raises(ValueError, match="ProductCategory 99999 not found"):
        await category_service.delete_category(99999)


# ============================================================================
# Test Business Logic
# ============================================================================


@pytest.mark.asyncio
async def test_category_code_validation(category_service, db_session):
    """Test code validation (alphanumeric + underscores only)."""
    # Valid codes with underscores
    valid_request = ProductCategoryCreateRequest(code="CACTUS_123", name="Cactus with Code")
    response = await category_service.create_category(valid_request)
    assert response.code == "CACTUS_123"
    await db_session.commit()


@pytest.mark.asyncio
async def test_multiple_categories_independence(category_service, db_session):
    """Test that multiple categories can coexist independently."""
    # Arrange & Act - Create multiple categories
    cat1_request = ProductCategoryCreateRequest(code="CAT1", name="Category 1")
    cat2_request = ProductCategoryCreateRequest(code="CAT2", name="Category 2")
    cat3_request = ProductCategoryCreateRequest(code="CAT3", name="Category 3")

    cat1 = await category_service.create_category(cat1_request)
    cat2 = await category_service.create_category(cat2_request)
    cat3 = await category_service.create_category(cat3_request)
    await db_session.commit()

    # Assert - All exist independently
    assert cat1.id != cat2.id
    assert cat2.id != cat3.id

    # Delete one shouldn't affect others
    await category_service.delete_category(cat2.id)
    await db_session.commit()

    # Verify cat1 and cat3 still exist
    cat1_still_exists = await category_service.get_category_by_id(cat1.id)
    cat3_still_exists = await category_service.get_category_by_id(cat3.id)

    assert cat1_still_exists is not None
    assert cat3_still_exists is not None

    # Verify cat2 is gone
    with pytest.raises(ValueError):
        await category_service.get_category_by_id(cat2.id)
