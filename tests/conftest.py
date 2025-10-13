"""Shared pytest fixtures and configuration for DemeterAI tests.

This module provides test fixtures for:
- Database session management (with automatic rollback)
- FastAPI test client (with dependency injection)
- Sample test data factories
- Test database isolation

All fixtures use async/await and are compatible with pytest-asyncio.
Tests get a fresh database state for each test function (scope="function").
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app

# =============================================================================
# Test Database Configuration
# =============================================================================

# Use test database URL from settings (or override for tests)
# Note: Until F012 (Docker), we use in-memory SQLite for tests
# SQLite in-memory database for testing (no PostgreSQL required)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

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
    1. Creates all tables in the test database
    2. Yields a session for the test to use
    3. Rolls back any changes after the test completes
    4. Drops all tables (clean slate for next test)

    Usage:
        @pytest.mark.unit
        async def test_warehouse_creation(db_session):
            warehouse = Warehouse(code="WH-001", name="Test")
            db_session.add(warehouse)
            await db_session.commit()
            assert warehouse.id is not None
    """
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
    """Factory fixture for storage area test data.

    Usage:
        def test_storage_area_creation(sample_storage_area):
            area = StorageArea(**sample_storage_area)
            assert area.code == "AREA-TEST"
    """
    return {
        "code": "AREA-TEST",
        "name": "Test Storage Area",
        "description": "Storage area for testing",
        "type": "section",
        "active": True,
    }


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
        # Run with PostgreSQL test database
        pytest --db-url="postgresql+asyncpg://user:pass@localhost/test_db"

        # Run with SQLite (default, PostGIS tests will be skipped)
        pytest --db-url="sqlite+aiosqlite:///:memory:"
    """
    parser.addoption(
        "--db-url",
        action="store",
        default="sqlite+aiosqlite:///:memory:",
        help="Database URL for testing (default: SQLite in-memory)",
    )


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Markers are already defined in pyproject.toml
    # Store db_url in config for access in tests
    config.db_url = config.getoption("--db-url")

    # Add note about PostGIS tests
    if "sqlite" in config.db_url:
        print("\n" + "=" * 70)
        print("NOTE: Using SQLite in-memory database")
        print("PostGIS integration tests will be SKIPPED")
        print("To run PostGIS tests, use:")
        print("  pytest --db-url='postgresql+asyncpg://user:pass@localhost/test_db'")
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
