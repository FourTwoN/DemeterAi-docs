"""Unit tests for ProductCategoryService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock for ProductCategoryRepository.

Coverage target: ≥85%

Test categories:
- create_category: success, duplicate handling
- get_category_by_id: success, not found
- get_all_categories: empty, multiple categories
- update_category: success, not found
- delete_category: success, not found

See:
    - Service: app/services/product_category_service.py
    - Task: backlog/03_kanban/00_backlog/S019-product-category-service.md
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.product_category import ProductCategory
from app.schemas.product_category_schema import (
    ProductCategoryCreateRequest,
    ProductCategoryResponse,
    ProductCategoryUpdateRequest,
)
from app.services.product_category_service import ProductCategoryService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_category_repo():
    """Create mock ProductCategoryRepository for testing."""
    return AsyncMock()


@pytest.fixture
def category_service(mock_category_repo):
    """Create ProductCategoryService with mocked repository."""
    return ProductCategoryService(category_repo=mock_category_repo)


@pytest.fixture
def mock_category():
    """Create mock ProductCategory model instance."""
    category = Mock(spec=ProductCategory)
    category.id = 1
    category.code = "CACTUS"
    category.name = "Cactus"
    category.description = "Cacti family (Cactaceae)"
    category.created_at = datetime(2025, 10, 20, 14, 30, 0)
    category.updated_at = None
    return category


@pytest.fixture
def sample_create_request():
    """Sample create request."""
    return ProductCategoryCreateRequest(
        code="SUCCULENT", name="Succulent", description="Succulent plants"
    )


# ============================================================================
# Test Create Category
# ============================================================================


@pytest.mark.asyncio
async def test_create_category_success(category_service, mock_category_repo, mock_category):
    """Test successful category creation."""
    # Arrange
    request = ProductCategoryCreateRequest(code="CACTUS", name="Cactus", description="Cacti family")
    mock_category_repo.create.return_value = mock_category

    # Act
    response = await category_service.create_category(request)

    # Assert
    assert isinstance(response, ProductCategoryResponse)
    assert response.id == 1
    assert response.code == "CACTUS"
    assert response.name == "Cactus"
    mock_category_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_category_minimal_fields(category_service, mock_category_repo):
    """Test creating category with only required fields."""
    # Arrange
    request = ProductCategoryCreateRequest(code="ORCHID", name="Orchid")

    mock_minimal = Mock(spec=ProductCategory)
    mock_minimal.id = 2
    mock_minimal.code = "ORCHID"
    mock_minimal.name = "Orchid"
    mock_minimal.description = None
    mock_minimal.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_minimal.updated_at = None

    mock_category_repo.create.return_value = mock_minimal

    # Act
    response = await category_service.create_category(request)

    # Assert
    assert response.code == "ORCHID"
    assert response.description is None


# ============================================================================
# Test Get Category
# ============================================================================


@pytest.mark.asyncio
async def test_get_category_by_id_success(category_service, mock_category_repo, mock_category):
    """Test getting category by ID successfully."""
    # Arrange
    mock_category_repo.get.return_value = mock_category

    # Act
    response = await category_service.get_category_by_id(1)

    # Assert
    assert response.id == 1
    assert response.code == "CACTUS"
    mock_category_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_category_by_id_not_found(category_service, mock_category_repo):
    """Test getting non-existent category raises ValueError."""
    # Arrange
    mock_category_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="ProductCategory 999 not found"):
        await category_service.get_category_by_id(999)


# ============================================================================
# Test Get All Categories
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_categories_success(category_service, mock_category_repo):
    """Test getting all categories."""
    # Arrange
    mock_cat1 = Mock(spec=ProductCategory)
    mock_cat1.id = 1
    mock_cat1.code = "CACTUS"
    mock_cat1.name = "Cactus"
    mock_cat1.description = "Cacti"
    mock_cat1.created_at = datetime(2025, 10, 20, 14, 0, 0)
    mock_cat1.updated_at = None

    mock_cat2 = Mock(spec=ProductCategory)
    mock_cat2.id = 2
    mock_cat2.code = "SUCCULENT"
    mock_cat2.name = "Succulent"
    mock_cat2.description = "Succulents"
    mock_cat2.created_at = datetime(2025, 10, 20, 14, 30, 0)
    mock_cat2.updated_at = None

    mock_category_repo.get_multi.return_value = [mock_cat1, mock_cat2]

    # Act
    response = await category_service.get_all_categories()

    # Assert
    assert len(response) == 2
    assert response[0].code == "CACTUS"
    assert response[1].code == "SUCCULENT"
    mock_category_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_categories_empty(category_service, mock_category_repo):
    """Test getting categories when none exist."""
    # Arrange
    mock_category_repo.get_multi.return_value = []

    # Act
    response = await category_service.get_all_categories()

    # Assert
    assert len(response) == 0


@pytest.mark.asyncio
async def test_get_all_categories_active_only_flag(category_service, mock_category_repo):
    """Test active_only parameter (reserved for future soft delete)."""
    # Arrange
    mock_category_repo.get_multi.return_value = []

    # Act
    await category_service.get_all_categories(active_only=True)
    await category_service.get_all_categories(active_only=False)

    # Assert - Both calls should behave the same (parameter reserved for future)
    assert mock_category_repo.get_multi.call_count == 2


# ============================================================================
# Test Update Category
# ============================================================================


@pytest.mark.asyncio
async def test_update_category_success(category_service, mock_category_repo, mock_category):
    """Test updating category successfully."""
    # Arrange
    request = ProductCategoryUpdateRequest(
        name="Updated Cactus Name", description="Updated description"
    )

    updated_mock = Mock(spec=ProductCategory)
    updated_mock.id = 1
    updated_mock.code = "CACTUS"
    updated_mock.name = "Updated Cactus Name"
    updated_mock.description = "Updated description"
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_category_repo.get.return_value = mock_category
    mock_category_repo.update.return_value = updated_mock

    # Act
    response = await category_service.update_category(1, request)

    # Assert
    assert response.name == "Updated Cactus Name"
    assert response.description == "Updated description"
    assert response.updated_at is not None
    mock_category_repo.get.assert_called_once_with(1)
    mock_category_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_category_not_found(category_service, mock_category_repo):
    """Test updating non-existent category raises ValueError."""
    # Arrange
    request = ProductCategoryUpdateRequest(name="Updated Name")
    mock_category_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="ProductCategory 999 not found"):
        await category_service.update_category(999, request)


@pytest.mark.asyncio
async def test_update_category_partial(category_service, mock_category_repo, mock_category):
    """Test partial update (only name, no description)."""
    # Arrange
    request = ProductCategoryUpdateRequest(name="New Name Only")

    updated_mock = Mock(spec=ProductCategory)
    updated_mock.id = 1
    updated_mock.code = "CACTUS"
    updated_mock.name = "New Name Only"
    updated_mock.description = "Cacti family (Cactaceae)"  # Unchanged
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_category_repo.get.return_value = mock_category
    mock_category_repo.update.return_value = updated_mock

    # Act
    response = await category_service.update_category(1, request)

    # Assert
    assert response.name == "New Name Only"
    # Verify update was called with only the fields that were set
    call_args = mock_category_repo.update.call_args
    assert "name" in call_args[0][1]


# ============================================================================
# Test Delete Category
# ============================================================================


@pytest.mark.asyncio
async def test_delete_category_success(category_service, mock_category_repo, mock_category):
    """Test deleting category successfully."""
    # Arrange
    mock_category_repo.get.return_value = mock_category
    mock_category_repo.delete.return_value = None

    # Act
    await category_service.delete_category(1)

    # Assert
    mock_category_repo.get.assert_called_once_with(1)
    mock_category_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_category_not_found(category_service, mock_category_repo):
    """Test deleting non-existent category raises ValueError."""
    # Arrange
    mock_category_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="ProductCategory 999 not found"):
        await category_service.delete_category(999)
