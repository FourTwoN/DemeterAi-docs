"""Unit tests for StorageAreaService.

Tests business logic with mocked repository and service dependencies.
No database access - uses AsyncMock for StorageAreaRepository and WarehouseService.

TESTING STRATEGY:
- Mock repository methods (get, create, update, etc.)
- Mock WarehouseService (Service→Service pattern)
- Use REAL Shapely for geometry validation (business logic)
- Mock geoalchemy2 functions (from_shape, to_shape) for PostGIS conversion

Coverage target: ≥85%

Test categories:
- create_storage_area: success, duplicate code, warehouse not found, geometry out of bounds
- get_storage_area_by_id: success, not found
- get_storage_area_by_gps: found, not found
- get_areas_by_warehouse: with/without locations
- calculate_utilization: success, area not found
- update_storage_area: success, not found, geometry validation
- delete_storage_area: success, not found
- _validate_within_parent: valid, out of bounds

See:
    - Service: app/services/storage_area_service.py
    - Task: backlog/03_kanban/00_backlog/S002-storage-area-service.md
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.exceptions import (
    DuplicateCodeException,
    GeometryOutOfBoundsException,
    StorageAreaNotFoundException,
    WarehouseNotFoundException,
)
from app.models.storage_area import StorageArea
from app.schemas.storage_area_schema import (
    StorageAreaCreateRequest,
    StorageAreaUpdateRequest,
)
from app.services.storage_area_service import StorageAreaService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_area_repo():
    """Create mock StorageAreaRepository for testing."""
    mock = AsyncMock()
    # Add the model attribute that StorageAreaService uses for queries
    mock.model = StorageArea
    # Mock session.execute as async
    mock.session.execute = AsyncMock()
    return mock


@pytest.fixture
def mock_warehouse_service():
    """Create mock WarehouseService for testing."""
    return AsyncMock()


@pytest.fixture
def area_service(mock_area_repo, mock_warehouse_service):
    """Create StorageAreaService with mocked dependencies."""
    return StorageAreaService(
        storage_area_repo=mock_area_repo, warehouse_service=mock_warehouse_service
    )


@pytest.fixture
def sample_area_geojson():
    """Valid GeoJSON polygon for storage area (smaller than warehouse)."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.6483, -33.4493],
                [-70.6481, -33.4493],
                [-70.6481, -33.4491],
                [-70.6483, -33.4491],
                [-70.6483, -33.4493],  # Closed
            ]
        ],
    }


@pytest.fixture
def sample_warehouse_geojson():
    """Valid GeoJSON polygon for warehouse (larger than area)."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.648300, -33.448900],
                [-70.647300, -33.448900],
                [-70.647300, -33.449900],
                [-70.648300, -33.449900],
                [-70.648300, -33.448900],  # Closed
            ]
        ],
    }


@pytest.fixture
def mock_warehouse(sample_warehouse_geojson):
    """Create mock Warehouse response from WarehouseService."""
    warehouse = Mock()
    warehouse.warehouse_id = 1
    warehouse.code = "GH-001"
    warehouse.name = "Main Greenhouse"
    warehouse.geojson_coordinates = sample_warehouse_geojson
    return warehouse


@pytest.fixture
def mock_storage_area(sample_area_geojson):
    """Create mock StorageArea model instance."""
    area = Mock(spec=StorageArea)
    area.storage_area_id = 1
    area.warehouse_id = 1
    area.parent_area_id = None  # Missing field for Pydantic
    area.code = "GH-001-NORTH"
    area.name = "North Wing"
    area.position = Mock()
    area.position.value = "N"
    area.geojson_coordinates = "mocked_wkb_element_polygon"
    area.centroid = "mocked_wkb_element_point"
    area.area_m2 = 2500.50
    area.active = True
    area.created_at = datetime(2025, 10, 20, 14, 30, 0)
    area.updated_at = None
    area.storage_locations = []
    return area


# ============================================================================
# create_storage_area tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_storage_area_success(
    area_service,
    mock_area_repo,
    mock_warehouse_service,
    sample_area_geojson,
    sample_warehouse_geojson,
    mock_warehouse,
    mock_storage_area,
):
    """Test successful storage area creation."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_id.return_value = mock_warehouse
    mock_area_repo.get_by_field.return_value = None  # No duplicate
    mock_area_repo.create.return_value = mock_storage_area

    request = StorageAreaCreateRequest(
        warehouse_id=1,
        code="GH-001-NORTH",
        name="North Wing",
        position="N",
        geojson_coordinates=sample_area_geojson,
    )

    # Act - patch ONLY geoalchemy2 functions
    with patch("geoalchemy2.shape.from_shape") as mock_from_shape:
        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_from_shape.return_value = "mocked_postgis_geometry"

            # Mock to_shape for response conversion
            polygon_mock = Mock()
            polygon_mock.__geo_interface__ = sample_area_geojson

            point_mock = Mock()
            point_mock.__geo_interface__ = {
                "type": "Point",
                "coordinates": [-70.6482, -33.4492],
            }

            mock_to_shape.side_effect = [polygon_mock, point_mock]

            result = await area_service.create_storage_area(request)

    # Assert
    assert result.storage_area_id == 1
    assert result.code == "GH-001-NORTH"
    assert result.name == "North Wing"
    mock_warehouse_service.get_warehouse_by_id.assert_called_once_with(1)
    mock_area_repo.get_by_field.assert_called_once_with("code", "GH-001-NORTH")
    mock_area_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_storage_area_warehouse_not_found(
    area_service, mock_warehouse_service, sample_area_geojson
):
    """Test failure when parent warehouse doesn't exist."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_id.return_value = None

    request = StorageAreaCreateRequest(
        warehouse_id=999,
        code="GH-999-NORTH",
        name="Orphan Area",
        geojson_coordinates=sample_area_geojson,
    )

    # Act & Assert
    with pytest.raises(WarehouseNotFoundException) as exc_info:
        await area_service.create_storage_area(request)

    assert "999" in str(exc_info.value)
    mock_warehouse_service.get_warehouse_by_id.assert_called_once_with(999)


@pytest.mark.asyncio
async def test_create_storage_area_duplicate_code(
    area_service,
    mock_area_repo,
    mock_warehouse_service,
    mock_warehouse,
    mock_storage_area,
    sample_area_geojson,
):
    """Test duplicate code rejection."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_id.return_value = mock_warehouse
    mock_area_repo.get_by_field.return_value = mock_storage_area  # Duplicate exists

    request = StorageAreaCreateRequest(
        warehouse_id=1,
        code="GH-001-NORTH",
        name="Another North Wing",
        geojson_coordinates=sample_area_geojson,
    )

    # Act & Assert
    with pytest.raises(DuplicateCodeException) as exc_info:
        await area_service.create_storage_area(request)

    assert "GH-001-NORTH" in str(exc_info.value)
    mock_area_repo.get_by_field.assert_called_once_with("code", "GH-001-NORTH")
    mock_area_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_storage_area_geometry_out_of_bounds(
    area_service, mock_area_repo, mock_warehouse_service, mock_warehouse
):
    """Test geometry validation rejects area extending beyond warehouse."""
    # Arrange
    mock_warehouse_service.get_warehouse_by_id.return_value = mock_warehouse
    mock_area_repo.get_by_field.return_value = None

    # Area OUTSIDE warehouse bounds
    out_of_bounds_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.650, -33.450],  # Far outside warehouse
                [-70.649, -33.450],
                [-70.649, -33.451],
                [-70.650, -33.451],
                [-70.650, -33.450],
            ]
        ],
    }

    request = StorageAreaCreateRequest(
        warehouse_id=1,
        code="GH-001-OUTSIDE",
        name="Outside Area",
        geojson_coordinates=out_of_bounds_geojson,
    )

    # Act & Assert
    with pytest.raises(GeometryOutOfBoundsException) as exc_info:
        await area_service.create_storage_area(request)

    assert "beyond warehouse boundaries" in str(exc_info.value).lower()
    mock_area_repo.create.assert_not_called()


# ============================================================================
# get_storage_area_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_storage_area_by_id_success(
    area_service, mock_area_repo, mock_storage_area, sample_area_geojson
):
    """Test successful storage area retrieval by ID."""
    # Arrange
    mock_area_repo.get.return_value = mock_storage_area

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_area_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6482, -33.4492],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await area_service.get_storage_area_by_id(1)

    # Assert
    assert result.storage_area_id == 1
    assert result.code == "GH-001-NORTH"
    mock_area_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_storage_area_by_id_not_found(area_service, mock_area_repo):
    """Test StorageAreaNotFoundException when ID not found."""
    # Arrange
    mock_area_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(StorageAreaNotFoundException) as exc_info:
        await area_service.get_storage_area_by_id(999)

    assert "999" in str(exc_info.value)
    mock_area_repo.get.assert_called_once_with(999)


# ============================================================================
# get_storage_area_by_gps tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_storage_area_by_gps_found(
    area_service, mock_area_repo, mock_storage_area, sample_area_geojson
):
    """Test GPS-based storage area lookup (point inside polygon)."""
    # Arrange
    # Mock session.execute() to return a result with scalars().first()
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = mock_storage_area
    mock_area_repo.session.execute.return_value = mock_result

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_area_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6482, -33.4492],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await area_service.get_storage_area_by_gps(-70.6482, -33.4492)

    # Assert
    assert result is not None
    assert result.storage_area_id == 1
    assert result.code == "GH-001-NORTH"
    mock_area_repo.session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_storage_area_by_gps_not_found(area_service, mock_area_repo):
    """Test GPS lookup returns None when point outside all polygons."""
    # Arrange
    # Mock session.execute() to return no results
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = None
    mock_area_repo.session.execute.return_value = mock_result

    # Act
    result = await area_service.get_storage_area_by_gps(-75.0, -35.0)

    # Assert
    assert result is None
    mock_area_repo.session.execute.assert_called_once()


# ============================================================================
# get_areas_by_warehouse tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_areas_by_warehouse_without_locations(
    area_service, mock_area_repo, mock_storage_area, sample_area_geojson
):
    """Test getting areas without storage locations."""
    # Arrange
    # Mock session.execute() to return list of areas
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = [mock_storage_area]
    mock_area_repo.session.execute.return_value = mock_result

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_area_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6482, -33.4492],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await area_service.get_areas_by_warehouse(1, include_locations=False)

    # Assert
    assert len(result) == 1
    assert result[0].storage_area_id == 1
    assert result[0].code == "GH-001-NORTH"
    mock_area_repo.session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_areas_by_warehouse_with_locations(
    area_service, mock_area_repo, mock_storage_area, sample_area_geojson
):
    """Test getting areas with storage locations."""
    # Arrange
    location_mock = Mock()
    location_mock.storage_location_id = 1
    location_mock.code = "LOC-001"
    location_mock.name = "Location 1"
    location_mock.active = True

    mock_storage_area.storage_locations = [location_mock]

    # Mock session.execute() to return list of areas
    mock_result = Mock()
    mock_result.scalars.return_value.all.return_value = [mock_storage_area]
    mock_area_repo.session.execute.return_value = mock_result

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_area_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6482, -33.4492],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await area_service.get_areas_by_warehouse(1, include_locations=True)

    # Assert
    assert len(result) == 1
    assert len(result[0].storage_locations) == 1
    assert result[0].storage_locations[0].code == "LOC-001"
    mock_area_repo.session.execute.assert_called_once()


# ============================================================================
# calculate_utilization tests
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_utilization_success(area_service, mock_area_repo):
    """Test area utilization calculation."""
    # Arrange
    mock_area = Mock()
    mock_area.storage_area_id = 1
    mock_area.area_m2 = 1000.0  # 1000 m²
    mock_area_repo.get.return_value = mock_area

    # Mock sum query result (500 m² used)
    mock_result = Mock()
    mock_result.scalar.return_value = 500.0
    mock_area_repo.session.execute.return_value = mock_result

    # Act
    result = await area_service.calculate_utilization(1)

    # Assert
    assert result == 50.0  # 500/1000 * 100 = 50%
    mock_area_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_calculate_utilization_area_not_found(area_service, mock_area_repo):
    """Test calculate_utilization raises exception when area not found."""
    # Arrange
    mock_area_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(StorageAreaNotFoundException):
        await area_service.calculate_utilization(999)


# ============================================================================
# update_storage_area tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_storage_area_success(
    area_service, mock_area_repo, mock_warehouse_service, mock_storage_area, sample_area_geojson
):
    """Test successful storage area update (partial update)."""
    # Arrange
    mock_area_repo.get.return_value = mock_storage_area

    updated_area = Mock(spec=StorageArea)
    updated_area.storage_area_id = 1
    updated_area.code = "GH-001-NORTH"
    updated_area.name = "Updated North Wing"
    updated_area.position = Mock()
    updated_area.position.value = "N"
    updated_area.geojson_coordinates = mock_storage_area.geojson_coordinates
    updated_area.centroid = mock_storage_area.centroid
    updated_area.area_m2 = mock_storage_area.area_m2
    updated_area.warehouse_id = 1
    updated_area.active = True
    updated_area.created_at = mock_storage_area.created_at
    updated_area.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_area_repo.update.return_value = updated_area

    request = StorageAreaUpdateRequest(name="Updated North Wing")

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_area_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6482, -33.4492],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await area_service.update_storage_area(1, request)

    # Assert
    assert result.storage_area_id == 1
    assert result.name == "Updated North Wing"
    mock_area_repo.get.assert_called_once_with(1)
    mock_area_repo.update.assert_called_once_with(1, {"name": "Updated North Wing"})


@pytest.mark.asyncio
async def test_update_storage_area_not_found(area_service, mock_area_repo):
    """Test update raises StorageAreaNotFoundException when ID not found."""
    # Arrange
    mock_area_repo.get.return_value = None

    request = StorageAreaUpdateRequest(name="New Name")

    # Act & Assert
    with pytest.raises(StorageAreaNotFoundException) as exc_info:
        await area_service.update_storage_area(999, request)

    assert "999" in str(exc_info.value)
    mock_area_repo.get.assert_called_once_with(999)
    mock_area_repo.update.assert_not_called()


# ============================================================================
# delete_storage_area tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_storage_area_success(area_service, mock_area_repo, mock_storage_area):
    """Test successful soft delete (set active=False)."""
    # Arrange
    mock_area_repo.get.return_value = mock_storage_area
    mock_area_repo.update.return_value = mock_storage_area

    # Act
    result = await area_service.delete_storage_area(1)

    # Assert
    assert result is True
    mock_area_repo.get.assert_called_once_with(1)
    mock_area_repo.update.assert_called_once_with(1, {"active": False})


@pytest.mark.asyncio
async def test_delete_storage_area_not_found(area_service, mock_area_repo):
    """Test delete raises StorageAreaNotFoundException when ID not found."""
    # Arrange
    mock_area_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(StorageAreaNotFoundException) as exc_info:
        await area_service.delete_storage_area(999)

    assert "999" in str(exc_info.value)
    mock_area_repo.get.assert_called_once_with(999)
    mock_area_repo.update.assert_not_called()


# ============================================================================
# _validate_within_parent tests
# ============================================================================


def test_validate_within_parent_valid(area_service, sample_area_geojson, sample_warehouse_geojson):
    """Test geometry validation accepts child within parent."""
    # Act & Assert (should not raise)
    area_service._validate_within_parent(sample_area_geojson, sample_warehouse_geojson)


def test_validate_within_parent_out_of_bounds(area_service, sample_warehouse_geojson):
    """Test geometry validation rejects child extending beyond parent."""
    # Arrange - Area OUTSIDE warehouse
    out_of_bounds_area = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.650, -33.450],
                [-70.649, -33.450],
                [-70.649, -33.451],
                [-70.650, -33.451],
                [-70.650, -33.450],
            ]
        ],
    }

    # Act & Assert
    with pytest.raises(GeometryOutOfBoundsException) as exc_info:
        area_service._validate_within_parent(out_of_bounds_area, sample_warehouse_geojson)

    assert "beyond warehouse boundaries" in str(exc_info.value).lower()
