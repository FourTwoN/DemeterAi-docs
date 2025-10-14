"""Integration tests for StorageArea model with PostGIS spatial features.

These tests require a REAL PostgreSQL database with PostGIS extension enabled.
They test:
- GENERATED column for area_m2 auto-calculation
- Trigger for centroid auto-update (INSERT + UPDATE)
- Spatial containment validation trigger (area MUST be within warehouse)
- Self-referential relationships (parent/child areas)
- Cascade delete from warehouse and parent areas
- Spatial queries (ST_DWithin, ST_Distance, ST_Contains)
- GIST index performance verification with EXPLAIN ANALYZE
- Full database stack (no mocking)

NOTE: These tests will be SKIPPED if running with SQLite in-memory database.
      Run with PostgreSQL test database to execute these tests.

Test data uses realistic GPS coordinates (Santiago, Chile region).
"""

from decimal import Decimal

import pytest
from geoalchemy2.functions import ST_Area, ST_Contains, ST_DWithin
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, Polygon
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_area import StorageArea
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

    This large warehouse will contain multiple storage areas.
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
def area_outside_warehouse():
    """Create a storage area polygon OUTSIDE warehouse boundary.

    This polygon is completely outside the warehouse - used for negative testing.
    """
    coords = [
        (-70.650, -33.451),  # Completely outside warehouse
        (-70.649, -33.451),
        (-70.649, -33.450),
        (-70.650, -33.450),
        (-70.650, -33.451),
    ]
    return Polygon(coords)


@pytest.fixture
def area_partially_outside_warehouse():
    """Create a storage area that overlaps but extends beyond warehouse boundary.

    Used to test that partial containment is rejected.
    """
    coords = [
        (-70.6485, -33.4505),  # Overlaps but extends north
        (-70.6475, -33.4505),
        (-70.6475, -33.4485),  # Extends outside
        (-70.6485, -33.4485),
        (-70.6485, -33.4505),
    ]
    return Polygon(coords)


# =============================================================================
# Test: GENERATED Column (area_m2)
# =============================================================================


class TestStorageAreaGeneratedColumnArea:
    """Test GENERATED column for area_m2 auto-calculation from geometry."""

    @pytest.mark.asyncio
    async def test_area_auto_calculated_on_insert(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test that area_m2 is auto-calculated from geometry on INSERT.

        The area should be approximately 2500 m² (500m x 500m).
        GENERATED column uses ST_Area(geojson_coordinates::geography).
        """
        # Arrange - Create warehouse first
        warehouse = await warehouse_factory(code="WH-AREA-TEST")

        # Create storage area inside warehouse
        area = StorageArea(
            code="WH-AREA-TEST-NORTH",
            name="Area Calculation Test",
            warehouse_id=warehouse.warehouse_id,
            position="N",
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )

        # Act
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Assert
        assert area.area_m2 is not None
        assert area.area_m2 > 0

        # Area should be approximately 2500 m² (allowing 15% tolerance for spherical geometry)
        expected_area = Decimal("2500.00")
        tolerance = expected_area * Decimal("0.15")  # 15% tolerance
        assert abs(area.area_m2 - expected_area) < tolerance

    @pytest.mark.asyncio
    async def test_area_updates_when_geometry_changes(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test that area_m2 recalculates when geometry is updated."""
        # Arrange - Create warehouse and initial storage area
        warehouse = await warehouse_factory(code="WH-UPDATE-TEST")

        area = StorageArea(
            code="WH-UPDATE-TEST-NORTH",
            name="Area Update Test",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        initial_area = area.area_m2

        # Act - Update geometry to smaller polygon (250m x 250m)
        smaller_polygon = Polygon(
            [
                (-70.6485, -33.4495),
                (-70.6482, -33.4495),
                (-70.6482, -33.4492),
                (-70.6485, -33.4492),
                (-70.6485, -33.4495),
            ]
        )
        area.geojson_coordinates = from_shape(smaller_polygon, srid=4326)
        await db_session.commit()
        await db_session.refresh(area)

        # Assert - Area should have decreased
        assert area.area_m2 < initial_area

    @pytest.mark.asyncio
    async def test_area_calculation_uses_geography_cast(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Verify area calculation uses geography cast for accurate spherical measurements."""
        # Arrange
        warehouse = await warehouse_factory(code="WH-GEOGRAPHY")

        area = StorageArea(
            code="WH-GEOGRAPHY-CENTER",
            name="Geography Cast Test",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Act - Manual calculation using geography cast
        result = await db_session.execute(
            select(ST_Area(StorageArea.geojson_coordinates.cast(text("geography")))).where(
                StorageArea.storage_area_id == area.storage_area_id
            )
        )
        manual_area = result.scalar_one()

        # Assert - GENERATED column should match manual calculation
        assert abs(float(area.area_m2) - manual_area) < 0.01  # Within 1 cm²


# =============================================================================
# Test: Centroid Trigger
# =============================================================================


class TestStorageAreaCentroidTrigger:
    """Test trigger for centroid auto-calculation (BEFORE INSERT OR UPDATE)."""

    @pytest.mark.asyncio
    async def test_centroid_auto_set_on_insert(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test that centroid is auto-calculated by trigger on INSERT."""
        # Arrange
        warehouse = await warehouse_factory(code="WH-CENTROID")

        area = StorageArea(
            code="WH-CENTROID-NORTH",
            name="Centroid Test Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )

        # Centroid should be None before insert
        assert area.centroid is None

        # Act
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Assert - Centroid should be auto-populated by trigger
        assert area.centroid is not None

    @pytest.mark.asyncio
    async def test_centroid_within_polygon(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test that calculated centroid is actually inside the polygon."""
        # Arrange
        warehouse = await warehouse_factory(code="WH-CENTROID-INSIDE")

        area = StorageArea(
            code="WH-CENTROID-INSIDE-SOUTH",
            name="Centroid Inside Test",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Act - Convert geometries to Shapely for containment check
        polygon_shape = to_shape(area.geojson_coordinates)
        centroid_shape = to_shape(area.centroid)

        # Assert - Centroid should be contained within polygon
        assert polygon_shape.contains(centroid_shape)

    @pytest.mark.asyncio
    async def test_centroid_updates_on_geometry_change(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test that centroid is recalculated when geometry changes (UPDATE trigger)."""
        # Arrange
        warehouse = await warehouse_factory(code="WH-CENTROID-UPDATE")

        area = StorageArea(
            code="WH-CENTROID-UPDATE-EAST",
            name="Centroid Update Test",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        initial_centroid = to_shape(area.centroid)

        # Act - Update geometry to different location
        shifted_polygon = Polygon(
            [
                (-70.6480, -33.4495),  # Shifted east
                (-70.6475, -33.4495),
                (-70.6475, -33.4490),
                (-70.6480, -33.4490),
                (-70.6480, -33.4495),
            ]
        )
        area.geojson_coordinates = from_shape(shifted_polygon, srid=4326)
        await db_session.commit()
        await db_session.refresh(area)

        updated_centroid = to_shape(area.centroid)

        # Assert - Centroid should have moved
        assert initial_centroid.x != updated_centroid.x or initial_centroid.y != updated_centroid.y


# =============================================================================
# Test: Spatial Containment Validation (CRITICAL - NEW FEATURE)
# =============================================================================


class TestStorageAreaSpatialContainment:
    """Test spatial containment validation trigger (area MUST be within warehouse)."""

    @pytest.mark.asyncio
    async def test_area_within_warehouse_success(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_inside_warehouse_500x500m: Polygon,
    ):
        """Test that storage area INSIDE warehouse boundary succeeds."""
        # Arrange - Create warehouse
        warehouse = Warehouse(
            code="WH-CONTAIN-SUCCESS",
            name="Containment Success Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Act - Create storage area INSIDE warehouse (should succeed)
        area = StorageArea(
            code="WH-CONTAIN-SUCCESS-NORTH",
            name="North Storage Area",
            warehouse_id=warehouse.warehouse_id,
            position="N",
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Assert - Should succeed without exception
        assert area.storage_area_id is not None
        assert area.warehouse_id == warehouse.warehouse_id

    @pytest.mark.asyncio
    async def test_area_outside_warehouse_rejected(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_outside_warehouse: Polygon,
    ):
        """Test that storage area OUTSIDE warehouse boundary is rejected.

        This is the CRITICAL test - validates spatial containment trigger.
        """
        # Arrange - Create warehouse
        warehouse = Warehouse(
            code="WH-CONTAIN-FAIL",
            name="Containment Fail Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Act & Assert - Create storage area OUTSIDE warehouse (should fail)
        area = StorageArea(
            code="WH-CONTAIN-FAIL-OUTSIDE",
            name="Outside Storage Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_outside_warehouse, srid=4326),
        )
        db_session.add(area)

        with pytest.raises(IntegrityError, match="within warehouse boundary|containment"):
            await db_session.commit()

        # Rollback to clean up
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_area_partially_outside_rejected(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_partially_outside_warehouse: Polygon,
    ):
        """Test that storage area PARTIALLY outside warehouse is rejected.

        Area overlaps but extends beyond warehouse boundary.
        """
        # Arrange
        warehouse = Warehouse(
            code="WH-PARTIAL-FAIL",
            name="Partial Containment Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Act & Assert - Partially outside (should fail)
        area = StorageArea(
            code="WH-PARTIAL-FAIL-OVERLAP",
            name="Overlapping Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_partially_outside_warehouse, srid=4326),
        )
        db_session.add(area)

        with pytest.raises(IntegrityError, match="within warehouse boundary|containment"):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_update_area_outside_boundary_rejected(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_inside_warehouse_500x500m: Polygon,
        area_outside_warehouse: Polygon,
    ):
        """Test that updating area geometry to go outside warehouse is rejected."""
        # Arrange - Create valid area inside warehouse
        warehouse = Warehouse(
            code="WH-UPDATE-CONTAIN",
            name="Update Containment Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()

        area = StorageArea(
            code="WH-UPDATE-CONTAIN-AREA",
            name="Valid Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        # Act & Assert - Update to move outside (should fail)
        area.geojson_coordinates = from_shape(area_outside_warehouse, srid=4326)

        with pytest.raises(IntegrityError, match="within warehouse boundary|containment"):
            await db_session.commit()

        await db_session.rollback()


# =============================================================================
# Test: Self-Referential Relationships (Parent/Child Areas)
# =============================================================================


class TestStorageAreaHierarchy:
    """Test self-referential parent/child relationships."""

    @pytest.mark.asyncio
    async def test_hierarchical_area_query(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test querying parent → children relationship."""
        # Arrange - Create warehouse
        warehouse = await warehouse_factory(code="WH-HIERARCHY")

        # Create parent area (NORTH wing)
        parent = StorageArea(
            code="WH-HIERARCHY-NORTH",
            name="North Wing",
            warehouse_id=warehouse.warehouse_id,
            position="N",
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(parent)
        await db_session.commit()
        await db_session.refresh(parent)

        # Create child areas (PROP-1 and PROP-2 within North wing)
        child1_polygon = Polygon(
            [
                (-70.6485, -33.4495),
                (-70.6483, -33.4495),
                (-70.6483, -33.4493),
                (-70.6485, -33.4493),
                (-70.6485, -33.4495),
            ]
        )
        child1 = StorageArea(
            code="WH-HIERARCHY-NORTH-PROP1",
            name="Propagation Zone 1",
            warehouse_id=warehouse.warehouse_id,
            parent_area_id=parent.storage_area_id,
            geojson_coordinates=from_shape(child1_polygon, srid=4326),
        )

        child2_polygon = Polygon(
            [
                (-70.6483, -33.4495),
                (-70.6481, -33.4495),
                (-70.6481, -33.4493),
                (-70.6483, -33.4493),
                (-70.6483, -33.4495),
            ]
        )
        child2 = StorageArea(
            code="WH-HIERARCHY-NORTH-PROP2",
            name="Propagation Zone 2",
            warehouse_id=warehouse.warehouse_id,
            parent_area_id=parent.storage_area_id,
            geojson_coordinates=from_shape(child2_polygon, srid=4326),
        )

        db_session.add_all([child1, child2])
        await db_session.commit()

        # Act - Query parent and access children
        await db_session.refresh(parent)

        # Assert - Parent should have 2 children
        assert len(parent.child_areas) == 2
        child_codes = [c.code for c in parent.child_areas]
        assert "WH-HIERARCHY-NORTH-PROP1" in child_codes
        assert "WH-HIERARCHY-NORTH-PROP2" in child_codes


# =============================================================================
# Test: Cascade Delete
# =============================================================================


class TestStorageAreaCascadeDelete:
    """Test cascade delete behavior."""

    @pytest.mark.asyncio
    async def test_cascade_delete_from_warehouse(
        self,
        db_session: AsyncSession,
        warehouse_polygon_1000x1000m: Polygon,
        area_inside_warehouse_500x500m: Polygon,
    ):
        """Test that deleting warehouse cascades to storage areas."""
        # Arrange - Create warehouse + 3 storage areas
        warehouse = Warehouse(
            code="WH-CASCADE-DELETE",
            name="Cascade Delete Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(warehouse_polygon_1000x1000m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        area1 = StorageArea(
            code="WH-CASCADE-DELETE-NORTH",
            name="North Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        area2 = StorageArea(
            code="WH-CASCADE-DELETE-SOUTH",
            name="South Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        area3 = StorageArea(
            code="WH-CASCADE-DELETE-EAST",
            name="East Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )

        db_session.add_all([area1, area2, area3])
        await db_session.commit()

        area_ids = [area1.storage_area_id, area2.storage_area_id, area3.storage_area_id]

        # Act - Delete warehouse
        await db_session.delete(warehouse)
        await db_session.commit()

        # Assert - All storage areas should be deleted
        for area_id in area_ids:
            result = await db_session.execute(
                select(StorageArea).where(StorageArea.storage_area_id == area_id)
            )
            deleted_area = result.scalar_one_or_none()
            assert deleted_area is None

    @pytest.mark.asyncio
    async def test_cascade_delete_parent_area(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test that deleting parent area cascades to child areas."""
        # Arrange - Create parent + 2 children
        warehouse = await warehouse_factory(code="WH-CASCADE-PARENT")

        parent = StorageArea(
            code="WH-CASCADE-PARENT-NORTH",
            name="North Wing",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(parent)
        await db_session.commit()
        await db_session.refresh(parent)

        child1_polygon = Polygon(
            [
                (-70.6485, -33.4495),
                (-70.6483, -33.4495),
                (-70.6483, -33.4493),
                (-70.6485, -33.4493),
                (-70.6485, -33.4495),
            ]
        )
        child1 = StorageArea(
            code="WH-CASCADE-PARENT-CHILD1",
            name="Child 1",
            warehouse_id=warehouse.warehouse_id,
            parent_area_id=parent.storage_area_id,
            geojson_coordinates=from_shape(child1_polygon, srid=4326),
        )

        child2_polygon = Polygon(
            [
                (-70.6483, -33.4495),
                (-70.6481, -33.4495),
                (-70.6481, -33.4493),
                (-70.6483, -33.4493),
                (-70.6483, -33.4495),
            ]
        )
        child2 = StorageArea(
            code="WH-CASCADE-PARENT-CHILD2",
            name="Child 2",
            warehouse_id=warehouse.warehouse_id,
            parent_area_id=parent.storage_area_id,
            geojson_coordinates=from_shape(child2_polygon, srid=4326),
        )

        db_session.add_all([child1, child2])
        await db_session.commit()

        child_ids = [child1.storage_area_id, child2.storage_area_id]

        # Act - Delete parent area
        await db_session.delete(parent)
        await db_session.commit()

        # Assert - Children should be deleted
        for child_id in child_ids:
            result = await db_session.execute(
                select(StorageArea).where(StorageArea.storage_area_id == child_id)
            )
            deleted_child = result.scalar_one_or_none()
            assert deleted_child is None


# =============================================================================
# Test: Spatial Queries
# =============================================================================


class TestStorageAreaSpatialQueries:
    """Test PostGIS spatial query functions."""

    @pytest.mark.asyncio
    async def test_find_area_by_gps_point(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test ST_Contains: GPS point → StorageArea lookup (critical for photo localization)."""
        # Arrange - Create warehouse + storage area
        warehouse = await warehouse_factory(code="WH-GPS-LOOKUP")

        area = StorageArea(
            code="WH-GPS-LOOKUP-CENTER",
            name="Center Area",
            warehouse_id=warehouse.warehouse_id,
            position="C",
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()

        # Test GPS point inside area (centroid of the polygon)
        gps_point = from_shape(Point(-70.64825, -33.44925), srid=4326)

        # Act - Query for storage area containing GPS point
        stmt = select(StorageArea).where(ST_Contains(StorageArea.geojson_coordinates, gps_point))
        result = await db_session.execute(stmt)
        found_areas = result.scalars().all()

        # Assert
        assert len(found_areas) == 1
        assert found_areas[0].code == "WH-GPS-LOOKUP-CENTER"

    @pytest.mark.asyncio
    async def test_find_areas_within_radius(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test ST_DWithin: Find storage areas within N meters of GPS point."""
        # Arrange - Create 3 storage areas at different distances
        warehouse = await warehouse_factory(code="WH-RADIUS")

        # Area 1: Close to target point
        area1 = StorageArea(
            code="WH-RADIUS-NEAR",
            name="Near Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )

        # Area 2: Far from target point
        far_polygon = Polygon(
            [
                (-70.665, -33.465),
                (-70.664, -33.465),
                (-70.664, -33.464),
                (-70.665, -33.464),
                (-70.665, -33.465),
            ]
        )
        area2 = StorageArea(
            code="WH-RADIUS-FAR",
            name="Far Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(far_polygon, srid=4326),
        )

        db_session.add_all([area1, area2])
        await db_session.commit()

        # Act - Find areas within 1000m of target point
        target_point = from_shape(Point(-70.6482, -33.4492), srid=4326)

        stmt = select(StorageArea).where(
            ST_DWithin(
                StorageArea.centroid.cast(text("geography")),
                target_point.cast(text("geography")),
                1000,  # 1000 meters
            )
        )
        result = await db_session.execute(stmt)
        nearby_areas = result.scalars().all()

        # Assert - Should find only nearby area
        codes = [a.code for a in nearby_areas]
        assert "WH-RADIUS-NEAR" in codes
        assert "WH-RADIUS-FAR" not in codes


# =============================================================================
# Test: GIST Index Performance
# =============================================================================


class TestStorageAreaGISTIndexPerformance:
    """Test GIST spatial index usage with EXPLAIN ANALYZE."""

    @pytest.mark.asyncio
    async def test_gist_index_used_for_spatial_query(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Verify that GIST index is used for spatial queries (not sequential scan)."""
        # Arrange - Create test storage area
        warehouse = await warehouse_factory(code="WH-INDEX-TEST")

        area = StorageArea(
            code="WH-INDEX-TEST-NORTH",
            name="Index Test Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area)
        await db_session.commit()

        # Act - Run EXPLAIN ANALYZE on spatial query
        explain_query = text("""
            EXPLAIN ANALYZE
            SELECT * FROM storage_areas
            WHERE ST_Contains(
                geojson_coordinates,
                ST_SetSRID(ST_MakePoint(-70.6482, -33.4492), 4326)
            )
        """)

        result = await db_session.execute(explain_query)
        explain_output = "\n".join([row[0] for row in result.fetchall()])

        # Assert - Should use GIST index (NOT "Seq Scan")
        assert "Index Scan" in explain_output or "Bitmap Heap Scan" in explain_output
        assert "idx_storage_areas_geom" in explain_output


# =============================================================================
# Test: Code Uniqueness
# =============================================================================


class TestStorageAreaCodeUniqueness:
    """Test unique constraint on code field (integration with DB)."""

    @pytest.mark.asyncio
    async def test_duplicate_code_rejected(
        self, db_session: AsyncSession, warehouse_factory, area_inside_warehouse_500x500m: Polygon
    ):
        """Test that duplicate storage area codes are rejected by database."""
        # Arrange - Create first storage area
        warehouse = await warehouse_factory(code="WH-UNIQUE")

        area1 = StorageArea(
            code="WH-UNIQUE-NORTH",
            name="First North Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area1)
        await db_session.commit()

        # Act & Assert - Try to create second area with same code
        area2 = StorageArea(
            code="WH-UNIQUE-NORTH",  # Duplicate!
            name="Second North Area",
            warehouse_id=warehouse.warehouse_id,
            geojson_coordinates=from_shape(area_inside_warehouse_500x500m, srid=4326),
        )
        db_session.add(area2)

        with pytest.raises(IntegrityError, match="unique|duplicate"):
            await db_session.commit()
