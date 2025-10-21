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

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app

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
                ALTER TABLE warehouses ADD COLUMN area_m2 NUMERIC(10,2)
                GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
            """)
            )
        except Exception:
            pass  # Column conversion failed, but tests can still run

        try:
            # Warehouses: centroid trigger function
            await conn.execute(
                text("""
                CREATE OR REPLACE FUNCTION update_warehouse_centroid()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.centroid = ST_Centroid(NEW.geojson_coordinates);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            )
            # Create trigger
            await conn.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS trg_warehouse_centroid
                BEFORE INSERT OR UPDATE OF geojson_coordinates ON warehouses
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
                ADD COLUMN area_m2 NUMERIC(10,2)
                GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
            """)
            )
        except Exception:
            pass

        try:
            # StorageAreas: centroid trigger function
            await conn.execute(
                text("""
                CREATE OR REPLACE FUNCTION update_storage_area_centroid()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.centroid = ST_Centroid(NEW.geojson_coordinates);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            )
            # Create trigger
            await conn.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS trg_storage_area_centroid
                BEFORE INSERT OR UPDATE OF geojson_coordinates ON storage_areas
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
                ADD COLUMN area_m2 NUMERIC(10,2)
                GENERATED ALWAYS AS (0) STORED
            """)
            )
        except Exception:
            pass

        try:
            # StorageLocations: centroid = coordinates (for POINT geometries)
            await conn.execute(
                text("""
                CREATE OR REPLACE FUNCTION update_storage_location_centroid()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.centroid = NEW.geojson_coordinates;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            )
            # Create trigger
            await conn.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS trg_storage_location_centroid
                BEFORE INSERT OR UPDATE OF geojson_coordinates ON storage_locations
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
        coordinates=from_shape(Polygon(north_coords), srid=4326),
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
        coordinates=from_shape(Polygon(south_coords), srid=4326),
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
        coordinates=from_shape(Polygon(center_coords), srid=4326),
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
        def test_product_creation(sample_product):
            product = Product(**sample_product)
            assert product.code == "PROD-TEST"
    """
    return {
        "code": "PROD-TEST",
        "name": "Test Product",
        "description": "Product for testing",
        "scientific_name": "Testus productus",
        "category": "cactus",
        "active": True,
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
        "geojson_coordinates": from_shape(point, srid=4326),
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
            "geojson_coordinates": from_shape(default_point, srid=4326),
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
        coordinates=from_shape(Point(-70.64825, -33.44925), srid=4326),
    )

    # Create Location 2 (slightly east)
    location2 = StorageLocation(
        code="WH-SAMPLE-AREA-LOC2",
        name="Storage Location 2",
        storage_area_id=area.storage_area_id,
        qr_code="LOC-SAM-02",
        coordinates=from_shape(Point(-70.64820, -33.44920), srid=4326),
    )

    # Create Location 3 (slightly west)
    location3 = StorageLocation(
        code="WH-SAMPLE-AREA-LOC3",
        name="Storage Location 3",
        storage_area_id=area.storage_area_id,
        qr_code="LOC-SAM-03",
        coordinates=from_shape(Point(-70.64830, -33.44930), srid=4326),
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

    # Show database configuration
    print("\n" + "=" * 70)
    print("USING PostgreSQL + PostGIS TEST DATABASE")
    print(f"Database URL: {config.db_url.replace('demeter_test_password', '***')}")
    print("All tests (unit + integration) will use PostgreSQL")
    print("=" * 70 + "\n")


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
