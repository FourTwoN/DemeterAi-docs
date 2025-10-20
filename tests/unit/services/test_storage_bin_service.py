"""Unit tests for StorageBinService.

Tests business logic with mocked repository and service dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock StorageBinRepository
- Mock StorageLocationService (Service→Service pattern)
- Test basic CRUD operations (leaf level, no geometry)

Coverage target: ≥85%

Test categories:
- create_storage_bin: success, duplicate code, location not found
- get_storage_bin_by_id: success, not found
- get_bins_by_location: success

See:
    - Service: app/services/storage_bin_service.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.storage_bin_schema import StorageBinCreateRequest
from app.services.storage_bin_service import (
    StorageBinNotFoundException,
    StorageBinService,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_bin_repo():
    """Create mock StorageBinRepository."""
    return AsyncMock()


@pytest.fixture
def mock_location_service():
    """Create mock StorageLocationService."""
    return AsyncMock()


@pytest.fixture
def bin_service(mock_bin_repo, mock_location_service):
    """Create StorageBinService with mocked dependencies."""
    return StorageBinService(bin_repo=mock_bin_repo, location_service=mock_location_service)


@pytest.fixture
def mock_storage_bin():
    """Create mock StorageBin model instance."""
    bin_obj = Mock()
    bin_obj.storage_bin_id = 1
    bin_obj.storage_location_id = 1
    bin_obj.storage_bin_type_id = 1
    bin_obj.code = "GH-001-NORTH-LOC01-BIN01"
    bin_obj.label = "Bin 01"
    bin_obj.position_metadata = {"bbox": {"x": 100, "y": 200, "width": 300, "height": 150}}
    bin_obj.status = Mock()
    bin_obj.status.value = "active"
    bin_obj.created_at = datetime(2025, 10, 20, 14, 30, 0)
    bin_obj.updated_at = None
    return bin_obj


@pytest.fixture
def mock_storage_location():
    """Create mock StorageLocation response from StorageLocationService."""
    location = Mock()
    location.storage_location_id = 1
    location.code = "GH-001-NORTH-LOC01"
    location.name = "Location 01"
    return location


# ============================================================================
# create_storage_bin tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_storage_bin_success(
    bin_service, mock_bin_repo, mock_location_service, mock_storage_location, mock_storage_bin
):
    """Test successful storage bin creation."""
    # Arrange
    mock_location_service.get_storage_location_by_id.return_value = mock_storage_location
    mock_bin_repo.get_by_field.return_value = None  # No duplicate
    mock_bin_repo.create.return_value = mock_storage_bin

    request = StorageBinCreateRequest(
        storage_location_id=1,
        storage_bin_type_id=1,
        code="GH-001-NORTH-LOC01-BIN01",
        label="Bin 01",
        position_metadata={"bbox": {"x": 100, "y": 200, "width": 300, "height": 150}},
        status="active",
    )

    # Act
    result = await bin_service.create_storage_bin(request)

    # Assert
    assert result.storage_bin_id == 1
    assert result.code == "GH-001-NORTH-LOC01-BIN01"
    assert result.label == "Bin 01"
    mock_location_service.get_storage_location_by_id.assert_called_once_with(1)
    mock_bin_repo.get_by_field.assert_called_once_with("code", "GH-001-NORTH-LOC01-BIN01")
    mock_bin_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_storage_bin_duplicate_code(
    bin_service, mock_bin_repo, mock_location_service, mock_storage_location, mock_storage_bin
):
    """Test duplicate code rejection."""
    # Arrange
    mock_location_service.get_storage_location_by_id.return_value = mock_storage_location
    mock_bin_repo.get_by_field.return_value = mock_storage_bin  # Duplicate exists

    request = StorageBinCreateRequest(
        storage_location_id=1,
        storage_bin_type_id=1,
        code="GH-001-NORTH-LOC01-BIN01",
        label="Another Bin",
        status="active",
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await bin_service.create_storage_bin(request)

    assert "GH-001-NORTH-LOC01-BIN01" in str(exc_info.value)
    mock_bin_repo.create.assert_not_called()


# ============================================================================
# get_storage_bin_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_storage_bin_by_id_success(bin_service, mock_bin_repo, mock_storage_bin):
    """Test successful storage bin retrieval by ID."""
    # Arrange
    mock_bin_repo.get.return_value = mock_storage_bin

    # Act
    result = await bin_service.get_storage_bin_by_id(1)

    # Assert
    assert result.storage_bin_id == 1
    assert result.code == "GH-001-NORTH-LOC01-BIN01"
    mock_bin_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_storage_bin_by_id_not_found(bin_service, mock_bin_repo):
    """Test StorageBinNotFoundException when ID not found."""
    # Arrange
    mock_bin_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(StorageBinNotFoundException) as exc_info:
        await bin_service.get_storage_bin_by_id(999)

    assert "999" in str(exc_info.value)
    mock_bin_repo.get.assert_called_once_with(999)


# ============================================================================
# get_bins_by_location tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_bins_by_location_success(bin_service, mock_bin_repo, mock_storage_bin):
    """Test getting all bins for a storage location."""
    # Arrange
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = [mock_storage_bin]
    mock_bin_repo.session.execute.return_value = mock_result

    # Act
    result = await bin_service.get_bins_by_location(1)

    # Assert
    assert len(result) == 1
    assert result[0].storage_bin_id == 1
    assert result[0].code == "GH-001-NORTH-LOC01-BIN01"
    mock_bin_repo.session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_bins_by_location_empty(bin_service, mock_bin_repo):
    """Test getting bins when location has none."""
    # Arrange
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = []
    mock_bin_repo.session.execute.return_value = mock_result

    # Act
    result = await bin_service.get_bins_by_location(1)

    # Assert
    assert result == []
    mock_bin_repo.session.execute.assert_called_once()
