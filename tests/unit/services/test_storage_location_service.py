"""Unit tests for StorageLocationService.

Tests business logic with mocked repository and service dependencies.
No database access - uses AsyncMock.

TESTING STRATEGY:
- Mock StorageLocationRepository
- Mock WarehouseService and StorageAreaService (Service→Service pattern)
- Use REAL Shapely for geometry validation
- Mock geoalchemy2 functions for PostGIS conversion

Coverage target: ≥85%

Test categories:
- create_storage_location: success, duplicate code, area not found, geometry validation
- get_storage_location_by_id: success, not found
- get_location_by_gps: full chain (warehouse → area → location)
- get_locations_by_area: success
- update_storage_location: success, not found
- delete_storage_location: success, not found
- _validate_point_within_area: valid, out of bounds

See:
    - Service: app/services/storage_location_service.py
    - Task: backlog/03_kanban/00_backlog/S003-storage-location-service.md
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.exceptions import DuplicateCodeException, GeometryOutOfBoundsException
from app.schemas.storage_location_schema import (
    StorageLocationCreateRequest,
    StorageLocationUpdateRequest,
)
from app.services.storage_location_service import (
    StorageLocationNotFoundException,
    StorageLocationService,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_location_repo():
    """Create mock StorageLocationRepository."""
    return AsyncMock()


@pytest.fixture
def mock_warehouse_service():
    """Create mock WarehouseService."""
    return AsyncMock()


@pytest.fixture
def mock_area_service():
    """Create mock StorageAreaService."""
    return AsyncMock()


@pytest.fixture
def location_service(mock_location_repo, mock_warehouse_service, mock_area_service):
    """Create StorageLocationService with mocked dependencies."""
    return StorageLocationService(
        location_repo=mock_location_repo,
        warehouse_service=mock_warehouse_service,
        area_service=mock_area_service,
    )


@pytest.fixture
def sample_point_geojson():
    """Valid GeoJSON Point for storage location."""
    return {
        "type": "Point",
        "coordinates": [-70.6482, -33.4492],  # Center of area
    }


@pytest.fixture
def sample_area_geojson():
    """Valid GeoJSON polygon for storage area (contains point)."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.6483, -33.4493],
                [-70.6481, -33.4493],
                [-70.6481, -33.4491],
                [-70.6483, -33.4491],
                [-70.6483, -33.4493],
            ]
        ],
    }


@pytest.fixture
def mock_storage_location(sample_point_geojson):
    """Create mock StorageLocation model instance."""
    location = Mock()
    location.storage_location_id = 1
    location.storage_area_id = 1
    location.code = "GH-001-NORTH-LOC01"
    location.name = "Location 01"
    location.qr_code = "QR-LOC-001"
    location.coordinates = "mocked_wkb_point"
    location.centroid = "mocked_wkb_point"
    location.area_m2 = 0.0
    location.position_metadata = {}
    location.active = True
    location.created_at = datetime(2025, 10, 20, 14, 30, 0)
    location.updated_at = None
    return location


@pytest.fixture
def mock_storage_area(sample_area_geojson):
    """Create mock StorageArea response from StorageAreaService."""
    area = Mock()
    area.storage_area_id = 1
    area.code = "GH-001-NORTH"
    area.name = "North Wing"
    area.geojson_coordinates = sample_area_geojson
    return area


@pytest.fixture
def mock_warehouse():
    """Create mock Warehouse response from WarehouseService."""
    warehouse = Mock()
    warehouse.warehouse_id = 1
    warehouse.code = "GH-001"
    warehouse.name = "Main Greenhouse"
    return warehouse


# ============================================================================
# create_storage_location tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_storage_location_success(
    location_service,
    mock_location_repo,
    mock_area_service,
    sample_point_geojson,
    mock_storage_area,
    mock_storage_location,
):
    """Test successful storage location creation."""
    # Arrange
    mock_area_service.get_storage_area_by_id.return_value = mock_storage_area
    mock_location_repo.get_by_field.return_value = None  # No duplicate
    mock_location_repo.create.return_value = mock_storage_location

    request = StorageLocationCreateRequest(
        storage_area_id=1,
        code="GH-001-NORTH-LOC01",
        name="Location 01",
        qr_code="QR-LOC-001",
        coordinates=sample_point_geojson,
    )

    # Act
    with patch("geoalchemy2.shape.from_shape") as mock_from_shape:
        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_from_shape.return_value = "mocked_postgis_point"

            point_mock = Mock()
            point_mock.__geo_interface__ = sample_point_geojson

            mock_to_shape.side_effect = [point_mock, point_mock]  # coordinates, centroid

            result = await location_service.create_storage_location(request)

    # Assert
    assert result.storage_location_id == 1
    assert result.code == "GH-001-NORTH-LOC01"
    assert result.name == "Location 01"
    mock_area_service.get_storage_area_by_id.assert_called_once_with(1)
    mock_location_repo.get_by_field.assert_called_once_with("code", "GH-001-NORTH-LOC01")
    mock_location_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_storage_location_duplicate_code(
    location_service,
    mock_location_repo,
    mock_area_service,
    mock_storage_area,
    mock_storage_location,
    sample_point_geojson,
):
    """Test duplicate code rejection."""
    # Arrange
    mock_area_service.get_storage_area_by_id.return_value = mock_storage_area
    mock_location_repo.get_by_field.return_value = mock_storage_location  # Duplicate exists

    request = StorageLocationCreateRequest(
        storage_area_id=1,
        code="GH-001-NORTH-LOC01",
        name="Another Location",
        coordinates=sample_point_geojson,
    )

    # Act & Assert
    with pytest.raises(DuplicateCodeException) as exc_info:
        await location_service.create_storage_location(request)

    assert "GH-001-NORTH-LOC01" in str(exc_info.value)
    mock_location_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_storage_location_point_outside_area(
    location_service, mock_location_repo, mock_area_service, mock_storage_area
):
    """Test geometry validation rejects point outside area polygon."""
    # Arrange
    mock_area_service.get_storage_area_by_id.return_value = mock_storage_area
    mock_location_repo.get_by_field.return_value = None

    # Point OUTSIDE area bounds
    outside_point = {
        "type": "Point",
        "coordinates": [-70.650, -33.450],  # Far outside
    }

    request = StorageLocationCreateRequest(
        storage_area_id=1,
        code="GH-001-NORTH-LOC99",
        name="Outside Location",
        coordinates=outside_point,
    )

    # Act & Assert
    with pytest.raises(GeometryOutOfBoundsException) as exc_info:
        await location_service.create_storage_location(request)

    assert "outside storage area boundaries" in str(exc_info.value).lower()
    mock_location_repo.create.assert_not_called()


# ============================================================================
# get_storage_location_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_storage_location_by_id_success(
    location_service, mock_location_repo, mock_storage_location, sample_point_geojson
):
    """Test successful storage location retrieval by ID."""
    # Arrange
    mock_location_repo.get.return_value = mock_storage_location

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        point_mock = Mock()
        point_mock.__geo_interface__ = sample_point_geojson

        mock_to_shape.side_effect = [point_mock, point_mock]

        result = await location_service.get_storage_location_by_id(1)

    # Assert
    assert result.storage_location_id == 1
    assert result.code == "GH-001-NORTH-LOC01"
    mock_location_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_storage_location_by_id_not_found(location_service, mock_location_repo):
    """Test StorageLocationNotFoundException when ID not found."""
    # Arrange
    mock_location_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(StorageLocationNotFoundException) as exc_info:
        await location_service.get_storage_location_by_id(999)

    assert "999" in str(exc_info.value)
    mock_location_repo.get.assert_called_once_with(999)


# ============================================================================
# get_location_by_gps tests (full chain)
# ============================================================================


@pytest.mark.asyncio
async def test_get_location_by_gps_success(
    location_service,
    mock_location_repo,
    mock_warehouse_service,
    mock_area_service,
    mock_warehouse,
    mock_storage_area,
    mock_storage_location,
    sample_point_geojson,
):
    """Test GPS-based full hierarchy lookup (warehouse → area → location)."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_gps.return_value = mock_warehouse
    mock_area_service.get_storage_area_by_gps.return_value = mock_storage_area

    # Mock session.execute to return location
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = mock_storage_location
    mock_location_repo.session.execute.return_value = mock_result

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        point_mock = Mock()
        point_mock.__geo_interface__ = sample_point_geojson

        mock_to_shape.side_effect = [point_mock, point_mock]

        result = await location_service.get_location_by_gps(-70.6482, -33.4492)

    # Assert
    assert result is not None
    assert result.storage_location_id == 1
    assert result.code == "GH-001-NORTH-LOC01"
    mock_warehouse_service.get_warehouse_by_gps.assert_called_once_with(-70.6482, -33.4492)
    mock_area_service.get_storage_area_by_gps.assert_called_once_with(
        -70.6482, -33.4492, warehouse_id=1
    )


@pytest.mark.asyncio
async def test_get_location_by_gps_warehouse_not_found(location_service, mock_warehouse_service):
    """Test GPS lookup returns None when warehouse not found."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_gps.return_value = None

    # Act
    result = await location_service.get_location_by_gps(-75.0, -35.0)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_location_by_gps_area_not_found(
    location_service, mock_warehouse_service, mock_area_service, mock_warehouse
):
    """Test GPS lookup returns None when area not found."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_gps.return_value = mock_warehouse
    mock_area_service.get_storage_area_by_gps.return_value = None

    # Act
    result = await location_service.get_location_by_gps(-70.6482, -33.4492)

    # Assert
    assert result is None


# ============================================================================
# get_locations_by_area tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_locations_by_area_success(
    location_service, mock_location_repo, mock_storage_location, sample_point_geojson
):
    """Test getting all locations for a storage area."""
    # Arrange
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = [mock_storage_location]
    mock_location_repo.session.execute.return_value = mock_result

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        point_mock = Mock()
        point_mock.__geo_interface__ = sample_point_geojson

        mock_to_shape.side_effect = [point_mock, point_mock]

        result = await location_service.get_locations_by_area(1)

    # Assert
    assert len(result) == 1
    assert result[0].storage_location_id == 1
    assert result[0].code == "GH-001-NORTH-LOC01"


# ============================================================================
# update_storage_location tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_storage_location_success(
    location_service, mock_location_repo, mock_storage_location, sample_point_geojson
):
    """Test successful storage location update (partial update)."""
    # Arrange
    mock_location_repo.get.return_value = mock_storage_location

    updated_location = Mock()
    updated_location.storage_location_id = 1
    updated_location.storage_area_id = 1
    updated_location.code = "GH-001-NORTH-LOC01"
    updated_location.name = "Updated Location"
    updated_location.qr_code = "QR-LOC-001"
    updated_location.coordinates = mock_storage_location.coordinates
    updated_location.centroid = mock_storage_location.centroid
    updated_location.area_m2 = 0.0
    updated_location.position_metadata = {}
    updated_location.active = True
    updated_location.created_at = mock_storage_location.created_at
    updated_location.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_location_repo.update.return_value = updated_location

    request = StorageLocationUpdateRequest(name="Updated Location")

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        point_mock = Mock()
        point_mock.__geo_interface__ = sample_point_geojson

        mock_to_shape.side_effect = [point_mock, point_mock]

        result = await location_service.update_storage_location(1, request)

    # Assert
    assert result.storage_location_id == 1
    assert result.name == "Updated Location"
    mock_location_repo.get.assert_called_once_with(1)
    mock_location_repo.update.assert_called_once_with(1, {"name": "Updated Location"})


@pytest.mark.asyncio
async def test_update_storage_location_not_found(location_service, mock_location_repo):
    """Test update raises StorageLocationNotFoundException when ID not found."""
    # Arrange
    mock_location_repo.get.return_value = None

    request = StorageLocationUpdateRequest(name="New Name")

    # Act & Assert
    with pytest.raises(StorageLocationNotFoundException) as exc_info:
        await location_service.update_storage_location(999, request)

    assert "999" in str(exc_info.value)
    mock_location_repo.get.assert_called_once_with(999)
    mock_location_repo.update.assert_not_called()


# ============================================================================
# delete_storage_location tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_storage_location_success(
    location_service, mock_location_repo, mock_storage_location
):
    """Test successful soft delete (set active=False)."""
    # Arrange
    mock_location_repo.get.return_value = mock_storage_location
    mock_location_repo.update.return_value = mock_storage_location

    # Act
    result = await location_service.delete_storage_location(1)

    # Assert
    assert result is True
    mock_location_repo.get.assert_called_once_with(1)
    mock_location_repo.update.assert_called_once_with(1, {"active": False})


@pytest.mark.asyncio
async def test_delete_storage_location_not_found(location_service, mock_location_repo):
    """Test delete raises StorageLocationNotFoundException when ID not found."""
    # Arrange
    mock_location_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(StorageLocationNotFoundException) as exc_info:
        await location_service.delete_storage_location(999)

    assert "999" in str(exc_info.value)
    mock_location_repo.get.assert_called_once_with(999)
    mock_location_repo.update.assert_not_called()


# ============================================================================
# _validate_point_within_area tests
# ============================================================================


def test_validate_point_within_area_valid(
    location_service, sample_point_geojson, sample_area_geojson
):
    """Test geometry validation accepts point within area."""
    # Act & Assert (should not raise)
    location_service._validate_point_within_area(sample_point_geojson, sample_area_geojson)


def test_validate_point_within_area_out_of_bounds(location_service, sample_area_geojson):
    """Test geometry validation rejects point outside area."""
    # Arrange - Point OUTSIDE area
    outside_point = {
        "type": "Point",
        "coordinates": [-70.650, -33.450],
    }

    # Act & Assert
    with pytest.raises(GeometryOutOfBoundsException) as exc_info:
        location_service._validate_point_within_area(outside_point, sample_area_geojson)

    assert "outside storage area boundaries" in str(exc_info.value).lower()
