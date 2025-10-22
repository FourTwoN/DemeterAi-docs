"""Unit tests for PackagingTypeService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock PackagingTypeRepository
- Test CRUD operations (create, get_by_id, get_all, update, delete)

Coverage target: ≥80%

Test categories:
- create: success
- get_by_id: success, not found
- get_all: success, empty list
- update: success, not found
- delete: success, not found

See:
    - Service: app/services/packaging_type_service.py
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.packaging_type_schema import (
    PackagingTypeCreateRequest,
    PackagingTypeResponse,
    PackagingTypeUpdateRequest,
)
from app.services.packaging_type_service import PackagingTypeService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_packaging_type_repo():
    """Create mock PackagingTypeRepository."""
    return AsyncMock()


@pytest.fixture
def packaging_type_service(mock_packaging_type_repo):
    """Create PackagingTypeService with mocked dependencies."""
    return PackagingTypeService(repo=mock_packaging_type_repo)


@pytest.fixture
def mock_packaging_type():
    """Create mock PackagingType model instance."""
    packaging_type = Mock()
    packaging_type.id = 1
    packaging_type.code = "POT"
    packaging_type.name = "Pot"
    packaging_type.description = None
    return packaging_type


# ============================================================================
# create tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_packaging_type_success(
    packaging_type_service, mock_packaging_type_repo, mock_packaging_type
):
    """Test successful packaging type creation."""
    # Arrange
    mock_packaging_type_repo.create.return_value = mock_packaging_type
    request = PackagingTypeCreateRequest(code="POT", name="Pot")

    # Act
    result = await packaging_type_service.create(request)

    # Assert
    assert isinstance(result, PackagingTypeResponse)
    assert result.id == 1
    assert result.code == "POT"
    assert result.name == "Pot"
    mock_packaging_type_repo.create.assert_called_once()


# ============================================================================
# get_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_success(
    packaging_type_service, mock_packaging_type_repo, mock_packaging_type
):
    """Test successful retrieval by ID."""
    # Arrange
    mock_packaging_type_repo.get.return_value = mock_packaging_type

    # Act
    result = await packaging_type_service.get_by_id(1)

    # Assert
    assert isinstance(result, PackagingTypeResponse)
    assert result.id == 1
    assert result.code == "POT"
    assert result.name == "Pot"
    mock_packaging_type_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_by_id_not_found(packaging_type_service, mock_packaging_type_repo):
    """Test ValueError when ID not found."""
    # Arrange
    mock_packaging_type_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_type_service.get_by_id(999)

    mock_packaging_type_repo.get.assert_called_once_with(999)


# ============================================================================
# get_all tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_success(
    packaging_type_service, mock_packaging_type_repo, mock_packaging_type
):
    """Test successful retrieval of all packaging types."""
    # Arrange
    mock_packaging_type_2 = Mock()
    mock_packaging_type_2.id = 2
    mock_packaging_type_2.code = "TRAY"
    mock_packaging_type_2.name = "Tray"
    mock_packaging_type_2.description = None

    mock_packaging_type_repo.get_multi.return_value = [
        mock_packaging_type,
        mock_packaging_type_2,
    ]

    # Act
    result = await packaging_type_service.get_all(limit=100)

    # Assert
    assert len(result) == 2
    assert result[0].id == 1
    assert result[0].code == "POT"
    assert result[1].id == 2
    assert result[1].code == "TRAY"
    mock_packaging_type_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_empty(packaging_type_service, mock_packaging_type_repo):
    """Test get_all returns empty list when no records exist."""
    # Arrange
    mock_packaging_type_repo.get_multi.return_value = []

    # Act
    result = await packaging_type_service.get_all()

    # Assert
    assert result == []
    mock_packaging_type_repo.get_multi.assert_called_once()


# ============================================================================
# update tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_packaging_type_success(
    packaging_type_service, mock_packaging_type_repo, mock_packaging_type
):
    """Test successful packaging type update."""
    # Arrange
    updated_type = Mock()
    updated_type.id = 1
    updated_type.code = "POT"
    updated_type.name = "Pot - Updated"
    updated_type.description = None

    mock_packaging_type_repo.get.return_value = mock_packaging_type
    mock_packaging_type_repo.update.return_value = updated_type

    request = PackagingTypeUpdateRequest(name="Pot - Updated")

    # Act
    result = await packaging_type_service.update(1, request)

    # Assert
    assert isinstance(result, PackagingTypeResponse)
    assert result.id == 1
    assert result.name == "Pot - Updated"
    mock_packaging_type_repo.get.assert_called_once_with(1)
    mock_packaging_type_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_packaging_type_not_found(packaging_type_service, mock_packaging_type_repo):
    """Test ValueError when updating non-existent packaging type."""
    # Arrange
    mock_packaging_type_repo.get.return_value = None
    request = PackagingTypeUpdateRequest(name="Updated")

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_type_service.update(999, request)

    mock_packaging_type_repo.get.assert_called_once_with(999)
    mock_packaging_type_repo.update.assert_not_called()


# ============================================================================
# delete tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_packaging_type_success(
    packaging_type_service, mock_packaging_type_repo, mock_packaging_type
):
    """Test successful packaging type deletion."""
    # Arrange
    mock_packaging_type_repo.get.return_value = mock_packaging_type
    mock_packaging_type_repo.delete.return_value = None

    # Act
    result = await packaging_type_service.delete(1)

    # Assert
    assert result is None
    mock_packaging_type_repo.get.assert_called_once_with(1)
    mock_packaging_type_repo.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_packaging_type_not_found(packaging_type_service, mock_packaging_type_repo):
    """Test ValueError when deleting non-existent packaging type."""
    # Arrange
    mock_packaging_type_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await packaging_type_service.delete(999)

    mock_packaging_type_repo.get.assert_called_once_with(999)
    mock_packaging_type_repo.delete.assert_not_called()
