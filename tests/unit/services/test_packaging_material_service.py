"""Unit tests for PackagingMaterialService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock PackagingMaterialRepository
- Test CRUD operations (create, get_by_id, get_all, update, delete)

Coverage target: ≥80%

Test categories:
- create: success
- get_by_id: success, not found
- get_all: success, empty list
- update: success, not found
- delete: success, not found

See:
    - Service: app/services/packaging_material_service.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.packaging_material_schema import (
    PackagingMaterialCreateRequest,
    PackagingMaterialResponse,
    PackagingMaterialUpdateRequest,
)
from app.services.packaging_material_service import PackagingMaterialService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_packaging_material_repo():
    """Create mock PackagingMaterialRepository."""
    return AsyncMock()


@pytest.fixture
def packaging_material_service(mock_packaging_material_repo):
    """Create PackagingMaterialService with mocked dependencies."""
    return PackagingMaterialService(repo=mock_packaging_material_repo)


@pytest.fixture
def mock_packaging_material():
    """Create mock PackagingMaterial model instance."""
    material = Mock()
    material.packaging_material_id = 1
    material.code = "PLASTIC"
    material.name = "Plastic"
    material.created_at = datetime(2025, 10, 20, 14, 30, 0)
    material.updated_at = None
    return material


# ============================================================================
# create tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_packaging_material_success(
    packaging_material_service, mock_packaging_material_repo, mock_packaging_material
):
    """Test successful packaging material creation."""
    # Arrange
    mock_packaging_material_repo.create.return_value = mock_packaging_material
    request = PackagingMaterialCreateRequest(code="PLASTIC", name="Plastic")

    # Act
    result = await packaging_material_service.create(request)

    # Assert
    assert isinstance(result, PackagingMaterialResponse)
    assert result.packaging_material_id == 1
    assert result.code == "PLASTIC"
    assert result.name == "Plastic"
    mock_packaging_material_repo.create.assert_called_once()
    call_args = mock_packaging_material_repo.create.call_args[0][0]
    assert call_args["code"] == "PLASTIC"
    assert call_args["name"] == "Plastic"


# ============================================================================
# get_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(
    packaging_material_service, mock_packaging_material_repo, mock_packaging_material
):
    """Test successful retrieval by ID."""
    # Arrange
    mock_packaging_material_repo.get.return_value = mock_packaging_material

    # Act
    result = await packaging_material_service.get_by_id(1)

    # Assert
    assert isinstance(result, PackagingMaterialResponse)
    assert result.packaging_material_id == 1
    assert result.code == "PLASTIC"
    assert result.name == "Plastic"
    mock_packaging_material_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(packaging_material_service, mock_packaging_material_repo):
    """Test ValueError when ID not found."""
    # Arrange
    mock_packaging_material_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_material_service.get_by_id(999)

    mock_packaging_material_repo.get.assert_called_once_with(999)


# ============================================================================
# get_all tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(
    packaging_material_service, mock_packaging_material_repo, mock_packaging_material
):
    """Test successful retrieval of all packaging materials."""
    # Arrange
    mock_material_2 = Mock()
    mock_material_2.packaging_material_id = 2
    mock_material_2.code = "CERAMIC"
    mock_material_2.name = "Ceramic"
    mock_material_2.created_at = datetime(2025, 10, 20, 15, 0, 0)
    mock_material_2.updated_at = None

    mock_packaging_material_repo.get_multi.return_value = [
        mock_packaging_material,
        mock_material_2,
    ]

    # Act
    result = await packaging_material_service.get_all(limit=100)

    # Assert
    assert len(result) == 2
    assert result[0].packaging_material_id == 1
    assert result[0].code == "PLASTIC"
    assert result[1].packaging_material_id == 2
    assert result[1].code == "CERAMIC"
    mock_packaging_material_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(packaging_material_service, mock_packaging_material_repo):
    """Test get_all returns empty list when no records exist."""
    # Arrange
    mock_packaging_material_repo.get_multi.return_value = []

    # Act
    result = await packaging_material_service.get_all()

    # Assert
    assert result == []
    mock_packaging_material_repo.get_multi.assert_called_once()


# ============================================================================
# update tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_packaging_material_success(
    packaging_material_service, mock_packaging_material_repo, mock_packaging_material
):
    """Test successful packaging material update."""
    # Arrange
    updated_material = Mock()
    updated_material.packaging_material_id = 1
    updated_material.code = "PLASTIC"
    updated_material.name = "Plastic - Recycled"
    updated_material.created_at = datetime(2025, 10, 20, 14, 30, 0)
    updated_material.updated_at = datetime(2025, 10, 20, 16, 0, 0)

    mock_packaging_material_repo.get.return_value = mock_packaging_material
    mock_packaging_material_repo.update.return_value = updated_material

    request = PackagingMaterialUpdateRequest(name="Plastic - Recycled")

    # Act
    result = await packaging_material_service.update(1, request)

    # Assert
    assert isinstance(result, PackagingMaterialResponse)
    assert result.packaging_material_id == 1
    assert result.name == "Plastic - Recycled"
    mock_packaging_material_repo.get.assert_called_once_with(1)
    mock_packaging_material_repo.update.assert_called_once()
    call_args = mock_packaging_material_repo.update.call_args[0]
    assert call_args[0] == 1
    assert call_args[1]["name"] == "Plastic - Recycled"


@pytest.mark.asyncio
async def test_update_packaging_material_not_found(
    packaging_material_service, mock_packaging_material_repo
):
    """Test ValueError when updating non-existent packaging material."""
    # Arrange
    mock_packaging_material_repo.get.return_value = None
    request = PackagingMaterialUpdateRequest(name="Updated")

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_material_service.update(999, request)

    mock_packaging_material_repo.get.assert_called_once_with(999)
    mock_packaging_material_repo.update.assert_not_called()


# ============================================================================
# delete tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_packaging_material_success(
    packaging_material_service, mock_packaging_material_repo, mock_packaging_material
):
    """Test successful packaging material deletion."""
    # Arrange
    mock_packaging_material_repo.get.return_value = mock_packaging_material
    mock_packaging_material_repo.delete.return_value = None

    # Act
    result = await packaging_material_service.delete(1)

    # Assert
    assert result is None
    mock_packaging_material_repo.get.assert_called_once_with(1)
    mock_packaging_material_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_packaging_material_not_found(
    packaging_material_service, mock_packaging_material_repo
):
    """Test ValueError when deleting non-existent packaging material."""
    # Arrange
    mock_packaging_material_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_material_service.delete(999)

    mock_packaging_material_repo.get.assert_called_once_with(999)
    mock_packaging_material_repo.delete.assert_not_called()
