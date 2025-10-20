"""Unit tests for LocationHierarchyService.

Tests aggregation logic with mocked service dependencies.
This service orchestrates warehouse → area → location → bin hierarchy.

TESTING STRATEGY:
- Mock WarehouseService, StorageAreaService, StorageLocationService, StorageBinService
- Test full hierarchy aggregation
- Test GPS lookup chain
- No database access (all services mocked)

Coverage target: ≥85%

Test categories:
- get_full_hierarchy: success, multiple areas/locations/bins
- lookup_gps_full_chain: success, location not found

See:
    - Service: app/services/location_hierarchy_service.py
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.services.location_hierarchy_service import LocationHierarchyService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_warehouse_service():
    """Create mock WarehouseService."""
    return AsyncMock()


@pytest.fixture
def mock_area_service():
    """Create mock StorageAreaService."""
    return AsyncMock()


@pytest.fixture
def mock_location_service():
    """Create mock StorageLocationService."""
    return AsyncMock()


@pytest.fixture
def mock_bin_service():
    """Create mock StorageBinService."""
    return AsyncMock()


@pytest.fixture
def hierarchy_service(
    mock_warehouse_service, mock_area_service, mock_location_service, mock_bin_service
):
    """Create LocationHierarchyService with all mocked dependencies."""
    return LocationHierarchyService(
        warehouse_service=mock_warehouse_service,
        area_service=mock_area_service,
        location_service=mock_location_service,
        bin_service=mock_bin_service,
    )


@pytest.fixture
def mock_warehouse():
    """Mock warehouse response."""
    warehouse = Mock()
    warehouse.warehouse_id = 1
    warehouse.code = "GH-001"
    warehouse.name = "Main Greenhouse"
    return warehouse


@pytest.fixture
def mock_area():
    """Mock storage area response."""
    area = Mock()
    area.storage_area_id = 1
    area.code = "GH-001-NORTH"
    area.name = "North Wing"
    return area


@pytest.fixture
def mock_location():
    """Mock storage location response."""
    location = Mock()
    location.storage_location_id = 1
    location.code = "GH-001-NORTH-LOC01"
    location.name = "Location 01"
    return location


@pytest.fixture
def mock_bin():
    """Mock storage bin response."""
    bin_obj = Mock()
    bin_obj.storage_bin_id = 1
    bin_obj.code = "BIN-001"
    bin_obj.label = "Bin 1"
    return bin_obj


# ============================================================================
# get_full_hierarchy tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_full_hierarchy_success(
    hierarchy_service,
    mock_warehouse_service,
    mock_area_service,
    mock_location_service,
    mock_bin_service,
    mock_warehouse,
    mock_area,
    mock_location,
    mock_bin,
):
    """Test full hierarchy retrieval (warehouse → areas → locations → bins)."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_id.return_value = mock_warehouse
    mock_area_service.get_areas_by_warehouse.return_value = [mock_area]
    mock_location_service.get_locations_by_area.return_value = [mock_location]
    mock_bin_service.get_bins_by_location.return_value = [mock_bin]

    # Act
    result = await hierarchy_service.get_full_hierarchy(1)

    # Assert
    assert result["warehouse"] == mock_warehouse
    assert len(result["areas"]) == 1
    assert result["areas"][0]["area"] == mock_area
    assert len(result["areas"][0]["locations"]) == 1
    assert result["areas"][0]["locations"][0]["location"] == mock_location
    assert len(result["areas"][0]["locations"][0]["bins"]) == 1
    assert result["areas"][0]["locations"][0]["bins"][0] == mock_bin

    mock_warehouse_service.get_warehouse_by_id.assert_called_once_with(1)
    mock_area_service.get_areas_by_warehouse.assert_called_once_with(1)
    mock_location_service.get_locations_by_area.assert_called_once_with(1)
    mock_bin_service.get_bins_by_location.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_full_hierarchy_multiple_areas(
    hierarchy_service,
    mock_warehouse_service,
    mock_area_service,
    mock_location_service,
    mock_bin_service,
    mock_warehouse,
):
    """Test hierarchy with multiple areas."""
    # Arrange
    area1 = Mock()
    area1.storage_area_id = 1
    area1.name = "North"

    area2 = Mock()
    area2.storage_area_id = 2
    area2.name = "South"

    location1 = Mock()
    location1.storage_location_id = 1

    location2 = Mock()
    location2.storage_location_id = 2

    bin1 = Mock()
    bin2 = Mock()

    mock_warehouse_service.get_warehouse_by_id.return_value = mock_warehouse
    mock_area_service.get_areas_by_warehouse.return_value = [area1, area2]
    mock_location_service.get_locations_by_area.side_effect = [
        [location1],  # area1 locations
        [location2],  # area2 locations
    ]
    mock_bin_service.get_bins_by_location.side_effect = [
        [bin1],  # location1 bins
        [bin2],  # location2 bins
    ]

    # Act
    result = await hierarchy_service.get_full_hierarchy(1)

    # Assert
    assert len(result["areas"]) == 2
    assert result["areas"][0]["area"].name == "North"
    assert result["areas"][1]["area"].name == "South"


@pytest.mark.asyncio
async def test_get_full_hierarchy_empty_areas(
    hierarchy_service, mock_warehouse_service, mock_area_service, mock_warehouse
):
    """Test hierarchy with no areas (empty warehouse)."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_id.return_value = mock_warehouse
    mock_area_service.get_areas_by_warehouse.return_value = []

    # Act
    result = await hierarchy_service.get_full_hierarchy(1)

    # Assert
    assert result["warehouse"] == mock_warehouse
    assert result["areas"] == []


# ============================================================================
# lookup_gps_full_chain tests
# ============================================================================


@pytest.mark.asyncio
async def test_lookup_gps_full_chain_success(
    hierarchy_service, mock_location_service, mock_bin_service, mock_location, mock_bin
):
    """Test GPS lookup returns location with bins."""
    # Arrange
    mock_location_service.get_location_by_gps.return_value = mock_location
    mock_bin_service.get_bins_by_location.return_value = [mock_bin]

    # Act
    result = await hierarchy_service.lookup_gps_full_chain(-70.6482, -33.4492)

    # Assert
    assert result is not None
    assert result["location"] == mock_location
    assert len(result["bins"]) == 1
    assert result["bins"][0] == mock_bin
    mock_location_service.get_location_by_gps.assert_called_once_with(-70.6482, -33.4492)
    mock_bin_service.get_bins_by_location.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_lookup_gps_full_chain_location_not_found(hierarchy_service, mock_location_service):
    """Test GPS lookup returns None when location not found."""
    # Arrange
    mock_location_service.get_location_by_gps.return_value = None

    # Act
    result = await hierarchy_service.lookup_gps_full_chain(-75.0, -35.0)

    # Assert
    assert result is None
    mock_location_service.get_location_by_gps.assert_called_once_with(-75.0, -35.0)


@pytest.mark.asyncio
async def test_lookup_gps_full_chain_no_bins(
    hierarchy_service, mock_location_service, mock_bin_service, mock_location
):
    """Test GPS lookup with location but no bins."""
    # Arrange
    mock_location_service.get_location_by_gps.return_value = mock_location
    mock_bin_service.get_bins_by_location.return_value = []

    # Act
    result = await hierarchy_service.lookup_gps_full_chain(-70.6482, -33.4492)

    # Assert
    assert result is not None
    assert result["location"] == mock_location
    assert result["bins"] == []
