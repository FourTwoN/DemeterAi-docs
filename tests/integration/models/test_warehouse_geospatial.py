"""Integration tests for Warehouse model with PostGIS spatial features.

These tests require a REAL PostgreSQL database with PostGIS extension enabled.
They test:
- GENERATED column for area_m2 auto-calculation
- Trigger for centroid auto-update (INSERT + UPDATE)
- Spatial queries (ST_DWithin, ST_Distance, ST_Contains)
- GIST index performance verification with EXPLAIN ANALYZE
- Full database stack (no mocking)

NOTE: These tests will be SKIPPED if running with SQLite in-memory database.
      Run with PostgreSQL test database to execute these tests.

Test data uses realistic GPS coordinates (Santiago, Chile region).
"""

from decimal import Decimal

import pytest
from geoalchemy2.functions import ST_Area, ST_Contains, ST_Distance, ST_DWithin
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point, Polygon
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import Warehouse

# Skip all tests in this module if PostGIS is not available
# (i.e., running with SQLite in-memory database)
# Note: Integration tests are skipped by default in SQLite mode
pytestmark = pytest.mark.integration


@pytest.fixture
def sample_polygon_100x50m():
    """Create a 100m x 50m rectangular polygon (realistic warehouse size).

    Coordinates are in Santiago, Chile region (WGS84/SRID 4326).
    This represents a typical greenhouse or cultivation area.
    """
    coords = [
        (-70.648300, -33.448900),  # SW corner
        (-70.647300, -33.448900),  # SE corner (100m east)
        (-70.647300, -33.449400),  # NE corner (50m north)
        (-70.648300, -33.449400),  # NW corner
        (-70.648300, -33.448900),  # Close polygon
    ]
    return Polygon(coords)


@pytest.fixture
def sample_polygon_large():
    """Create a larger polygon for distance testing (~200m x 100m)."""
    coords = [
        (-70.650000, -33.450000),
        (-70.648000, -33.450000),
        (-70.648000, -33.451000),
        (-70.650000, -33.451000),
        (-70.650000, -33.450000),
    ]
    return Polygon(coords)


class TestWarehouseGeneratedColumnArea:
    """Test GENERATED column for area_m2 auto-calculation from geometry."""

    @pytest.mark.asyncio
    async def test_area_auto_calculated_on_insert(
        self, db_session: AsyncSession, sample_polygon_100x50m: Polygon
    ):
        """Test that area_m2 is auto-calculated from geometry on INSERT.

        The area should be approximately 5000 m² (100m x 50m).
        GENERATED column uses ST_Area(geojson_coordinates::geography).
        """
        # Arrange
        warehouse = Warehouse(
            code="AREA-TEST-01",
            name="Area Calculation Test Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )

        # Act
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Assert
        assert warehouse.area_m2 is not None
        assert warehouse.area_m2 > 0

        # Area should be approximately 5000 m² (allowing 10% tolerance for spherical geometry)
        expected_area = Decimal("5000.00")
        tolerance = expected_area * Decimal("0.10")  # 10% tolerance
        assert abs(warehouse.area_m2 - expected_area) < tolerance

    @pytest.mark.asyncio
    async def test_area_updates_when_geometry_changes(
        self,
        db_session: AsyncSession,
        sample_polygon_100x50m: Polygon,
        sample_polygon_large: Polygon,
    ):
        """Test that area_m2 recalculates when geometry is updated."""
        # Arrange - Create warehouse with small polygon
        warehouse = Warehouse(
            code="AREA-UPDATE-01",
            name="Area Update Test",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        initial_area = warehouse.area_m2

        # Act - Update geometry to larger polygon
        warehouse.geojson_coordinates = from_shape(sample_polygon_large, srid=4326)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Assert - Area should have increased
        assert warehouse.area_m2 > initial_area

    @pytest.mark.asyncio
    async def test_area_calculation_uses_geography_cast(
        self, db_session: AsyncSession, sample_polygon_100x50m: Polygon
    ):
        """Verify area calculation uses geography cast for accurate spherical measurements.

        ST_Area(geometry) returns square degrees (inaccurate)
        ST_Area(geography) returns square meters (accurate)
        """
        # Arrange
        warehouse = Warehouse(
            code="GEOGRAPHY-01",
            name="Geography Cast Test",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Act - Manual calculation using geography cast
        result = await db_session.execute(
            select(ST_Area(Warehouse.geojson_coordinates.cast(text("geography")))).where(
                Warehouse.warehouse_id == warehouse.warehouse_id
            )
        )
        manual_area = result.scalar_one()

        # Assert - GENERATED column should match manual calculation
        assert abs(float(warehouse.area_m2) - manual_area) < 0.01  # Within 1 cm²


class TestWarehouseCentroidTrigger:
    """Test trigger for centroid auto-calculation (BEFORE INSERT OR UPDATE)."""

    @pytest.mark.asyncio
    async def test_centroid_auto_set_on_insert(
        self, db_session: AsyncSession, sample_polygon_100x50m: Polygon
    ):
        """Test that centroid is auto-calculated by trigger on INSERT."""
        # Arrange
        warehouse = Warehouse(
            code="CENTROID-01",
            name="Centroid Test Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )

        # Centroid should be None before insert
        assert warehouse.centroid is None

        # Act
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Assert - Centroid should be auto-populated by trigger
        assert warehouse.centroid is not None

    @pytest.mark.asyncio
    async def test_centroid_within_polygon(
        self, db_session: AsyncSession, sample_polygon_100x50m: Polygon
    ):
        """Test that calculated centroid is actually inside the polygon."""
        # Arrange
        warehouse = Warehouse(
            code="CENTROID-INSIDE-01",
            name="Centroid Inside Test",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        # Act - Convert geometries to Shapely for containment check
        polygon_shape = to_shape(warehouse.geojson_coordinates)
        centroid_shape = to_shape(warehouse.centroid)

        # Assert - Centroid should be contained within polygon
        assert polygon_shape.contains(centroid_shape)

    @pytest.mark.asyncio
    async def test_centroid_updates_on_geometry_change(
        self,
        db_session: AsyncSession,
        sample_polygon_100x50m: Polygon,
        sample_polygon_large: Polygon,
    ):
        """Test that centroid is recalculated when geometry changes (UPDATE trigger)."""
        # Arrange - Create warehouse
        warehouse = Warehouse(
            code="CENTROID-UPDATE-01",
            name="Centroid Update Test",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        initial_centroid = to_shape(warehouse.centroid)

        # Act - Update geometry to different location
        warehouse.geojson_coordinates = from_shape(sample_polygon_large, srid=4326)
        await db_session.commit()
        await db_session.refresh(warehouse)

        updated_centroid = to_shape(warehouse.centroid)

        # Assert - Centroid should have moved
        assert initial_centroid.x != updated_centroid.x
        assert initial_centroid.y != updated_centroid.y


class TestWarehouseSpatialQueries:
    """Test PostGIS spatial query functions."""

    @pytest.fixture
    async def create_multiple_warehouses(self, db_session: AsyncSession):
        """Create 3 warehouses at different distances for spatial testing."""
        # Warehouse 1: Close to origin point (-70.6475, -33.4495)
        w1 = Warehouse(
            code="NEAR-01",
            name="Nearby Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        # Warehouse 2: Medium distance (~500m away)
        w2 = Warehouse(
            code="MID-01",
            name="Mid Distance Warehouse",
            warehouse_type="shadehouse",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.653, -33.453),
                        (-70.652, -33.453),
                        (-70.652, -33.454),
                        (-70.653, -33.454),
                        (-70.653, -33.453),
                    ]
                ),
                srid=4326,
            ),
        )

        # Warehouse 3: Far away (~2km away)
        w3 = Warehouse(
            code="FAR-01",
            name="Far Warehouse",
            warehouse_type="open_field",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.665, -33.465),
                        (-70.664, -33.465),
                        (-70.664, -33.466),
                        (-70.665, -33.466),
                        (-70.665, -33.465),
                    ]
                ),
                srid=4326,
            ),
        )

        db_session.add_all([w1, w2, w3])
        await db_session.commit()

        return [w1, w2, w3]

    @pytest.mark.asyncio
    async def test_find_warehouses_within_radius(
        self, db_session: AsyncSession, create_multiple_warehouses
    ):
        """Test ST_DWithin to find warehouses within N meters of a GPS point.

        This is critical for photo localization - finding which warehouse
        a GPS-tagged photo belongs to.
        """
        # Arrange
        target_point = from_shape(Point(-70.6475, -33.4495), srid=4326)

        # Act - Find warehouses within 1000m (1km) of target point
        stmt = select(Warehouse).where(
            ST_DWithin(
                Warehouse.centroid.cast(text("geography")),
                target_point.cast(text("geography")),
                1000,  # 1000 meters radius
            )
        )
        result = await db_session.execute(stmt)
        nearby_warehouses = result.scalars().all()

        # Assert - Should find only NEAR-01 (within 1km)
        assert len(nearby_warehouses) >= 1
        codes = [w.code for w in nearby_warehouses]
        assert "NEAR-01" in codes
        assert "FAR-01" not in codes  # Too far (>2km)

    @pytest.mark.asyncio
    async def test_find_nearest_warehouse(
        self, db_session: AsyncSession, create_multiple_warehouses
    ):
        """Test ST_Distance to find the nearest warehouse to a GPS point.

        Used for photo upload when exact location is unknown.
        """
        # Arrange
        target_point = from_shape(Point(-70.6475, -33.4495), srid=4326)

        # Act - Order by distance, get closest
        stmt = (
            select(Warehouse)
            .order_by(
                ST_Distance(
                    Warehouse.centroid.cast(text("geography")), target_point.cast(text("geography"))
                )
            )
            .limit(1)
        )
        result = await db_session.execute(stmt)
        nearest = result.scalar_one()

        # Assert - Should be NEAR-01
        assert nearest.code == "NEAR-01"

    @pytest.mark.asyncio
    async def test_point_in_polygon_localization(self, db_session: AsyncSession):
        """Test ST_Contains to check if GPS point is inside warehouse boundary.

        Critical for precise photo localization - determining if a photo
        was taken inside a specific warehouse.
        """
        # Arrange - Create warehouse with known boundary
        warehouse = Warehouse(
            code="CONTAIN-01",
            name="Containment Test Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6480, -33.4490),
                        (-70.6470, -33.4490),
                        (-70.6470, -33.4500),
                        (-70.6480, -33.4500),
                        (-70.6480, -33.4490),
                    ]
                ),
                srid=4326,
            ),
        )
        db_session.add(warehouse)
        await db_session.commit()

        # Test point inside warehouse
        point_inside = from_shape(Point(-70.6475, -33.4495), srid=4326)

        # Test point outside warehouse
        point_outside = from_shape(Point(-70.6500, -33.4520), srid=4326)

        # Act - Query for warehouses containing inside point
        stmt_inside = select(Warehouse).where(
            ST_Contains(Warehouse.geojson_coordinates, point_inside)
        )
        result_inside = await db_session.execute(stmt_inside)
        warehouses_inside = result_inside.scalars().all()

        # Act - Query for warehouses containing outside point
        stmt_outside = select(Warehouse).where(
            ST_Contains(Warehouse.geojson_coordinates, point_outside)
        )
        result_outside = await db_session.execute(stmt_outside)
        warehouses_outside = result_outside.scalars().all()

        # Assert
        assert len(warehouses_inside) == 1
        assert warehouses_inside[0].code == "CONTAIN-01"
        assert len(warehouses_outside) == 0


class TestWarehouseGISTIndexPerformance:
    """Test GIST spatial index usage with EXPLAIN ANALYZE."""

    @pytest.mark.asyncio
    async def test_gist_index_used_for_spatial_query(self, db_session: AsyncSession):
        """Verify that GIST index is used for spatial queries (not sequential scan).

        GIST index is CRITICAL for performance with large warehouse datasets.
        Without it, spatial queries do full table scans.
        """
        # Arrange - Create test warehouse
        warehouse = Warehouse(
            code="INDEX-01",
            name="Index Test Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )
        db_session.add(warehouse)
        await db_session.commit()

        # Act - Run EXPLAIN ANALYZE on spatial query
        target_point = from_shape(Point(-70.6475, -33.4495), srid=4326)

        explain_query = text("""
            EXPLAIN ANALYZE
            SELECT * FROM warehouses
            WHERE ST_DWithin(
                centroid::geography,
                ST_SetSRID(ST_MakePoint(-70.6475, -33.4495), 4326)::geography,
                1000
            )
        """)

        result = await db_session.execute(explain_query)
        explain_output = "\n".join([row[0] for row in result.fetchall()])

        # Assert - Should use GIST index (NOT "Seq Scan")
        assert "Index Scan" in explain_output or "Bitmap Heap Scan" in explain_output
        assert "idx_warehouses_centroid" in explain_output

    @pytest.mark.asyncio
    async def test_gist_index_used_for_containment_query(self, db_session: AsyncSession):
        """Verify GIST index usage for ST_Contains queries."""
        # Arrange
        warehouse = Warehouse(
            code="CONTAIN-INDEX-01",
            name="Containment Index Test",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )
        db_session.add(warehouse)
        await db_session.commit()

        # Act - EXPLAIN ANALYZE for containment query
        explain_query = text("""
            EXPLAIN ANALYZE
            SELECT * FROM warehouses
            WHERE ST_Contains(
                geojson_coordinates,
                ST_SetSRID(ST_MakePoint(-70.6475, -33.4495), 4326)
            )
        """)

        result = await db_session.execute(explain_query)
        explain_output = "\n".join([row[0] for row in result.fetchall()])

        # Assert - Should use idx_warehouses_geom index
        assert "Index Scan" in explain_output or "Bitmap Heap Scan" in explain_output
        assert "idx_warehouses_geom" in explain_output


class TestWarehouseCodeUniqueness:
    """Test unique constraint on code field (integration with DB)."""

    @pytest.mark.asyncio
    async def test_duplicate_code_rejected(
        self, db_session: AsyncSession, sample_polygon_100x50m: Polygon
    ):
        """Test that duplicate warehouse codes are rejected by database."""
        # Arrange - Create first warehouse
        w1 = Warehouse(
            code="UNIQUE-01",
            name="First Warehouse",
            warehouse_type="greenhouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )
        db_session.add(w1)
        await db_session.commit()

        # Act & Assert - Try to create second warehouse with same code
        from sqlalchemy.exc import IntegrityError

        w2 = Warehouse(
            code="UNIQUE-01",  # Duplicate!
            name="Second Warehouse",
            warehouse_type="shadehouse",
            geojson_coordinates=from_shape(sample_polygon_100x50m, srid=4326),
        )
        db_session.add(w2)

        with pytest.raises(IntegrityError, match="unique|duplicate"):
            await db_session.commit()
