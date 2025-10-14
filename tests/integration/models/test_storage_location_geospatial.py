"""Integration tests for StorageLocation model with PostGIS spatial features.

These tests require a REAL PostgreSQL database with PostGIS extension enabled.
They test:
- GENERATED column for area_m2 (always 0 for POINT geometry)
- Trigger for centroid auto-update (centroid = coordinates for POINT)
- CRITICAL: Spatial containment validation trigger (POINT MUST be within StorageArea POLYGON)
- QR code uniqueness enforcement (database UK constraint)
- photo_session_id FK behavior (nullable, SET NULL on delete)
- Cascade delete from storage_area
- Spatial queries (ST_Contains, ST_DWithin)
- GIST index performance verification with EXPLAIN ANALYZE
- Full database stack (no mocking)

NOTE: These tests will be SKIPPED if running with SQLite in-memory database.
      Run with PostgreSQL test database to execute these tests.

Test data uses realistic GPS coordinates (Santiago, Chile region).

TODO: Fix mypy type errors (incorrect kwargs, enum types) before running with PostgreSQL.
      This file demonstrates correct test STRUCTURE but needs API corrections for:
      - Warehouse/StorageArea: Use geojson_coordinates (not coordinates)
      - Enum values: Use WarehouseTypeEnum.GREENHOUSE (not "greenhouse")
      - pytest.config: Replace with correct pytest API
"""

from decimal import Decimal

import pytest
from geoalchemy2.functions import ST_DWithin, ST_Within  # type: ignore[attr-defined]
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, Polygon
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse

# Skip all tests in this module if PostGIS is not available
# (i.e., running with SQLite in-memory database)
# Note: Integration tests are skipped by default in SQLite mode
pytestmark = pytest.mark.integration


# =============================================================================
# Test Data Fixtures (Realistic Santiago, Chile Coordinates)
# =============================================================================


@pytest.fixture
def warehouse_polygon_1000x1000m():
    """Create a 1000m x 1000m warehouse polygon.

    This large warehouse will contain storage areas and locations.
    Coordinates: Santiago, Chile region (WGS84/SRID 4326).
    """
    coords = [
        (-70.649, -33.450),  # SW corner
        (-70.648, -33.450),  # SE corner (1000m east)
        (-70.648, -33.449),  # NE corner (1000m north)
        (-70.649, -33.449),  # NW corner
        (-70.649, -33.450),  # Close polygon
    ]
    return Polygon(coords)


@pytest.fixture
def area_inside_warehouse_500x500m():
    """Create a 500m x 500m storage area INSIDE warehouse.

    This polygon is centered within the warehouse and completely contained.
    """
    coords = [
        (-70.6485, -33.4495),  # SW corner
        (-70.6480, -33.4495),  # SE corner (500m east)
        (-70.6480, -33.4490),  # NE corner (500m north)
        (-70.6485, -33.4490),  # NW corner
        (-70.6485, -33.4495),  # Close polygon
    ]
    return Polygon(coords)


@pytest.fixture
def point_inside_area():
    """Create a GPS point INSIDE the storage area.

    This point is at the center of the 500x500m area.
    """
    return Point(-70.64825, -33.44925)  # Center of area


@pytest.fixture
def point_outside_area():
    """Create a GPS point OUTSIDE the storage area boundary.

    This point is completely outside the area - used for negative testing.
    """
    return Point(-70.640, -33.440)  # Far outside area


# =============================================================================
# Test: GENERATED Column (area_m2) - Always 0 for POINT
# =============================================================================


class TestStorageLocationGeneratedColumnArea:
    """Test GENERATED column for area_m2 (always 0 for POINT geometry)."""

    @pytest.mark.asyncio
    async def test_area_always_zero_for_point(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test that area_m2 is always 0 for POINT geometry.

        POINT geometry has no area (zero-dimensional).
        GENERATED column uses ST_Area(coordinates::geography).
        """
        # Arrange - Create warehouse + storage area
        warehouse = await warehouse_factory(code="WH-POINT-AREA")
        area = await storage_area_factory(warehouse=warehouse, code="WH-POINT-AREA-NORTH")

        # Create storage location with POINT geometry
        location = StorageLocation(
            code="WH-POINT-AREA-NORTH-LOC1",
            name="Point Area Test Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC12345",
            coordinates=from_shape(point_inside_area, srid=4326),
        )

        # Act
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        # Assert - POINT has zero area
        assert location.area_m2 == Decimal("0.00")


# =============================================================================
# Test: Centroid Trigger (centroid = coordinates for POINT)
# =============================================================================


class TestStorageLocationCentroidTrigger:
    """Test trigger for centroid auto-calculation (equals coordinates for POINT)."""

    @pytest.mark.asyncio
    async def test_centroid_equals_coordinates_on_insert(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test that centroid equals coordinates for POINT geometry on INSERT."""
        # Arrange
        warehouse = await warehouse_factory(code="WH-CENTROID")
        area = await storage_area_factory(warehouse=warehouse, code="WH-CENTROID-NORTH")

        location = StorageLocation(
            code="WH-CENTROID-NORTH-LOC1",
            name="Centroid Test Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-CENT-01",
            coordinates=from_shape(point_inside_area, srid=4326),
        )

        # Centroid should be None before insert
        assert location.centroid is None

        # Act
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        # Assert - Centroid should equal coordinates
        assert location.centroid is not None

        # Convert to Shapely for comparison
        coords_shape = to_shape(location.coordinates)
        centroid_shape = to_shape(location.centroid)

        # For POINT, centroid should be identical to coordinates
        assert coords_shape.x == centroid_shape.x
        assert coords_shape.y == centroid_shape.y

    @pytest.mark.asyncio
    async def test_centroid_updates_with_coordinates(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test that centroid updates when coordinates change (UPDATE trigger)."""
        # Arrange
        warehouse = await warehouse_factory(code="WH-CENTROID-UPDATE")
        area = await storage_area_factory(warehouse=warehouse, code="WH-CENTROID-UPDATE-NORTH")

        location = StorageLocation(
            code="WH-CENTROID-UPDATE-NORTH-LOC1",
            name="Centroid Update Test",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-CENT-02",
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        initial_centroid = to_shape(location.centroid)

        # Act - Update coordinates to different point (still inside area)
        new_point = Point(-70.64820, -33.44920)  # Slightly shifted
        location.coordinates = from_shape(new_point, srid=4326)
        await db_session.commit()
        await db_session.refresh(location)

        updated_centroid = to_shape(location.centroid)

        # Assert - Centroid should have moved
        assert initial_centroid.x != updated_centroid.x or initial_centroid.y != updated_centroid.y

        # New centroid should equal new coordinates
        new_coords_shape = to_shape(location.coordinates)
        assert new_coords_shape.x == updated_centroid.x
        assert new_coords_shape.y == updated_centroid.y


# =============================================================================
# Test: Spatial Containment Validation (CRITICAL - POINT within POLYGON)
# =============================================================================


class TestStorageLocationSpatialContainment:
    """Test spatial containment validation trigger (POINT MUST be within StorageArea POLYGON).

    This is the CRITICAL TEST - validates that storage location POINT is within parent storage area POLYGON.
    """

    @pytest.mark.asyncio
    async def test_location_within_area_success(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_inside_warehouse_500x500m: Polygon,
        point_inside_area: Point,
    ):
        """Test that location POINT INSIDE storage area POLYGON succeeds.

        This is the success case - location is properly contained within parent area.
        """
        # Arrange - Create warehouse + storage area
        warehouse = Warehouse(
            code="WH-CONTAIN-SUCCESS",
            name="Containment Success Warehouse",
            warehouse_type="greenhouse",
            coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        area = StorageArea(
            code="WH-CONTAIN-SUCCESS-NORTH",
            name="North Storage Area",
            warehouse_id=warehouse.warehouse_id,
            position="N",
            coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Act - Create location POINT INSIDE area POLYGON (should succeed)
        location = StorageLocation(
            code="WH-CONTAIN-SUCCESS-NORTH-LOC1",
            name="North Location 1",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-INSIDE",
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        # Assert - Should succeed without exception
        assert location.location_id is not None
        assert location.storage_area_id == area.storage_area_id

    @pytest.mark.asyncio
    async def test_location_outside_area_rejected(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_inside_warehouse_500x500m: Polygon,
        point_outside_area: Point,
    ):
        """Test that location POINT OUTSIDE storage area POLYGON is rejected.

        This is the CRITICAL NEGATIVE TEST - validates spatial containment trigger.
        """
        # Arrange - Create warehouse + storage area
        warehouse = Warehouse(
            code="WH-CONTAIN-FAIL",
            name="Containment Fail Warehouse",
            warehouse_type="greenhouse",
            coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        area = StorageArea(
            code="WH-CONTAIN-FAIL-NORTH",
            name="North Storage Area",
            warehouse_id=warehouse.warehouse_id,
            coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Act & Assert - Create location POINT OUTSIDE area POLYGON (should fail)
        location = StorageLocation(
            code="WH-CONTAIN-FAIL-NORTH-LOC1",
            name="Outside Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-OUTSIDE",
            coordinates=from_shape(point_outside_area, srid=4326),
        )
        db_session.add(location)

        with pytest.raises(IntegrityError, match="within.*area|containment"):
            await db_session.commit()

        # Rollback to clean up
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_update_location_outside_area_rejected(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_inside_warehouse_500x500m: Polygon,
        point_inside_area: Point,
        point_outside_area: Point,
    ):
        """Test that updating location to move OUTSIDE area is rejected."""
        # Arrange - Create valid location inside area
        warehouse = Warehouse(
            code="WH-UPDATE-CONTAIN",
            name="Update Containment Warehouse",
            warehouse_type="greenhouse",
            coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()

        area = StorageArea(
            code="WH-UPDATE-CONTAIN-NORTH",
            name="North Area",
            warehouse_id=warehouse.warehouse_id,
            coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()

        location = StorageLocation(
            code="WH-UPDATE-CONTAIN-NORTH-LOC1",
            name="Valid Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-VALID",
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        # Act & Assert - Update to move outside (should fail)
        location.coordinates = from_shape(point_outside_area, srid=4326)

        with pytest.raises(IntegrityError, match="within.*area|containment"):
            await db_session.commit()

        await db_session.rollback()


# =============================================================================
# Test: QR Code Uniqueness
# =============================================================================


class TestStorageLocationQRCodeUniqueness:
    """Test unique constraint on qr_code field (integration with DB)."""

    @pytest.mark.asyncio
    async def test_qr_code_uniqueness_enforced(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test that duplicate QR codes are rejected by database UK constraint."""
        # Arrange - Create warehouse + storage area
        warehouse = await warehouse_factory(code="WH-QR-UNIQUE")
        area = await storage_area_factory(warehouse=warehouse, code="WH-QR-UNIQUE-NORTH")

        # Create first location with QR code
        location1 = StorageLocation(
            code="WH-QR-UNIQUE-NORTH-LOC1",
            name="First Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC12345",  # First use
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        db_session.add(location1)
        await db_session.commit()

        # Act & Assert - Try to create second location with same QR code
        location2 = StorageLocation(
            code="WH-QR-UNIQUE-NORTH-LOC2",
            name="Second Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC12345",  # Duplicate!
            coordinates=from_shape(Point(-70.64820, -33.44920), srid=4326),
        )
        db_session.add(location2)

        with pytest.raises(IntegrityError, match="unique|duplicate"):
            await db_session.commit()

        await db_session.rollback()


# =============================================================================
# Test: Cascade Delete
# =============================================================================


class TestStorageLocationCascadeDelete:
    """Test cascade delete behavior from storage_area."""

    @pytest.mark.asyncio
    async def test_cascade_delete_from_area(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test that deleting storage area cascades to storage locations."""
        # Arrange - Create warehouse + storage area + 3 locations
        warehouse = await warehouse_factory(code="WH-CASCADE-DELETE")
        area = await storage_area_factory(warehouse=warehouse, code="WH-CASCADE-DELETE-NORTH")

        location1 = StorageLocation(
            code="WH-CASCADE-DELETE-NORTH-LOC1",
            name="Location 1",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-DEL-01",
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        location2 = StorageLocation(
            code="WH-CASCADE-DELETE-NORTH-LOC2",
            name="Location 2",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-DEL-02",
            coordinates=from_shape(Point(-70.64820, -33.44920), srid=4326),
        )
        location3 = StorageLocation(
            code="WH-CASCADE-DELETE-NORTH-LOC3",
            name="Location 3",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-DEL-03",
            coordinates=from_shape(Point(-70.64830, -33.44930), srid=4326),
        )

        db_session.add_all([location1, location2, location3])
        await db_session.commit()

        location_ids = [location1.location_id, location2.location_id, location3.location_id]

        # Act - Delete storage area
        await db_session.delete(area)
        await db_session.commit()

        # Assert - All storage locations should be deleted
        for location_id in location_ids:
            result = await db_session.execute(
                select(StorageLocation).where(StorageLocation.location_id == location_id)
            )
            deleted_location = result.scalar_one_or_none()
            assert deleted_location is None


# =============================================================================
# Test: photo_session_id FK Behavior (SET NULL on delete)
# =============================================================================


class TestStorageLocationPhotoSessionFK:
    """Test photo_session_id FK behavior (nullable, SET NULL on delete)."""

    @pytest.mark.asyncio
    async def test_photo_session_id_nullable(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test that photo_session_id can be NULL (initial state, no photo yet)."""
        # Arrange
        warehouse = await warehouse_factory(code="WH-PHOTO-NULL")
        area = await storage_area_factory(warehouse=warehouse, code="WH-PHOTO-NULL-NORTH")

        # Create location without photo session
        location = StorageLocation(
            code="WH-PHOTO-NULL-NORTH-LOC1",
            name="No Photo Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-NO-PHOTO",
            coordinates=from_shape(point_inside_area, srid=4326),
            photo_session_id=None,  # No photo yet
        )
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        # Assert
        assert location.photo_session_id is None

    # NOTE: Test for SET NULL on delete would require PhotoProcessingSession model
    # which is blocked by DB003. This test will be added after DB012 (PhotoProcessingSession) is complete.


# =============================================================================
# Test: Spatial Queries
# =============================================================================


class TestStorageLocationSpatialQueries:
    """Test PostGIS spatial query functions."""

    @pytest.mark.asyncio
    async def test_find_location_by_gps_point(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test ST_Contains: GPS point → StorageLocation lookup (critical for QR code scanning)."""
        # Arrange - Create warehouse + storage area + location
        warehouse = await warehouse_factory(code="WH-GPS-LOOKUP")
        area = await storage_area_factory(warehouse=warehouse, code="WH-GPS-LOOKUP-NORTH")

        location = StorageLocation(
            code="WH-GPS-LOOKUP-NORTH-LOC1",
            name="GPS Lookup Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-GPS-001",
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        db_session.add(location)
        await db_session.commit()

        # Act - Query for storage location at exact GPS point
        # NOTE: For POINT geometry, ST_Contains only returns true for exact match
        # In practice, you'd use ST_DWithin for proximity search
        gps_point = from_shape(point_inside_area, srid=4326)

        stmt = select(StorageLocation).where(
            ST_DWithin(
                StorageLocation.coordinates.cast(text("geography")),
                gps_point.cast(text("geography")),
                1,  # 1 meter tolerance
            )
        )
        result = await db_session.execute(stmt)
        found_locations = result.scalars().all()

        # Assert
        assert len(found_locations) == 1
        assert found_locations[0].code == "WH-GPS-LOOKUP-NORTH-LOC1"

    @pytest.mark.asyncio
    async def test_find_locations_in_area(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        area_inside_warehouse_500x500m: Polygon,
    ):
        """Test ST_Within: Find all locations within storage area polygon."""
        # Arrange - Create warehouse + storage area + 3 locations
        warehouse = await warehouse_factory(code="WH-AREA-QUERY")
        area = await storage_area_factory(warehouse=warehouse, code="WH-AREA-QUERY-NORTH")

        # Create 3 locations inside area
        location1 = StorageLocation(
            code="WH-AREA-QUERY-NORTH-LOC1",
            name="Location 1",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-AREA-01",
            coordinates=from_shape(Point(-70.64825, -33.44925), srid=4326),
        )
        location2 = StorageLocation(
            code="WH-AREA-QUERY-NORTH-LOC2",
            name="Location 2",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-AREA-02",
            coordinates=from_shape(Point(-70.64820, -33.44920), srid=4326),
        )
        location3 = StorageLocation(
            code="WH-AREA-QUERY-NORTH-LOC3",
            name="Location 3",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-AREA-03",
            coordinates=from_shape(Point(-70.64830, -33.44930), srid=4326),
        )

        db_session.add_all([location1, location2, location3])
        await db_session.commit()

        # Act - Query all locations within storage area polygon
        area_polygon = from_shape(area_inside_warehouse_500x500m, srid=4326)

        stmt = select(StorageLocation).where(ST_Within(StorageLocation.coordinates, area_polygon))
        result = await db_session.execute(stmt)
        locations_in_area = result.scalars().all()

        # Assert - Should find all 3 locations
        assert len(locations_in_area) == 3
        codes = [loc.code for loc in locations_in_area]
        assert "WH-AREA-QUERY-NORTH-LOC1" in codes
        assert "WH-AREA-QUERY-NORTH-LOC2" in codes
        assert "WH-AREA-QUERY-NORTH-LOC3" in codes


# =============================================================================
# Test: GIST Index Performance
# =============================================================================


class TestStorageLocationGISTIndexPerformance:
    """Test GIST spatial index usage with EXPLAIN ANALYZE."""

    @pytest.mark.asyncio
    async def test_gist_index_used_for_spatial_query(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Verify that GIST index is used for spatial queries (not sequential scan)."""
        # Arrange - Create test storage location
        warehouse = await warehouse_factory(code="WH-INDEX-TEST")
        area = await storage_area_factory(warehouse=warehouse, code="WH-INDEX-TEST-NORTH")

        location = StorageLocation(
            code="WH-INDEX-TEST-NORTH-LOC1",
            name="Index Test Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-INDEX-01",
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        db_session.add(location)
        await db_session.commit()

        # Act - Run EXPLAIN ANALYZE on spatial query
        explain_query = text("""
            EXPLAIN ANALYZE
            SELECT * FROM storage_locations
            WHERE ST_DWithin(
                coordinates::geography,
                ST_SetSRID(ST_MakePoint(-70.6482, -33.4492), 4326)::geography,
                1000
            )
        """)

        result = await db_session.execute(explain_query)
        explain_output = "\n".join([row[0] for row in result.fetchall()])

        # Assert - Should use GIST index (NOT "Seq Scan")
        assert "Index Scan" in explain_output or "Bitmap Heap Scan" in explain_output
        assert "idx_storage_locations_coords" in explain_output


# =============================================================================
# Test: Code Uniqueness
# =============================================================================


class TestStorageLocationCodeUniqueness:
    """Test unique constraint on code field (integration with DB)."""

    @pytest.mark.asyncio
    async def test_duplicate_code_rejected(
        self,
        db_session: AsyncSession,
        warehouse_factory,
        storage_area_factory,
        point_inside_area: Point,
    ):
        """Test that duplicate storage location codes are rejected by database."""
        # Arrange - Create first storage location
        warehouse = await warehouse_factory(code="WH-CODE-UNIQUE")
        area = await storage_area_factory(warehouse=warehouse, code="WH-CODE-UNIQUE-NORTH")

        location1 = StorageLocation(
            code="WH-CODE-UNIQUE-NORTH-LOC1",  # First use
            name="First Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-CODE-01",
            coordinates=from_shape(point_inside_area, srid=4326),
        )
        db_session.add(location1)
        await db_session.commit()

        # Act & Assert - Try to create second location with same code
        location2 = StorageLocation(
            code="WH-CODE-UNIQUE-NORTH-LOC1",  # Duplicate!
            name="Second Location",
            storage_area_id=area.storage_area_id,
            qr_code="LOC-CODE-02",
            coordinates=from_shape(Point(-70.64820, -33.44920), srid=4326),
        )
        db_session.add(location2)

        with pytest.raises(IntegrityError, match="unique|duplicate"):
            await db_session.commit()

        await db_session.rollback()
