"""Shared pytest fixtures and configuration for DemeterAI tests.

This module provides test fixtures for:
- Database session management (with automatic rollback)
- FastAPI test client (with dependency injection)
- Sample test data factories
- Test database isolation

All fixtures use async/await and are compatible with pytest-asyncio.
Tests get a fresh database state for each test function (scope="function").
"""

# =============================================================================
# Test Database Configuration
# =============================================================================
import os
from datetime import UTC

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app

logger = get_logger(__name__)

# Use PostgreSQL test database (real database with PostGIS)
# This ensures tests are representative of production behavior
# To run tests: docker-compose up db_test -d && pytest
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test",
)

# Create test engine with NullPool (fresh connection per test)
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # No connection pooling for tests
)

# Test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create test database session with rollback after each test.

    This fixture:
    1. Drops all PostgreSQL ENUM types (from previous test runs)
    2. Creates all tables using SQLAlchemy metadata + manual SQL for GENERATED columns & triggers
    3. Yields a session for the test to use
    4. Rolls back any changes after the test completes
    5. Drops all tables (clean slate for next test)
    6. Drops all ENUM types (clean slate for next test)

    NOTE: We use SQLAlchemy create_all() + manual SQL because:
    - SQLAlchemy models define base structure and constraints
    - Manual SQL defines GENERATED columns and triggers that SQLAlchemy doesn't support
    - Tests reflect actual database behavior with all triggers active

    PostgreSQL ENUM handling:
        - SQLAlchemy's drop_all() drops tables but NOT enum types
        - We explicitly drop all enum types before AND after tests

    Usage:
        @pytest.mark.unit
        async def test_warehouse_creation(db_session):
            warehouse = Warehouse(code="WH-001", name="Test")
            db_session.add(warehouse)
            await db_session.commit()
            assert warehouse.id is not None
    """
    from sqlalchemy import text

    # List of all PostgreSQL ENUM types used in models
    # IMPORTANT: Keep this list in sync with app/models/*.py and alembic migrations
    enum_types = [
        "storage_bin_status_enum",
        "warehouse_type_enum",
        "position_enum",
        "sessionstatusenum",  # photo_processing_sessions
        "sampletypeenum",  # product_sample_images
        "movementtypeenum",  # stock_movements
        "sourcetypeenum",  # stock_movements
        "calculationmethodenum",  # estimations
        "bin_category_enum",  # storage_bin_types
    ]

    # Drop all ENUM types BEFORE creating tables
    async with test_engine.begin() as conn:
        for enum_type in enum_types:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type} CASCADE"))

    # Create all tables using SQLAlchemy metadata (respects FK dependencies via sorted_tables)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add GENERATED columns and triggers via raw SQL
    # These are not supported by SQLAlchemy ORM, so we execute them manually
    # Wrap in try/except per section so one failure doesn't abort the entire transaction
    async with test_engine.begin() as conn:
        try:
            # Warehouses: Convert area_m2 to GENERATED column
            await conn.execute(text("ALTER TABLE warehouses DROP COLUMN IF EXISTS area_m2 CASCADE"))
            await conn.execute(
                text("""
               ALTER TABLE warehouses
                   ADD COLUMN area_m2 NUMERIC(10, 2)
                       GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
               """)
            )
        except Exception:
            pass  # Column conversion failed, but tests can still run

        try:
            # Warehouses: centroid trigger function
            await conn.execute(
                text("""
               CREATE
               OR REPLACE FUNCTION update_warehouse_centroid()
                RETURNS TRIGGER AS $$
               BEGIN
                    NEW.centroid
               = ST_Centroid(NEW.geojson_coordinates);
               RETURN NEW;
               END;
                $$
               LANGUAGE plpgsql;
               """)
            )
            # Create trigger
            await conn.execute(
                text("""
               CREATE TRIGGER IF NOT EXISTS trg_warehouse_centroid
                BEFORE INSERT OR
               UPDATE OF geojson_coordinates
               ON warehouses
                   FOR EACH ROW
                   EXECUTE FUNCTION update_warehouse_centroid();
               """)
            )
        except Exception:
            pass  # Trigger might already exist

        try:
            # StorageAreas: area_m2 GENERATED column
            await conn.execute(
                text("ALTER TABLE storage_areas DROP COLUMN IF EXISTS area_m2 CASCADE")
            )
            await conn.execute(
                text("""
               ALTER TABLE storage_areas
                   ADD COLUMN area_m2 NUMERIC(10, 2)
                       GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
               """)
            )
        except Exception:
            pass

        try:
            # StorageAreas: centroid trigger function
            await conn.execute(
                text("""
               CREATE
               OR REPLACE FUNCTION update_storage_area_centroid()
                RETURNS TRIGGER AS $$
               BEGIN
                    NEW.centroid
               = ST_Centroid(NEW.geojson_coordinates);
               RETURN NEW;
               END;
                $$
               LANGUAGE plpgsql;
               """)
            )
            # Create trigger
            await conn.execute(
                text("""
               CREATE TRIGGER IF NOT EXISTS trg_storage_area_centroid
                BEFORE INSERT OR
               UPDATE OF geojson_coordinates
               ON storage_areas
                   FOR EACH ROW
                   EXECUTE FUNCTION update_storage_area_centroid();
               """)
            )
        except Exception:
            pass

        try:
            # StorageLocations: area_m2 GENERATED column (should be 0 for POINT geometries)
            await conn.execute(
                text("ALTER TABLE storage_locations DROP COLUMN IF EXISTS area_m2 CASCADE")
            )
            await conn.execute(
                text("""
               ALTER TABLE storage_locations
                   ADD COLUMN area_m2 NUMERIC(10, 2)
                       GENERATED ALWAYS AS (0) STORED
               """)
            )
        except Exception:
            pass

        try:
            # StorageLocations: centroid = coordinates (for POINT geometries)
            await conn.execute(
                text("""
               CREATE
               OR REPLACE FUNCTION update_storage_location_centroid()
                RETURNS TRIGGER AS $$
               BEGIN
                    NEW.centroid
               = NEW.geojson_coordinates;
               RETURN NEW;
               END;
                $$
               LANGUAGE plpgsql;
               """)
            )
            # Create trigger
            await conn.execute(
                text("""
               CREATE TRIGGER IF NOT EXISTS trg_storage_location_centroid
                BEFORE INSERT OR
               UPDATE OF geojson_coordinates
               ON storage_locations
                   FOR EACH ROW
                   EXECUTE FUNCTION update_storage_location_centroid();
               """)
            )
        except Exception:
            pass

    # Create session
    async with TestSessionLocal() as session:
        # Start a transaction
        await session.begin()

        yield session

        # Rollback any changes
        await session.rollback()

    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Drop all ENUM types AFTER dropping tables (clean slate)
    async with test_engine.begin() as conn:
        for enum_type in enum_types:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type} CASCADE"))


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI test client with test database.

    This fixture:
    1. Overrides the get_db_session dependency to use the test database
    2. Creates an async HTTP client for making requests
    3. Automatically cleans up overrides after test completes

    Usage:
        @pytest.mark.integration
        async def test_health_endpoint(client):
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}
    """

    # Override database dependency to use test database
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Create async HTTP client
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Clear overrides after test
    app.dependency_overrides.clear()


# =============================================================================
# Sample Data Fixtures (Factories)
# =============================================================================


@pytest.fixture
def sample_warehouse():
    """Factory fixture for warehouse test data with PostGIS geometry.

    Returns a dictionary that can be used to create a Warehouse instance.
    Includes realistic GPS coordinates (Santiago, Chile region).

    Usage:
        from app.models.warehouse import Warehouse
        from geoalchemy2.shape import from_shape

        def test_warehouse_creation(sample_warehouse):
            warehouse = Warehouse(**sample_warehouse)
            assert warehouse.code == "WH-TEST"
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon

    # 100m x 50m rectangular polygon (realistic greenhouse size)
    coords = [
        (-70.648300, -33.448900),  # SW corner
        (-70.647300, -33.448900),  # SE corner
        (-70.647300, -33.449400),  # NE corner
        (-70.648300, -33.449400),  # NW corner
        (-70.648300, -33.448900),  # Close polygon
    ]

    return {
        "code": "WH-TEST",
        "name": "Test Warehouse",
        "warehouse_type": "greenhouse",
        "geojson_coordinates": from_shape(Polygon(coords), srid=4326),
        "active": True,
    }


@pytest.fixture
def warehouse_factory(db_session):
    """Factory fixture for creating multiple warehouse instances.

    Creates warehouses with realistic PostGIS geometry and auto-incremented codes.

    Usage:
        @pytest.mark.asyncio
        async def test_multiple_warehouses(warehouse_factory):
            w1 = await warehouse_factory(code="WH-01")
            w2 = await warehouse_factory(code="WH-02", warehouse_type="shadehouse")
            assert w1.warehouse_id != w2.warehouse_id
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon

    from app.models.warehouse import Warehouse

    async def _create_warehouse(**kwargs):
        """Create and persist a warehouse with sensible defaults."""
        # Default geometry: 100m x 50m polygon
        default_coords = [
            (-70.648300, -33.448900),
            (-70.647300, -33.448900),
            (-70.647300, -33.449400),
            (-70.648300, -33.449400),
            (-70.648300, -33.448900),
        ]

        defaults = {
            "code": f"WH-{id(kwargs)}",  # Unique code
            "name": "Test Warehouse",
            "warehouse_type": "greenhouse",
            "geojson_coordinates": from_shape(Polygon(default_coords), srid=4326),
            "active": True,
        }

        # Merge user-provided kwargs
        defaults.update(kwargs)

        warehouse = Warehouse(**defaults)
        db_session.add(warehouse)
        await db_session.commit()
        await db_session.refresh(warehouse)

        return warehouse

    return _create_warehouse


@pytest.fixture
def sample_storage_area():
    """Factory fixture for storage area test data with PostGIS geometry.

    Returns a dictionary that can be used to create a StorageArea instance.
    Includes realistic GPS coordinates (Santiago, Chile region) for area INSIDE warehouse.

    Usage:
        from app.models.storage_area import StorageArea
        from geoalchemy2.shape import from_shape

        def test_storage_area_creation(sample_storage_area):
            area = StorageArea(**sample_storage_area)
            assert area.code == "WH-AREA-TEST"
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon

    # 500m x 500m rectangular polygon (realistic storage area size)
    # Coordinates INSIDE default warehouse bounds
    coords = [
        (-70.6485, -33.4495),  # SW corner
        (-70.6480, -33.4495),  # SE corner (500m east)
        (-70.6480, -33.4490),  # NE corner (500m north)
        (-70.6485, -33.4490),  # NW corner
        (-70.6485, -33.4495),  # Close polygon
    ]

    return {
        "code": "WH-AREA-TEST",
        "name": "Test Storage Area",
        "warehouse_id": 1,  # Must be set to valid warehouse ID in tests
        "position": "N",
        "geojson_coordinates": from_shape(Polygon(coords), srid=4326),
        "active": True,
    }


@pytest.fixture
def storage_area_factory(db_session, warehouse_factory):
    """Factory fixture for creating multiple storage area instances.

    Creates storage areas with realistic PostGIS geometry INSIDE warehouse bounds.
    Auto-creates warehouse if not provided.

    Usage:
        @pytest.mark.asyncio
        async def test_multiple_areas(storage_area_factory):
            area1 = await storage_area_factory(code="WH-AREA-01")
            area2 = await storage_area_factory(code="WH-AREA-02", position="S")
            assert area1.storage_area_id != area2.storage_area_id
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon

    from app.models.storage_area import StorageArea

    async def _create_storage_area(warehouse=None, **kwargs):
        """Create and persist a storage area with sensible defaults."""
        # Create warehouse if not provided
        if warehouse is None:
            warehouse = await warehouse_factory()

        # Default geometry: 500m x 500m polygon INSIDE warehouse
        default_coords = [
            (-70.6485, -33.4495),  # SW
            (-70.6480, -33.4495),  # SE
            (-70.6480, -33.4490),  # NE
            (-70.6485, -33.4490),  # NW
            (-70.6485, -33.4495),  # Close
        ]

        defaults = {
            "code": f"WH-AREA-{id(kwargs)}",  # Unique code
            "name": "Test Storage Area",
            "warehouse_id": warehouse.warehouse_id,
            "position": "N",
            "geojson_coordinates": from_shape(Polygon(default_coords), srid=4326),
            "active": True,
        }

        # Merge user-provided kwargs
        defaults.update(kwargs)

        area = StorageArea(**defaults)
        db_session.add(area)
        await db_session.commit()
        await db_session.refresh(area)

        return area

    return _create_storage_area


@pytest.fixture
async def sample_storage_areas(db_session, warehouse_factory):
    """Create warehouse + 3 storage areas for testing hierarchical queries.

    Returns:
        tuple: (warehouse, north_area, south_area, center_area)

    Usage:
        @pytest.mark.asyncio
        async def test_multiple_areas(sample_storage_areas):
            warehouse, north, south, center = sample_storage_areas
            assert north.warehouse_id == warehouse.warehouse_id
            assert len(warehouse.storage_areas) == 3
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Polygon

    from app.models.storage_area import StorageArea

    # Create warehouse
    warehouse = await warehouse_factory(code="WH-SAMPLE")

    # Create North area
    north_coords = [
        (-70.6485, -33.4495),
        (-70.6480, -33.4495),
        (-70.6480, -33.4490),
        (-70.6485, -33.4490),
        (-70.6485, -33.4495),
    ]
    north_area = StorageArea(
        code="WH-SAMPLE-NORTH",
        name="North Storage Area",
        warehouse_id=warehouse.warehouse_id,
        position="N",
        geojson_coordinates=from_shape(Polygon(north_coords), srid=4326),
    )

    # Create South area
    south_coords = [
        (-70.6485, -33.4505),
        (-70.6480, -33.4505),
        (-70.6480, -33.4500),
        (-70.6485, -33.4500),
        (-70.6485, -33.4505),
    ]
    south_area = StorageArea(
        code="WH-SAMPLE-SOUTH",
        name="South Storage Area",
        warehouse_id=warehouse.warehouse_id,
        position="S",
        geojson_coordinates=from_shape(Polygon(south_coords), srid=4326),
    )

    # Create Center area
    center_coords = [
        (-70.6483, -33.4493),
        (-70.6481, -33.4493),
        (-70.6481, -33.4491),
        (-70.6483, -33.4491),
        (-70.6483, -33.4493),
    ]
    center_area = StorageArea(
        code="WH-SAMPLE-CENTER",
        name="Center Propagation Zone",
        warehouse_id=warehouse.warehouse_id,
        position="C",
        geojson_coordinates=from_shape(Polygon(center_coords), srid=4326),
    )

    db_session.add_all([north_area, south_area, center_area])
    await db_session.commit()
    await db_session.refresh(north_area)
    await db_session.refresh(south_area)
    await db_session.refresh(center_area)

    return warehouse, north_area, south_area, center_area


@pytest.fixture
def sample_product():
    """Factory fixture for product test data.

    Usage:
        async def test_product_creation(sample_product, db_session):
            # Create family first
            family = ProductFamily(
                category_id=1,
                code="TEST-FAM",
                name="Test Family"
            )
            db_session.add(family)
            await db_session.commit()

            # Then create product
            sample_product["family_id"] = family.family_id
            product = Product(**sample_product)
            assert product.sku == "TEST-PROD-001"
    """
    return {
        "sku": "TEST-PROD-001",
        "common_name": "Test Product",
        "description": "Product for testing",
        "scientific_name": "Testus productus",
        "family_id": 1,  # Must be set to valid family ID in tests
        "custom_attributes": {},
    }


@pytest.fixture
def sample_storage_location():
    """Factory fixture for storage location test data with PostGIS geometry (POINT).

    Returns a dictionary that can be used to create a StorageLocation instance.
    Includes realistic GPS coordinates (Santiago, Chile region) for location INSIDE storage area.

    Usage:
        from app.models.storage_location import StorageLocation
        from geoalchemy2.shape import from_shape

        def test_storage_location_creation(sample_storage_location):
            location = StorageLocation(**sample_storage_location)
            assert location.code == "WH-AREA-LOC001"
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    # GPS point (realistic location coordinate)
    # Coordinates INSIDE default storage area bounds
    point = Point(-70.64825, -33.44925)  # Center of default area

    return {
        "code": "WH-AREA-LOC001",
        "name": "Test Storage Location",
        "storage_area_id": 1,  # Must be set to valid storage area ID in tests
        "qr_code": "LOC12345",
        "coordinates": from_shape(point, srid=4326),
        "position_metadata": {},
        "active": True,
    }


@pytest.fixture
def storage_location_factory(db_session, storage_area_factory):
    """Factory fixture for creating multiple storage location instances.

    Creates storage locations with realistic PostGIS POINT geometry INSIDE storage area bounds.
    Auto-creates storage area (and warehouse) if not provided.

    Usage:
        @pytest.mark.asyncio
        async def test_multiple_locations(storage_location_factory):
            loc1 = await storage_location_factory(code="WH-AREA-LOC01")
            loc2 = await storage_location_factory(code="WH-AREA-LOC02", qr_code="QR002")
            assert loc1.location_id != loc2.location_id
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    from app.models.storage_location import StorageLocation

    async def _create_storage_location(storage_area=None, **kwargs):
        """Create and persist a storage location with sensible defaults."""
        # Create storage area (and warehouse) if not provided
        if storage_area is None:
            storage_area = await storage_area_factory()

        # Default geometry: POINT INSIDE storage area
        # Generate unique point coordinates (slight variation for each location)
        base_x = -70.64825
        base_y = -33.44925
        offset = id(kwargs) % 1000 * 0.00001  # Slight offset for uniqueness
        default_point = Point(base_x + offset, base_y + offset)

        defaults = {
            "code": f"WH-AREA-LOC-{id(kwargs)}",  # Unique code
            "name": "Test Storage Location",
            "storage_area_id": storage_area.storage_area_id,
            "qr_code": f"LOC{id(kwargs) % 100000:05d}",  # Unique QR code (8 chars)
            "coordinates": from_shape(default_point, srid=4326),
            "position_metadata": {},
            "active": True,
        }

        # Merge user-provided kwargs
        defaults.update(kwargs)

        location = StorageLocation(**defaults)
        db_session.add(location)
        await db_session.commit()
        await db_session.refresh(location)

        return location

    return _create_storage_location


@pytest.fixture
async def sample_storage_locations(db_session, storage_area_factory):
    """Create storage area + 3 storage locations for testing hierarchical queries.

    Returns:
        tuple: (storage_area, location1, location2, location3)

    Usage:
        @pytest.mark.asyncio
        async def test_multiple_locations(sample_storage_locations):
            area, loc1, loc2, loc3 = sample_storage_locations
            assert loc1.storage_area_id == area.storage_area_id
            assert len(area.storage_locations) == 3
    """
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    from app.models.storage_location import StorageLocation

    # Create storage area
    area = await storage_area_factory(code="WH-SAMPLE-AREA")

    # Create Location 1 (center)
    location1 = StorageLocation(
        code="WH-SAMPLE-AREA-LOC1",
        name="Storage Location 1",
        storage_area_id=area.storage_area_id,
        qr_code="LOC-SAM-01",
        geojson_coordinates=from_shape(Point(-70.64825, -33.44925), srid=4326),
        position_metadata={},
    )

    # Create Location 2 (slightly east)
    location2 = StorageLocation(
        code="WH-SAMPLE-AREA-LOC2",
        name="Storage Location 2",
        storage_area_id=area.storage_area_id,
        qr_code="LOC-SAM-02",
        geojson_coordinates=from_shape(Point(-70.64820, -33.44920), srid=4326),
        position_metadata={},
    )

    # Create Location 3 (slightly west)
    location3 = StorageLocation(
        code="WH-SAMPLE-AREA-LOC3",
        name="Storage Location 3",
        storage_area_id=area.storage_area_id,
        qr_code="LOC-SAM-03",
        geojson_coordinates=from_shape(Point(-70.64830, -33.44930), srid=4326),
        position_metadata={},
    )

    db_session.add_all([location1, location2, location3])
    await db_session.commit()
    await db_session.refresh(location1)
    await db_session.refresh(location2)
    await db_session.refresh(location3)

    return area, location1, location2, location3


@pytest.fixture
def sample_storage_bin():
    """Factory fixture for storage bin test data.

    Returns a dictionary that can be used to create a StorageBin instance.
    No PostGIS geometry required (bins inherit location from parent).

    Usage:
        from app.models.storage_bin import StorageBin

        def test_storage_bin_creation(sample_storage_bin):
            bin_obj = StorageBin(**sample_storage_bin)
            assert bin_obj.code == "WH-AREA-LOC001-SEG001"
    """
    return {
        "code": "WH-AREA-LOC001-SEG001",
        "label": "Segmento 1",
        "storage_location_id": 1,  # Must be set to valid location ID in tests
        "status": "active",
        "position_metadata": {
            "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},
            "confidence": 0.92,
            "container_type": "segmento",
        },
    }


@pytest.fixture
def storage_bin_factory(db_session, storage_location_factory):
    """Factory fixture for creating multiple storage bin instances.

    Creates storage bins with realistic JSONB metadata.
    Auto-creates storage location (and area + warehouse) if not provided.

    Usage:
        @pytest.mark.asyncio
        async def test_multiple_bins(storage_bin_factory):
            bin1 = await storage_bin_factory(code="WH-AREA-LOC1-SEG001")
            bin2 = await storage_bin_factory(code="WH-AREA-LOC1-SEG002")
            assert bin1.storage_bin_id != bin2.storage_bin_id
    """
    from app.models.storage_bin import StorageBin, StorageBinStatusEnum

    async def _create_storage_bin(storage_location=None, **kwargs):
        """Create and persist a storage bin with sensible defaults."""
        # Create storage location (and area + warehouse) if not provided
        if storage_location is None:
            storage_location = await storage_location_factory()

        # Default metadata from ML segmentation
        default_metadata = {
            "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},
            "confidence": 0.85,
            "container_type": "segmento",
            "ml_model_version": "yolov11-seg-v2.3",
        }

        defaults = {
            "code": f"WH-AREA-LOC-BIN-{id(kwargs)}",  # Unique code
            "label": "Test Bin",
            "storage_location_id": storage_location.location_id,
            "status": StorageBinStatusEnum.active,
            "position_metadata": default_metadata,
        }

        # Merge user-provided kwargs
        defaults.update(kwargs)

        bin_obj = StorageBin(**defaults)
        db_session.add(bin_obj)
        await db_session.commit()
        await db_session.refresh(bin_obj)

        return bin_obj

    return _create_storage_bin


# Alias: Some tests use 'session' instead of 'db_session'
@pytest_asyncio.fixture(scope="function")
async def session(db_session):
    """Alias for db_session fixture - allows tests to use either name."""
    return db_session


@pytest.fixture
async def sample_storage_bins(db_session, storage_location_factory):
    """Create storage location + 3 storage bins for testing hierarchical queries.

    Returns:
        tuple: (storage_location, bin1, bin2, bin3)

    Usage:
        @pytest.mark.asyncio
        async def test_multiple_bins(sample_storage_bins):
            location, bin1, bin2, bin3 = sample_storage_bins
            assert bin1.storage_location_id == location.location_id
            assert len(location.storage_bins) == 3
    """
    from app.models.storage_bin import StorageBin, StorageBinStatusEnum

    # Create storage location
    location = await storage_location_factory(code="WH-SAMPLE-LOC")

    # Create Bin 1 (high confidence segmento)
    bin1 = StorageBin(
        code="WH-SAMPLE-LOC-SEG001",
        label="Segmento 1",
        storage_location_id=location.location_id,
        status=StorageBinStatusEnum.active,
        position_metadata={
            "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},
            "confidence": 0.95,
            "container_type": "segmento",
        },
    )

    # Create Bin 2 (medium confidence segmento)
    bin2 = StorageBin(
        code="WH-SAMPLE-LOC-SEG002",
        label="Segmento 2",
        storage_location_id=location.location_id,
        status=StorageBinStatusEnum.active,
        position_metadata={
            "bbox": {"x": 400, "y": 200, "width": 300, "height": 150},
            "confidence": 0.82,
            "container_type": "segmento",
        },
    )

    # Create Bin 3 (cajon)
    bin3 = StorageBin(
        code="WH-SAMPLE-LOC-CAJ01",
        label="Cajon 1",
        storage_location_id=location.location_id,
        status=StorageBinStatusEnum.active,
        position_metadata={
            "bbox": {"x": 700, "y": 200, "width": 400, "height": 200},
            "confidence": 0.88,
            "container_type": "cajon",
        },
    )

    db_session.add_all([bin1, bin2, bin3])
    await db_session.commit()
    await db_session.refresh(bin1)
    await db_session.refresh(bin2)
    await db_session.refresh(bin3)

    return location, bin1, bin2, bin3


# =============================================================================
# Product & Category Factories
# =============================================================================


@pytest.fixture
def product_category_factory(db_session):
    """Factory for creating ProductCategory instances.

    Usage:
        category = await product_category_factory(code="CACTUS", name="Cacti")
    """
    from app.models.product_category import ProductCategory

    async def _create(**kwargs):
        defaults = {
            "code": kwargs.pop("code", "TEST-CAT"),
            "name": kwargs.pop("name", "Test Category"),
            "description": kwargs.pop("description", "Test category description"),
        }
        defaults.update(kwargs)

        category = ProductCategory(**defaults)
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        return category

    return _create


@pytest.fixture
def product_family_factory(db_session, product_category_factory):
    """Factory for creating ProductFamily instances.

    Usage:
        family = await product_family_factory(category_id=1, name="Echeveria")
    """
    from app.models.product_family import ProductFamily

    async def _create(**kwargs):
        # If category_id not provided, create a category first
        if "category_id" not in kwargs:
            category = await product_category_factory()
            kwargs["category_id"] = category.category_id

        defaults = {
            "name": kwargs.pop("name", "Test Family"),
            "scientific_name": kwargs.pop("scientific_name", "Test scientific name"),
            "description": kwargs.pop("description", "Test family description"),
        }
        defaults.update(kwargs)

        family = ProductFamily(**defaults)
        db_session.add(family)
        await db_session.commit()
        await db_session.refresh(family)
        return family

    return _create


@pytest.fixture
def product_factory(db_session, product_family_factory):
    """Factory for creating Product instances.

    Usage:
        product = await product_factory(sku="TEST-001", common_name="Test Plant")
    """
    from app.models.product import Product

    async def _create(**kwargs):
        # If family_id not provided, create a family first
        if "family_id" not in kwargs:
            family = await product_family_factory()
            kwargs["family_id"] = family.family_id

        defaults = {
            "sku": kwargs.pop("sku", "TEST-SKU-001"),
            "common_name": kwargs.pop("common_name", "Test Product"),
            "scientific_name": kwargs.pop("scientific_name", None),
            "description": kwargs.pop("description", "Test product description"),
            "custom_attributes": kwargs.pop("custom_attributes", {}),
        }
        defaults.update(kwargs)

        product = Product(**defaults)
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    return _create


@pytest.fixture
def user_factory(db_session):
    """Factory for creating User instances.

    Usage:
        user = await user_factory(email="test@example.com", first_name="John")
    """
    from bcrypt import gensalt, hashpw  # type: ignore[import-not-found]

    from app.models.user import User, UserRoleEnum

    async def _create(**kwargs):
        # Generate a valid bcrypt hash for password
        password = kwargs.pop("password", "test_password_123")
        password_hash = hashpw(password.encode("utf-8"), gensalt(rounds=12)).decode("utf-8")

        defaults = {
            "email": kwargs.pop(
                "email", f"test{db_session.info.get('_user_counter', 0)}@demeter.ai"
            ),
            "password_hash": password_hash,
            "first_name": kwargs.pop("first_name", "Test"),
            "last_name": kwargs.pop("last_name", "User"),
            "role": kwargs.pop("role", UserRoleEnum.WORKER),
            "active": kwargs.pop("active", True),
        }

        # Update user counter
        if "_user_counter" not in db_session.info:
            db_session.info["_user_counter"] = 0
        db_session.info["_user_counter"] += 1

        defaults.update(kwargs)

        user = User(**defaults)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create


@pytest.fixture
def product_size_factory(db_session):
    """Factory for creating ProductSize instances.

    Note: ProductSizes are usually seeded in database migrations.
    Use this factory to create additional test sizes if needed.

    Usage:
        size = await product_size_factory(code="XL", name="Extra Large")
    """
    from app.models.product_size import ProductSize

    async def _create(**kwargs):
        defaults = {
            "code": kwargs.pop("code", "TESTSIZE"),
            "name": kwargs.pop("name", "Test Size"),
            "description": kwargs.pop("description", "Test size description"),
            "min_height_cm": kwargs.pop("min_height_cm", None),
            "max_height_cm": kwargs.pop("max_height_cm", None),
            "sort_order": kwargs.pop("sort_order", 99),
        }
        defaults.update(kwargs)

        size = ProductSize(**defaults)
        db_session.add(size)
        await db_session.commit()
        await db_session.refresh(size)
        return size

    return _create


@pytest.fixture
def product_state_factory(db_session):
    """Factory for creating ProductState instances.

    Note: ProductStates are usually seeded in database migrations.
    Use this factory to create additional test states if needed.

    Usage:
        state = await product_state_factory(code="TESTSTATE", name="Test State")
    """
    from app.models.product_state import ProductState

    async def _create(**kwargs):
        defaults = {
            "code": kwargs.pop("code", "TESTSTATE"),
            "name": kwargs.pop("name", "Test State"),
            "description": kwargs.pop("description", "Test state description"),
            "is_sellable": kwargs.pop("is_sellable", False),
            "sort_order": kwargs.pop("sort_order", 99),
        }
        defaults.update(kwargs)

        state = ProductState(**defaults)
        db_session.add(state)
        await db_session.commit()
        await db_session.refresh(state)
        return state

    return _create


# =============================================================================
# SQL Fixtures (Realistic Test Data)
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def sql_fixtures(db_session):
    """Load realistic test data using ORM models (single transaction).

    This fixture creates pre-configured test data including:
    - 1 warehouse (greenhouse in Buenos Aires)
    - 1 storage_area (North section)
    - 1 storage_location (Mesa Norte A1)
    - 1 storage_bin (Segment 001)
    - Product taxonomy: 1 category, 1 family, 1 product (Echeveria 'Lola')
    - Packaging: 1 type, 1 material, 1 color, 1 catalog item (8cm black pot)
    - 1 user (admin)
    - Product states: semilla, plantula, crecimiento, venta (SEED DATA)
    - Product sizes: XS, S, M, L, XL (SEED DATA)
    - Storage bin types: SEGMENT_STANDARD, PLUG_TRAY_288

    Key Advantages over SQL:
        - Uses ORM models (type-safe, no SQL injection)
        - Single transaction (visible to test, auto-rollback)
        - No subprocess/docker exec required
        - Easier to maintain and debug

    Usage:
        @pytest.mark.asyncio
        async def test_e2e_workflow(sql_fixtures):
            # Test code here - all fixtures are pre-loaded
            # Warehouse, area, location, bin, product, user are ready
            pass

    Note:
        - All geometries are VALID PostGIS (SRID 4326)
        - All FKs are satisfied
        - Data is REALISTIC (Buenos Aires coordinates)
        - Data is CLEANED UP after each test (db_session rollback)
    """
    from datetime import datetime

    from geoalchemy2 import WKTElement

    from app.models.packaging_catalog import PackagingCatalog
    from app.models.packaging_color import PackagingColor
    from app.models.packaging_material import PackagingMaterial
    from app.models.packaging_type import PackagingType
    from app.models.product import Product
    from app.models.product_category import ProductCategory
    from app.models.product_family import ProductFamily
    from app.models.product_size import ProductSize
    from app.models.product_state import ProductState
    from app.models.storage_area import StorageArea
    from app.models.storage_bin import StorageBin
    from app.models.storage_bin_type import StorageBinType
    from app.models.storage_location import StorageLocation
    from app.models.storage_location_config import StorageLocationConfig

    # Import ALL models needed
    from app.models.user import User
    from app.models.warehouse import Warehouse, WarehouseTypeEnum

    # =========================================================================
    # 1. USER (DB028) - Required for stock_movements.user_id
    # =========================================================================
    user = User(
        email="admin@demeter.ai",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6",  # 'test_password_123'
        first_name="System",
        last_name="Administrator",
        role="admin",
        active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.flush()

    # =========================================================================
    # 2. PRODUCT STATES (DB019) - SEED DATA
    # =========================================================================
    states = [
        ProductState(
            code="SEMILLA",
            name="Semilla",
            description="Etapa de semilla (pre-germinación)",
            is_sellable=False,
            sort_order=1,
        ),
        ProductState(
            code="PLANTULA",
            name="Plántula",
            description="Etapa de plántula (post-germinación, pre-transplante)",
            is_sellable=False,
            sort_order=2,
        ),
        ProductState(
            code="CRECIMIENTO",
            name="Crecimiento",
            description="Etapa de crecimiento vegetativo",
            is_sellable=False,
            sort_order=3,
        ),
        ProductState(
            code="VENTA",
            name="Listo para venta",
            description="Producto terminado en condiciones de venta",
            is_sellable=True,
            sort_order=4,
        ),
    ]
    for state in states:
        db_session.add(state)
    await db_session.flush()

    # =========================================================================
    # 3. PRODUCT SIZES (DB018) - SEED DATA
    # =========================================================================
    # NOTE: Codes must be 3-50 chars per ProductSize validator
    sizes = [
        ProductSize(
            code="SIZE_XS",
            name="Extra Small",
            description="Altura 0-5 cm",
            min_height_cm=0,
            max_height_cm=5,
            sort_order=1,
        ),
        ProductSize(
            code="SIZE_S",
            name="Small",
            description="Altura 5-10 cm",
            min_height_cm=5,
            max_height_cm=10,
            sort_order=2,
        ),
        ProductSize(
            code="SIZE_M",
            name="Medium",
            description="Altura 10-20 cm",
            min_height_cm=10,
            max_height_cm=20,
            sort_order=3,
        ),
        ProductSize(
            code="SIZE_L",
            name="Large",
            description="Altura 20-40 cm",
            min_height_cm=20,
            max_height_cm=40,
            sort_order=4,
        ),
        ProductSize(
            code="SIZE_XL",
            name="Extra Large",
            description="Altura 40+ cm",
            min_height_cm=40,
            max_height_cm=None,
            sort_order=5,
        ),
    ]
    for size in sizes:
        db_session.add(size)
    await db_session.flush()

    # =========================================================================
    # 4. WAREHOUSE (DB001) - Greenhouse in Buenos Aires
    # =========================================================================
    # PostGIS POLYGON: 100m x 50m rectangular greenhouse in Palermo, Buenos Aires
    # Coordinates: WGS84 (SRID 4326)
    warehouse_wkt = """POLYGON((
        -58.42000 -34.57500,
        -58.41900 -34.57500,
        -58.41900 -34.57550,
        -58.42000 -34.57550,
        -58.42000 -34.57500
    ))"""

    warehouse = Warehouse(
        code="GH-BA-001",
        name="Greenhouse Buenos Aires - Palermo",
        warehouse_type=WarehouseTypeEnum.GREENHOUSE,  # Use enum, not string
        geojson_coordinates=WKTElement(warehouse_wkt, srid=4326),
        active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(warehouse)
    await db_session.flush()

    # =========================================================================
    # 5. STORAGE AREA (DB002) - North section INSIDE warehouse
    # =========================================================================
    # PostGIS POLYGON: 50m x 25m area INSIDE warehouse bounds
    area_wkt = """POLYGON((
        -58.41980 -34.57510,
        -58.41950 -34.57510,
        -58.41950 -34.57530,
        -58.41980 -34.57530,
        -58.41980 -34.57510
    ))"""

    storage_area = StorageArea(
        warehouse_id=warehouse.warehouse_id,
        code="GH-BA-001-NORTH",
        name="North Propagation Zone",
        position="N",
        geojson_coordinates=WKTElement(area_wkt, srid=4326),
        active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(storage_area)
    await db_session.flush()

    # =========================================================================
    # 6. STORAGE LOCATION (DB003) - Mesa Norte A1 (POINT geometry)
    # =========================================================================
    # PostGIS POINT: Center of storage area
    # NOTE: StorageLocation uses 'coordinates' field, not 'geojson_coordinates'
    location_wkt = "POINT(-58.41965 -34.57520)"

    storage_location = StorageLocation(
        storage_area_id=storage_area.storage_area_id,
        code="GH-BA-001-NORTH-A1",
        name="Mesa Norte A1",
        qr_code="QR-MESA-A1",
        coordinates=WKTElement(location_wkt, srid=4326),  # 'coordinates', not 'geojson_coordinates'
        active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(storage_location)
    await db_session.flush()

    # =========================================================================
    # 7. STORAGE BIN TYPES (DB005) - Reference data
    # =========================================================================
    bin_types = [
        StorageBinType(
            code="SEGMENT_STANDARD",
            name="Individual Segment",
            category="segment",
            description="Individual segment detected by ML (no fixed dimensions)",
            rows=None,
            columns=None,
            capacity=None,
            is_grid=False,
            created_at=datetime.now(UTC),
        ),
        StorageBinType(
            code="PLUG_TRAY_288",
            name="288-Cell Plug Tray",
            category="plug",
            description="Standard 288-cell plug tray (18 rows × 16 columns)",
            rows=18,
            columns=16,
            capacity=288,
            is_grid=True,
            created_at=datetime.now(UTC),
        ),
    ]
    for bin_type in bin_types:
        db_session.add(bin_type)
    await db_session.flush()

    # =========================================================================
    # 8. STORAGE BIN (DB004) - Segment 001 with ML metadata
    # =========================================================================
    segment_bin_type = [bt for bt in bin_types if bt.code == "SEGMENT_STANDARD"][0]

    storage_bin = StorageBin(
        storage_location_id=storage_location.location_id,
        storage_bin_type_id=segment_bin_type.bin_type_id,
        code="GH-BA-001-NORTH-A1-SEG001",
        label="Segment 001",
        description="Segment detected by ML segmentation pipeline",
        position_metadata={
            "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},
            "confidence": 0.92,
            "container_type": "segmento",
            "ml_model_version": "yolov11-seg-v2.3",
            "detected_at": datetime.now(UTC).isoformat(),
        },
        status="active",
        created_at=datetime.now(UTC),
    )
    db_session.add(storage_bin)
    await db_session.flush()

    # =========================================================================
    # 9. PRODUCT CATEGORY (DB015) - Succulent category
    # =========================================================================
    product_category = ProductCategory(
        code="SUCCULENT",
        name="Suculentas",
        description="Plantas suculentas (cactáceas, crasuláceas, etc.)",
    )
    db_session.add(product_category)
    await db_session.flush()

    # =========================================================================
    # 10. PRODUCT FAMILY (DB016) - Echeveria family
    # =========================================================================
    product_family = ProductFamily(
        category_id=product_category.id,  # ProductCategory uses 'id', not 'category_id'
        name="Echeveria",
        scientific_name="Echeveria sp.",
        description="Género de suculentas con rosetas compactas (Familia Crassulaceae)",
    )
    db_session.add(product_family)
    await db_session.flush()

    # =========================================================================
    # 11. PRODUCT (DB017) - Echeveria 'Lola'
    # =========================================================================
    product = Product(
        family_id=product_family.family_id,
        sku="ECHEV-LOLA-001",
        common_name="Echeveria 'Lola'",
        scientific_name="Echeveria lilacina × Echeveria derenbergii",
        description="Suculenta roseta compacta con hojas azul-grisáceas",
        custom_attributes={
            "color": "blue-gray",
            "variegation": False,
            "growth_rate": "slow",
            "bloom_season": "spring",
            "cold_hardy": False,
        },
    )
    db_session.add(product)
    await db_session.flush()

    # =========================================================================
    # 12. PACKAGING TYPE (DB009) - Pot type
    # =========================================================================
    packaging_type = PackagingType(
        code="POT", name="Maceta", description="Maceta plástica redonda estándar"
    )
    db_session.add(packaging_type)
    await db_session.flush()

    # =========================================================================
    # 13. PACKAGING MATERIAL (DB021) - Plastic material
    # =========================================================================
    packaging_material = PackagingMaterial(
        code="PLASTIC", name="Plástico", description="Material plástico estándar (polipropileno)"
    )
    db_session.add(packaging_material)
    await db_session.flush()

    # =========================================================================
    # 14. PACKAGING COLOR (DB010) - Black color
    # =========================================================================
    packaging_color = PackagingColor(name="Black", hex_code="#000000")
    db_session.add(packaging_color)
    await db_session.flush()

    # =========================================================================
    # 15. PACKAGING CATALOG (DB022) - 8cm black plastic pot
    # =========================================================================
    packaging_catalog = PackagingCatalog(
        packaging_type_id=packaging_type.id,  # PackagingType uses 'id'
        packaging_material_id=packaging_material.id,  # PackagingMaterial uses 'id'
        packaging_color_id=packaging_color.id,  # PackagingColor uses 'id'
        sku="POT-8CM-BLACK",
        name="Maceta 8cm negra",
        volume_liters=0.25,
        diameter_cm=8.0,
        height_cm=8.0,
    )
    db_session.add(packaging_catalog)
    await db_session.flush()

    # =========================================================================
    # 16. STORAGE LOCATION CONFIG (DB024) - Expected product configuration
    # =========================================================================
    crecimiento_state = [s for s in states if s.code == "CRECIMIENTO"][0]

    storage_location_config = StorageLocationConfig(
        storage_location_id=storage_location.location_id,
        product_id=product.product_id,  # Product Python attr is 'product_id' (DB column is 'id')
        packaging_catalog_id=packaging_catalog.id,  # PackagingCatalog uses 'id'
        expected_product_state_id=crecimiento_state.product_state_id,  # ProductState uses 'product_state_id'
        area_cm2=500.00,  # 500 cm² available area
        active=True,
        notes="Configuration for Echeveria Lola in 8cm pots (growth stage)",
        created_at=datetime.now(UTC),
    )
    db_session.add(storage_location_config)
    await db_session.flush()

    logger.info(
        "ORM fixtures created",
        warehouses=1,
        storage_areas=1,
        storage_locations=1,
        storage_bins=1,
        products=1,
        users=1,
        packaging_items=4,
        states=4,
        sizes=5,
        bin_types=2,
    )

    # Yield to test - all data is visible in the same transaction
    yield

    # Cleanup happens automatically via db_session rollback


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings for testing.

    Usage:
        def test_with_debug_mode(mock_settings):
            mock_settings("DEBUG", "true")
            assert settings.debug is True
    """

    def _set_setting(key: str, value: str):
        monkeypatch.setenv(key, value)
        # Force settings reload (if using pydantic-settings)
        settings.__dict__[key.lower()] = value

    return _set_setting


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_addoption(parser):
    """Add custom command-line options for pytest.

    Usage:
        # Run with PostgreSQL test database (default)
        pytest

        # Override with custom database URL
        pytest --db-url="postgresql+asyncpg://user:pass@localhost/test_db"
    """
    parser.addoption(
        "--db-url",
        action="store",
        default=None,
        help="Database URL for testing (default: PostgreSQL from TEST_DATABASE_URL)",
    )


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Markers are already defined in pyproject.toml
    # Store db_url in config for access in tests (override TEST_DATABASE_URL if provided)
    config.db_url = config.getoption("--db-url") or TEST_DATABASE_URL

    # Log database configuration
    logger.info(
        "Test database configured",
        database_type="PostgreSQL + PostGIS",
        database_url=config.db_url.replace("demeter_test_password", "***"),
        test_scope="unit + integration",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location.

    Automatically adds markers based on test file location:
    - tests/unit/* → @pytest.mark.unit
    - tests/integration/* → @pytest.mark.integration
    """
    for item in items:
        # Add unit marker to all tests in tests/unit/
        if "tests/unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker to all tests in tests/integration/
        if "tests/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark async tests
        if pytest_asyncio.is_async_test(item):
            item.add_marker(pytest.mark.asyncio)
