"""Unit tests for ProductFamilyService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock for ProductFamilyRepository.

Coverage target: ≥85%

Test categories:
- create_family: success, with parent validation
- get_family_by_id: success, not found
- get_all_families: empty, multiple families
- update_family: success, not found
- delete_family: success, not found

See:
    - Service: app/services/product_family_service.py
    - Task: backlog/03_kanban/00_backlog/S020-product-family-service.md
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.product_family import ProductFamily
from app.schemas.product_family_schema import (
    ProductFamilyCreateRequest,
    ProductFamilyResponse,
    ProductFamilyUpdateRequest,
)
from app.services.product_family_service import ProductFamilyService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_family_repo():
    """Create mock ProductFamilyRepository for testing."""
    return AsyncMock()


@pytest.fixture
def mock_category_repo():
    """Create mock ProductCategoryRepository for testing."""
    return AsyncMock()


@pytest.fixture
def family_service(mock_family_repo, mock_category_repo):
    """Create ProductFamilyService with mocked dependencies."""
    return ProductFamilyService(family_repo=mock_family_repo, category_repo=mock_category_repo)


@pytest.fixture
def mock_family():
    """Create mock ProductFamily model instance."""
    family = Mock(spec=ProductFamily)
    family.family_id = 1
    family.category_id = 1
    family.name = "Echeveria"
    family.scientific_name = "Echeveria spp."
    family.description = "Echeveria genus"
    family.created_at = datetime(2025, 10, 20, 14, 30, 0)
    family.updated_at = None
    return family


# ============================================================================
# Test Create Family
# ============================================================================


@pytest.mark.asyncio
async def test_create_family_success(
    family_service, mock_family_repo, mock_category_repo, mock_family
):
    """Test successful family creation with parent category validation."""
    # Arrange
    request = ProductFamilyCreateRequest(
        category_id=1,
        name="Echeveria",
        scientific_name="Echeveria spp.",
        description="Echeveria genus",
    )

    # Mock category repo validates parent exists
    mock_category_repo.get.return_value = Mock()
    mock_family_repo.create.return_value = mock_family

    # Act
    response = await family_service.create_family(request)

    # Assert
    assert isinstance(response, ProductFamilyResponse)
    assert response.family_id == 1
    assert response.category_id == 1
    assert response.name == "Echeveria"
    mock_category_repo.get.assert_called_once_with(1)
    mock_family_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_family_minimal_fields(family_service, mock_family_repo, mock_category_repo):
    """Test creating family with only required fields."""
    # Arrange
    request = ProductFamilyCreateRequest(category_id=1, name="Sedum")

    mock_minimal = Mock(spec=ProductFamily)
    mock_minimal.family_id = 2
    mock_minimal.category_id = 1
    mock_minimal.name = "Sedum"
    mock_minimal.scientific_name = None
    mock_minimal.description = None
    mock_minimal.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_minimal.updated_at = None

    mock_category_repo.get.return_value = Mock()
    mock_family_repo.create.return_value = mock_minimal

    # Act
    response = await family_service.create_family(request)

    # Assert
    assert response.name == "Sedum"
    assert response.scientific_name is None
    assert response.description is None


@pytest.mark.asyncio
async def test_create_family_invalid_category(family_service, mock_category_repo):
    """Test creating family with non-existent category raises ValueError."""
    # Arrange
    request = ProductFamilyCreateRequest(category_id=999, name="Invalid Family")

    # Mock category repo returns None (not found)
    mock_category_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="ProductCategory 999 not found"):
        await family_service.create_family(request)


# ============================================================================
# Test Get Family
# ============================================================================


@pytest.mark.asyncio
async def test_get_family_by_id_success(family_service, mock_family_repo, mock_family):
    """Test getting family by ID successfully."""
    # Arrange
    mock_family_repo.get.return_value = mock_family

    # Act
    response = await family_service.get_family_by_id(1)

    # Assert
    assert response.family_id == 1
    assert response.name == "Echeveria"
    mock_family_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_family_by_id_not_found(family_service, mock_family_repo):
    """Test getting non-existent family raises ValueError."""
    # Arrange
    mock_family_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="ProductFamily 999 not found"):
        await family_service.get_family_by_id(999)


# ============================================================================
# Test Get All Families
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_families_success(family_service, mock_family_repo):
    """Test getting all families."""
    # Arrange
    mock_fam1 = Mock(spec=ProductFamily)
    mock_fam1.family_id = 1
    mock_fam1.category_id = 1
    mock_fam1.name = "Echeveria"
    mock_fam1.scientific_name = "Echeveria spp."
    mock_fam1.description = "Echeveria genus"
    mock_fam1.created_at = datetime(2025, 10, 20, 14, 0, 0)
    mock_fam1.updated_at = None

    mock_fam2 = Mock(spec=ProductFamily)
    mock_fam2.family_id = 2
    mock_fam2.category_id = 1
    mock_fam2.name = "Sedum"
    mock_fam2.scientific_name = "Sedum spp."
    mock_fam2.description = "Sedum genus"
    mock_fam2.created_at = datetime(2025, 10, 20, 14, 30, 0)
    mock_fam2.updated_at = None

    mock_family_repo.get_multi.return_value = [mock_fam1, mock_fam2]

    # Act
    response = await family_service.get_all_families()

    # Assert
    assert len(response) == 2
    assert response[0].name == "Echeveria"
    assert response[1].name == "Sedum"
    mock_family_repo.get_multi.assert_called_once_with(limit=200)


@pytest.mark.asyncio
async def test_get_all_families_empty(family_service, mock_family_repo):
    """Test getting families when none exist."""
    # Arrange
    mock_family_repo.get_multi.return_value = []

    # Act
    response = await family_service.get_all_families()

    # Assert
    assert len(response) == 0


# ============================================================================
# Test Update Family
# ============================================================================


@pytest.mark.asyncio
async def test_update_family_success(family_service, mock_family_repo, mock_family):
    """Test updating family successfully."""
    # Arrange
    request = ProductFamilyUpdateRequest(
        name="Updated Echeveria Name", description="Updated description"
    )

    updated_mock = Mock(spec=ProductFamily)
    updated_mock.family_id = 1
    updated_mock.category_id = 1
    updated_mock.name = "Updated Echeveria Name"
    updated_mock.scientific_name = "Echeveria spp."
    updated_mock.description = "Updated description"
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_family_repo.get.return_value = mock_family
    mock_family_repo.update.return_value = updated_mock

    # Act
    response = await family_service.update_family(1, request)

    # Assert
    assert response.name == "Updated Echeveria Name"
    assert response.description == "Updated description"
    mock_family_repo.get.assert_called_once_with(1)
    mock_family_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_family_not_found(family_service, mock_family_repo):
    """Test updating non-existent family raises ValueError."""
    # Arrange
    request = ProductFamilyUpdateRequest(name="Updated Name")
    mock_family_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="ProductFamily 999 not found"):
        await family_service.update_family(999, request)


@pytest.mark.asyncio
async def test_update_family_partial(family_service, mock_family_repo, mock_family):
    """Test partial update (only name, no description)."""
    # Arrange
    request = ProductFamilyUpdateRequest(name="New Name Only")

    updated_mock = Mock(spec=ProductFamily)
    updated_mock.family_id = 1
    updated_mock.category_id = 1
    updated_mock.name = "New Name Only"
    updated_mock.scientific_name = "Echeveria spp."
    updated_mock.description = "Echeveria genus"  # Unchanged
    updated_mock.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_mock.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_family_repo.get.return_value = mock_family
    mock_family_repo.update.return_value = updated_mock

    # Act
    response = await family_service.update_family(1, request)

    # Assert
    assert response.name == "New Name Only"
    call_args = mock_family_repo.update.call_args
    assert "name" in call_args[0][1]


# ============================================================================
# Test Delete Family
# ============================================================================


@pytest.mark.asyncio
async def test_delete_family_success(family_service, mock_family_repo, mock_family):
    """Test deleting family successfully."""
    # Arrange
    mock_family_repo.get.return_value = mock_family
    mock_family_repo.delete.return_value = None

    # Act
    await family_service.delete_family(1)

    # Assert
    mock_family_repo.get.assert_called_once_with(1)
    mock_family_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_family_not_found(family_service, mock_family_repo):
    """Test deleting non-existent family raises ValueError."""
    # Arrange
    mock_family_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="ProductFamily 999 not found"):
        await family_service.delete_family(999)
