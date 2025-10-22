"""Unit tests for WarehouseService.

Tests business logic with mocked repository dependencies.
No database access - uses AsyncMock for WarehouseRepository.

TESTING STRATEGY:
- Mock repository methods (get, create, update, etc.)
- Use REAL Shapely for geometry validation (business logic)
- Mock geoalchemy2 functions (from_shape, to_shape) for PostGIS conversion

Coverage target: ≥85%

Test categories:
- create_warehouse: success, duplicate code, invalid geometry
- get_warehouse_by_id: success, not found
- get_warehouse_by_gps: found, not found
- get_active_warehouses: with/without areas
- update_warehouse: success, not found, geometry validation
- delete_warehouse: success, not found
- _validate_geometry: valid polygon, invalid cases

See:
    - Service: app/services/warehouse_service.py
    - Task: backlog/03_kanban/01_ready/S001-warehouse-service.md
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.exceptions import DuplicateCodeException, WarehouseNotFoundException
from app.models.warehouse import Warehouse, WarehouseTypeEnum
from app.schemas.warehouse_schema import (
    WarehouseCreateRequest,
    WarehouseUpdateRequest,
)
from app.services.warehouse_service import WarehouseService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_warehouse_repo():
    """Create mock WarehouseRepository for testing."""
    return AsyncMock()


@pytest.fixture
def warehouse_service(mock_warehouse_repo):
    """Create WarehouseService with mocked repository."""
    return WarehouseService(warehouse_repo=mock_warehouse_repo)


@pytest.fixture
def sample_geojson():
    """Valid GeoJSON polygon for testing."""
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
def mock_warehouse(sample_geojson):
    """Create mock Warehouse model instance.

    The geometries are WKBElement objects that geoalchemy2.shape.to_shape
    will convert to Shapely objects with __geo_interface__.
    """
    warehouse = Mock(spec=Warehouse)
    warehouse.warehouse_id = 1
    warehouse.code = "GH-001"
    warehouse.name = "Main Greenhouse"
    warehouse.warehouse_type = WarehouseTypeEnum.GREENHOUSE
    warehouse.geojson_coordinates = "mocked_wkb_element_polygon"
    warehouse.centroid = "mocked_wkb_element_point"
    warehouse.area_m2 = 10500.50
    warehouse.active = True
    warehouse.created_at = datetime(2025, 10, 20, 14, 30, 0)
    warehouse.updated_at = None

    # Mock storage_areas relationship
    warehouse.storage_areas = []

    return warehouse


# ============================================================================
# create_warehouse tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_warehouse_success(
    warehouse_service, mock_warehouse_repo, sample_geojson, mock_warehouse
):
    """Test successful warehouse creation."""
    # Arrange
    mock_warehouse_repo.get_by_code.return_value = None  # No duplicate
    mock_warehouse_repo.create.return_value = mock_warehouse

    request = WarehouseCreateRequest(
        code="GH-001",
        name="Main Greenhouse",
        warehouse_type=WarehouseTypeEnum.GREENHOUSE,
        geojson_geojson_coordinates=sample_geojson,
    )

    # Act - patch ONLY geoalchemy2 functions (let Shapely validation run)
    with patch("geoalchemy2.shape.from_shape") as mock_from_shape:
        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_from_shape.return_value = "mocked_postgis_geometry"

            # Mock to_shape for response conversion
            polygon_mock = Mock()
            polygon_mock.__geo_interface__ = sample_geojson

            point_mock = Mock()
            point_mock.__geo_interface__ = {
                "type": "Point",
                "coordinates": [-70.6478, -33.4494],
            }

            mock_to_shape.side_effect = [polygon_mock, point_mock]

            result = await warehouse_service.create_warehouse(request)

    # Assert
    assert result.warehouse_id == 1
    assert result.code == "GH-001"
    assert result.name == "Main Greenhouse"
    assert result.warehouse_type == "greenhouse"
    mock_warehouse_repo.get_by_code.assert_called_once_with("GH-001")
    mock_warehouse_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_warehouse_duplicate_code(
    warehouse_service, mock_warehouse_repo, sample_geojson, mock_warehouse
):
    """Test duplicate code rejection."""
    # Arrange
    mock_warehouse_repo.get_by_code.return_value = mock_warehouse  # Duplicate exists

    request = WarehouseCreateRequest(
        code="GH-001",
        name="Another Warehouse",
        warehouse_type=WarehouseTypeEnum.GREENHOUSE,
        geojson_geojson_coordinates=sample_geojson,
    )

    # Act & Assert
    with pytest.raises(DuplicateCodeException) as exc_info:
        await warehouse_service.create_warehouse(request)

    assert "GH-001" in str(exc_info.value)
    mock_warehouse_repo.get_by_code.assert_called_once_with("GH-001")
    mock_warehouse_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_warehouse_invalid_geometry_not_closed(warehouse_service, mock_warehouse_repo):
    """Test geometry validation rejects non-closed polygons."""
    # Arrange
    mock_warehouse_repo.get_by_code.return_value = None

    invalid_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.648300, -33.448900],
                [-70.647300, -33.448900],
                [-70.647300, -33.449900],
                # Missing closing point
            ]
        ],
    }

    request = WarehouseCreateRequest(
        code="GH-002",
        name="Invalid Warehouse",
        warehouse_type=WarehouseTypeEnum.GREENHOUSE,
        geojson_geojson_coordinates=invalid_geojson,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="must be closed"):
        await warehouse_service.create_warehouse(request)

    mock_warehouse_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_warehouse_invalid_geometry_too_few_vertices(
    warehouse_service, mock_warehouse_repo
):
    """Test geometry validation rejects polygons with < 3 vertices."""
    # Arrange
    mock_warehouse_repo.get_by_code.return_value = None

    invalid_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.648300, -33.448900],
                [-70.647300, -33.448900],
                [-70.648300, -33.448900],  # Only 2 unique vertices
            ]
        ],
    }

    request = WarehouseCreateRequest(
        code="GH-003",
        name="Invalid Warehouse",
        warehouse_type=WarehouseTypeEnum.GREENHOUSE,
        geojson_geojson_coordinates=invalid_geojson,
    )

    # Act & Assert
    with pytest.raises(ValueError, match="at least 3 vertices"):
        await warehouse_service.create_warehouse(request)

    mock_warehouse_repo.create.assert_not_called()


# ============================================================================
# get_warehouse_by_id tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_warehouse_by_id_success(
    warehouse_service, mock_warehouse_repo, mock_warehouse, sample_geojson
):
    """Test successful warehouse retrieval by ID."""
    # Arrange
    mock_warehouse_repo.get.return_value = mock_warehouse

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        # Mock to_shape to return objects with __geo_interface__
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6478, -33.4494],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await warehouse_service.get_warehouse_by_id(1)

    # Assert
    assert result.warehouse_id == 1
    assert result.code == "GH-001"
    mock_warehouse_repo.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_warehouse_by_id_not_found(warehouse_service, mock_warehouse_repo):
    """Test WarehouseNotFoundException when ID not found."""
    # Arrange
    mock_warehouse_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(WarehouseNotFoundException) as exc_info:
        await warehouse_service.get_warehouse_by_id(999)

    assert "999" in str(exc_info.value)
    mock_warehouse_repo.get.assert_called_once_with(999)


# ============================================================================
# get_warehouse_by_gps tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_warehouse_by_gps_found(
    warehouse_service, mock_warehouse_repo, mock_warehouse, sample_geojson
):
    """Test GPS-based warehouse lookup (point inside polygon)."""
    # Arrange
    mock_warehouse_repo.get_by_gps_point.return_value = mock_warehouse

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6478, -33.4494],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await warehouse_service.get_warehouse_by_gps(-70.648, -33.449)

    # Assert
    assert result is not None
    assert result.warehouse_id == 1
    assert result.code == "GH-001"
    mock_warehouse_repo.get_by_gps_point.assert_called_once_with(-70.648, -33.449)


@pytest.mark.asyncio
async def test_get_warehouse_by_gps_not_found(warehouse_service, mock_warehouse_repo):
    """Test GPS lookup returns None when point outside all polygons."""
    # Arrange
    mock_warehouse_repo.get_by_gps_point.return_value = None

    # Act
    result = await warehouse_service.get_warehouse_by_gps(-75.0, -35.0)

    # Assert
    assert result is None
    mock_warehouse_repo.get_by_gps_point.assert_called_once_with(-75.0, -35.0)


# ============================================================================
# get_active_warehouses tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_active_warehouses_without_areas(
    warehouse_service, mock_warehouse_repo, mock_warehouse, sample_geojson
):
    """Test getting active warehouses without storage areas."""
    # Arrange
    mock_warehouses = [mock_warehouse]
    mock_warehouse_repo.get_active_warehouses.return_value = mock_warehouses

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6478, -33.4494],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await warehouse_service.get_active_warehouses(include_areas=False)

    # Assert
    assert len(result) == 1
    assert result[0].warehouse_id == 1
    assert result[0].code == "GH-001"
    mock_warehouse_repo.get_active_warehouses.assert_called_once_with(with_areas=False)


@pytest.mark.asyncio
async def test_get_active_warehouses_with_areas(
    warehouse_service, mock_warehouse_repo, mock_warehouse, sample_geojson
):
    """Test getting active warehouses with storage areas."""
    # Arrange
    # Mock storage area
    area_mock = Mock()
    area_mock.storage_area_id = 1
    area_mock.code = "AREA-A"
    area_mock.name = "Area A"
    area_mock.area_type = "production"
    area_mock.active = True

    mock_warehouse.storage_areas = [area_mock]
    mock_warehouse_repo.get_active_warehouses.return_value = [mock_warehouse]

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6478, -33.4494],
        }

        # Called for warehouse geometry + each storage area geometry (if they have geojson_coordinates)
        # For now, we'll assume storage areas don't have geometry
        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await warehouse_service.get_active_warehouses(include_areas=True)

    # Assert
    assert len(result) == 1
    assert result[0].warehouse_id == 1
    assert len(result[0].storage_areas) == 1
    assert result[0].storage_areas[0].code == "AREA-A"
    mock_warehouse_repo.get_active_warehouses.assert_called_once_with(with_areas=True)


# ============================================================================
# update_warehouse tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_warehouse_success(
    warehouse_service, mock_warehouse_repo, mock_warehouse, sample_geojson
):
    """Test successful warehouse update (partial update)."""
    # Arrange
    mock_warehouse_repo.get.return_value = mock_warehouse

    updated_warehouse = Mock(spec=Warehouse)
    updated_warehouse.warehouse_id = 1
    updated_warehouse.code = "GH-001"
    updated_warehouse.name = "Updated Greenhouse"
    updated_warehouse.warehouse_type = WarehouseTypeEnum.GREENHOUSE
    updated_warehouse.geojson_coordinates = mock_warehouse.geojson_coordinates
    updated_warehouse.centroid = mock_warehouse.centroid
    updated_warehouse.area_m2 = mock_warehouse.area_m2
    updated_warehouse.active = True
    updated_warehouse.created_at = mock_warehouse.created_at
    updated_warehouse.updated_at = datetime(2025, 10, 20, 15, 0, 0)

    mock_warehouse_repo.update.return_value = updated_warehouse

    request = WarehouseUpdateRequest(name="Updated Greenhouse")

    # Act
    with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
        polygon_mock = Mock()
        polygon_mock.__geo_interface__ = sample_geojson

        point_mock = Mock()
        point_mock.__geo_interface__ = {
            "type": "Point",
            "coordinates": [-70.6478, -33.4494],
        }

        mock_to_shape.side_effect = [polygon_mock, point_mock]

        result = await warehouse_service.update_warehouse(1, request)

    # Assert
    assert result.warehouse_id == 1
    assert result.name == "Updated Greenhouse"
    mock_warehouse_repo.get.assert_called_once_with(1)
    mock_warehouse_repo.update.assert_called_once_with(1, {"name": "Updated Greenhouse"})


@pytest.mark.asyncio
async def test_update_warehouse_not_found(warehouse_service, mock_warehouse_repo):
    """Test update raises WarehouseNotFoundException when ID not found."""
    # Arrange
    mock_warehouse_repo.get.return_value = None

    request = WarehouseUpdateRequest(name="New Name")

    # Act & Assert
    with pytest.raises(WarehouseNotFoundException) as exc_info:
        await warehouse_service.update_warehouse(999, request)

    assert "999" in str(exc_info.value)
    mock_warehouse_repo.get.assert_called_once_with(999)
    mock_warehouse_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_update_warehouse_with_geometry(
    warehouse_service, mock_warehouse_repo, mock_warehouse, sample_geojson
):
    """Test warehouse update with geometry change."""
    # Arrange
    mock_warehouse_repo.get.return_value = mock_warehouse
    mock_warehouse_repo.update.return_value = mock_warehouse

    request = WarehouseUpdateRequest(geojson_geojson_coordinates=sample_geojson)

    # Act
    with patch("geoalchemy2.shape.from_shape") as mock_from_shape:
        with patch("geoalchemy2.shape.to_shape") as mock_to_shape:
            mock_from_shape.return_value = "mocked_postgis_geometry"

            polygon_mock = Mock()
            polygon_mock.__geo_interface__ = sample_geojson

            point_mock = Mock()
            point_mock.__geo_interface__ = {
                "type": "Point",
                "coordinates": [-70.6478, -33.4494],
            }

            mock_to_shape.side_effect = [polygon_mock, point_mock]

            result = await warehouse_service.update_warehouse(1, request)

    # Assert
    assert result.warehouse_id == 1
    mock_warehouse_repo.get.assert_called_once_with(1)
    mock_warehouse_repo.update.assert_called_once()


# ============================================================================
# delete_warehouse tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_warehouse_success(warehouse_service, mock_warehouse_repo, mock_warehouse):
    """Test successful soft delete (set active=False)."""
    # Arrange
    mock_warehouse_repo.get.return_value = mock_warehouse
    mock_warehouse_repo.update.return_value = mock_warehouse

    # Act
    result = await warehouse_service.delete_warehouse(1)

    # Assert
    assert result is True
    mock_warehouse_repo.get.assert_called_once_with(1)
    mock_warehouse_repo.update.assert_called_once_with(1, {"active": False})


@pytest.mark.asyncio
async def test_delete_warehouse_not_found(warehouse_service, mock_warehouse_repo):
    """Test delete raises WarehouseNotFoundException when ID not found."""
    # Arrange
    mock_warehouse_repo.get.return_value = None

    # Act & Assert
    with pytest.raises(WarehouseNotFoundException) as exc_info:
        await warehouse_service.delete_warehouse(999)

    assert "999" in str(exc_info.value)
    mock_warehouse_repo.get.assert_called_once_with(999)
    mock_warehouse_repo.update.assert_not_called()


# ============================================================================
# _validate_geometry tests
# ============================================================================


def test_validate_geometry_valid_polygon(warehouse_service, sample_geojson):
    """Test geometry validation accepts valid polygon."""
    # Act & Assert (should not raise)
    warehouse_service._validate_geometry(sample_geojson)


def test_validate_geometry_invalid_type(warehouse_service):
    """Test geometry validation rejects non-Polygon types."""
    # Arrange
    invalid_geojson = {
        "type": "Point",
        "coordinates": [-70.648, -33.449],
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Expected Polygon"):
        warehouse_service._validate_geometry(invalid_geojson)


def test_validate_geometry_self_intersecting(warehouse_service):
    """Test geometry validation rejects self-intersecting polygons."""
    # Arrange (bow-tie polygon)
    invalid_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [0, 0],
                [2, 2],
                [2, 0],
                [0, 2],
                [0, 0],  # Self-intersecting
            ]
        ],
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid polygon"):
        warehouse_service._validate_geometry(invalid_geojson)


def test_validate_geometry_not_closed(warehouse_service):
    """Test geometry validation rejects non-closed polygons."""
    # Arrange
    invalid_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.648, -33.449],
                [-70.647, -33.449],
                [-70.647, -33.450],
                # Missing closing point
            ]
        ],
    }

    # Act & Assert
    with pytest.raises(ValueError, match="must be closed"):
        warehouse_service._validate_geometry(invalid_geojson)


def test_validate_geometry_too_few_vertices(warehouse_service):
    """Test geometry validation rejects polygons with < 3 vertices."""
    # Arrange
    invalid_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [-70.648, -33.449],
                [-70.647, -33.449],
                [-70.648, -33.449],  # Only 2 unique vertices
            ]
        ],
    }

    # Act & Assert
    with pytest.raises(ValueError, match="at least 3 vertices"):
        warehouse_service._validate_geometry(invalid_geojson)
