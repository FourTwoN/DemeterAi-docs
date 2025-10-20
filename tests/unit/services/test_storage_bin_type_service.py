"""Unit tests for StorageBinTypeService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock StorageBinTypeRepository
- Test CRUD operations (create_bin_type, get_bin_type_by_id, get_all_bin_types)
- Note: This service only has 3 methods (no update/delete)

Coverage target: ≥80%

Test categories:
- create_bin_type: success
- get_bin_type_by_id: success, not found
- get_all_bin_types: success, empty list

See:
    - Service: app/services/storage_bin_type_service.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.storage_bin_type_schema import (
    StorageBinTypeCreateRequest,
    StorageBinTypeResponse,
)
from app.services.storage_bin_type_service import StorageBinTypeService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_bin_type_repo():
    """Create mock StorageBinTypeRepository."""
    return AsyncMock()


@pytest.fixture
def bin_type_service(mock_bin_type_repo):
    """Create StorageBinTypeService with mocked dependencies."""
    return StorageBinTypeService(bin_type_repo=mock_bin_type_repo)


@pytest.fixture
def mock_bin_type():
    """Create mock StorageBinType model instance."""
    bin_type = Mock()
    bin_type.storage_bin_type_id = 1
    bin_type.code = "SHELF"
    bin_type.name = "Shelf Type"
    bin_type.description = "Standard shelf for plant storage"
    bin_type.created_at = datetime(2025, 10, 20, 14, 30, 0)
    return bin_type


# ============================================================================
# create_bin_type tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_bin_type_success(bin_type_service, mock_bin_type_repo, mock_bin_type):
    """Test successful bin type creation."""
    # Arrange
    mock_bin_type_repo.create.return_value = mock_bin_type
    request = StorageBinTypeCreateRequest(
        code="SHELF", name="Shelf Type", description="Standard shelf for plant storage"
    )

    # Act
    result = await bin_type_service.create_bin_type(request)

    # Assert
    assert isinstance(result, StorageBinTypeResponse)
    assert result.storage_bin_type_id == 1
    assert result.code == "SHELF"
    assert result.name == "Shelf Type"
    assert result.description == "Standard shelf for plant storage"
    mock_bin_type_repo.create.assert_called_once()
    call_args = mock_bin_type_repo.create.call_args[0][0]
    assert call_args["code"] == "SHELF"
    assert call_args["name"] == "Shelf Type"
    assert call_args["description"] == "Standard shelf for plant storage"


@pytest.mark.asyncio
async def test_create_bin_type_without_description(bin_type_service, mock_bin_type_repo):
    """Test creating bin type without optional description."""
    # Arrange
    mock_type = Mock()
    mock_type.storage_bin_type_id = 2
    mock_type.code = "FLOOR"
    mock_type.name = "Floor Type"
    mock_type.description = None
    mock_type.created_at = datetime(2025, 10, 20, 14, 30, 0)

    mock_bin_type_repo.create.return_value = mock_type
    request = StorageBinTypeCreateRequest(code="FLOOR", name="Floor Type")

    # Act
    result = await bin_type_service.create_bin_type(request)

    # Assert
    assert result.storage_bin_type_id == 2
    assert result.code == "FLOOR"
    assert result.description is None


# ============================================================================
# get_bin_type_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_bin_type_by_id_success(bin_type_service, mock_bin_type_repo, mock_bin_type):
    """Test successful retrieval by ID."""
    # Arrange
    mock_bin_type_repo.get.return_value = mock_bin_type

    # Act
    result = await bin_type_service.get_bin_type_by_id(1)

    # Assert
    assert isinstance(result, StorageBinTypeResponse)
    assert result.storage_bin_type_id == 1
    assert result.code == "SHELF"
    assert result.name == "Shelf Type"
    assert result.description == "Standard shelf for plant storage"
    mock_bin_type_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_bin_type_by_id_not_found(bin_type_service, mock_bin_type_repo):
    """Test ValueError when ID not found."""
    # Arrange
    mock_bin_type_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="not found"):
        await bin_type_service.get_bin_type_by_id(999)

    mock_bin_type_repo.get.assert_called_once_with(999)


# ============================================================================
# get_all_bin_types tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_bin_types_success(bin_type_service, mock_bin_type_repo, mock_bin_type):
    """Test successful retrieval of all bin types."""
    # Arrange
    mock_type_2 = Mock()
    mock_type_2.storage_bin_type_id = 2
    mock_type_2.code = "FLOOR"
    mock_type_2.name = "Floor Type"
    mock_type_2.description = "Floor storage for large plants"
    mock_type_2.created_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_type_3 = Mock()
    mock_type_3.storage_bin_type_id = 3
    mock_type_3.code = "BENCH"
    mock_type_3.name = "Bench Type"
    mock_type_3.description = None
    mock_type_3.created_at = datetime(2025, 10, 20, 15, 30, 0)

    mock_bin_type_repo.get_multi.return_value = [mock_bin_type, mock_type_2, mock_type_3]

    # Act
    result = await bin_type_service.get_all_bin_types()

    # Assert
    assert len(result) == 3
    assert result[0].storage_bin_type_id == 1
    assert result[0].code == "SHELF"
    assert result[1].storage_bin_type_id == 2
    assert result[1].code == "FLOOR"
    assert result[2].storage_bin_type_id == 3
    assert result[2].code == "BENCH"
    assert result[2].description is None
    mock_bin_type_repo.get_multi.assert_called_once_with(limit=100)


@pytest.mark.asyncio
async def test_get_all_bin_types_empty(bin_type_service, mock_bin_type_repo):
    """Test get_all_bin_types returns empty list when no records exist."""
    # Arrange
    mock_bin_type_repo.get_multi.return_value = []

    # Act
    result = await bin_type_service.get_all_bin_types()

    # Assert
    assert result == []
    mock_bin_type_repo.get_multi.assert_called_once_with(limit=100)
