"""E2E tests for SQL fixtures - Validates Flujo Principal V3 data setup.

This test file demonstrates how to use the sql_fixtures fixture for E2E testing
of the Flujo Principal V3 (Photo Upload → ML Processing → Stock Initialization).

Test Strategy:
    - Use sql_fixtures to load realistic test data
    - Verify all relationships are intact
    - Validate PostGIS geometries
    - Check all FKs are satisfied
    - Confirm data is ready for E2E workflow tests

Author: Python Expert (DemeterAI Team)
Date: 2025-10-22
"""

import pytest
from sqlalchemy import select, text

from app.models.packaging_catalog import PackagingCatalog
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
from app.models.user import User
from app.models.warehouse import Warehouse


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_load_successfully(sql_fixtures, db_session):
    """Verify SQL fixtures load all expected data."""
    # Verify warehouse
    result = await db_session.execute(select(Warehouse).where(Warehouse.code == "GH-BA-001"))
    warehouse = result.scalar_one_or_none()
    assert warehouse is not None, "Warehouse not loaded"
    assert warehouse.name == "Greenhouse Buenos Aires - Palermo"
    assert warehouse.warehouse_type.value == "greenhouse"
    assert warehouse.active is True

    # Verify storage area
    result = await db_session.execute(
        select(StorageArea).where(StorageArea.code == "GH-BA-001-NORTH")
    )
    area = result.scalar_one_or_none()
    assert area is not None, "StorageArea not loaded"
    assert area.name == "North Propagation Zone"
    assert area.warehouse_id == warehouse.warehouse_id

    # Verify storage location
    result = await db_session.execute(
        select(StorageLocation).where(StorageLocation.code == "GH-BA-001-NORTH-A1")
    )
    location = result.scalar_one_or_none()
    assert location is not None, "StorageLocation not loaded"
    assert location.name == "Mesa Norte A1"
    assert location.qr_code == "QR-MESA-A1"
    assert location.storage_area_id == area.storage_area_id

    # Verify storage bin
    result = await db_session.execute(
        select(StorageBin).where(StorageBin.code == "GH-BA-001-NORTH-A1-SEG001")
    )
    bin_obj = result.scalar_one_or_none()
    assert bin_obj is not None, "StorageBin not loaded"
    assert bin_obj.label == "Segment 001"
    assert bin_obj.status.value == "active"
    assert bin_obj.storage_location_id == location.location_id
    assert bin_obj.position_metadata is not None
    assert bin_obj.position_metadata["confidence"] == 0.92

    # Verify product
    result = await db_session.execute(select(Product).where(Product.sku == "ECHEV-LOLA-001"))
    product = result.scalar_one_or_none()
    assert product is not None, "Product not loaded"
    assert product.common_name == "Echeveria 'Lola'"
    assert product.custom_attributes["color"] == "blue-gray"

    # Verify user
    result = await db_session.execute(select(User).where(User.email == "admin@demeter.ai"))
    user = result.scalar_one_or_none()
    assert user is not None, "User not loaded"
    assert user.first_name == "System"
    assert user.last_name == "Administrator"
    assert user.role == "admin"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_postgis_geometries_valid(sql_fixtures, db_session):
    """Verify all PostGIS geometries are valid and have correct types."""
    # Warehouse geometry (POLYGON)
    result = await db_session.execute(
        text(
            """
        SELECT
            code,
            ST_IsValid(geojson_coordinates) AS is_valid,
            ST_GeometryType(geojson_coordinates) AS geom_type,
            ST_SRID(geojson_coordinates) AS srid
        FROM warehouses
        WHERE code = 'GH-BA-001'
    """
        )
    )
    row = result.fetchone()
    assert row is not None
    code, is_valid, geom_type, srid = row
    assert is_valid is True, f"Invalid warehouse geometry: {code}"
    assert geom_type == "ST_Polygon", f"Wrong warehouse geometry type: {geom_type}"
    assert srid == 4326, f"Wrong SRID: {srid}"

    # StorageArea geometry (POLYGON)
    result = await db_session.execute(
        text(
            """
        SELECT
            code,
            ST_IsValid(geojson_coordinates) AS is_valid,
            ST_GeometryType(geojson_coordinates) AS geom_type,
            ST_SRID(geojson_coordinates) AS srid
        FROM storage_areas
        WHERE code = 'GH-BA-001-NORTH'
    """
        )
    )
    row = result.fetchone()
    assert row is not None
    code, is_valid, geom_type, srid = row
    assert is_valid is True, f"Invalid area geometry: {code}"
    assert geom_type == "ST_Polygon", f"Wrong area geometry type: {geom_type}"
    assert srid == 4326, f"Wrong SRID: {srid}"

    # StorageLocation geometry (POINT)
    # NOTE: StorageLocation uses 'coordinates' field, not 'geojson_coordinates'
    result = await db_session.execute(
        text(
            """
        SELECT
            code,
            ST_IsValid(coordinates) AS is_valid,
            ST_GeometryType(coordinates) AS geom_type,
            ST_SRID(coordinates) AS srid
        FROM storage_locations
        WHERE code = 'GH-BA-001-NORTH-A1'
    """
        )
    )
    row = result.fetchone()
    assert row is not None
    code, is_valid, geom_type, srid = row
    assert is_valid is True, f"Invalid location geometry: {code}"
    assert geom_type == "ST_Point", f"Wrong location geometry type: {geom_type}"
    assert srid == 4326, f"Wrong SRID: {srid}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_generated_columns(sql_fixtures, db_session):
    """Verify GENERATED columns (area_m2, centroid) are populated."""
    # Warehouse: area_m2 should be > 0, centroid should exist
    result = await db_session.execute(
        text(
            """
        SELECT code, area_m2, ST_AsText(centroid) AS centroid_wkt
        FROM warehouses
        WHERE code = 'GH-BA-001'
    """
        )
    )
    row = result.fetchone()
    assert row is not None
    code, area_m2, centroid_wkt = row
    assert area_m2 is not None, f"GENERATED area_m2 is NULL for warehouse {code}"
    assert area_m2 > 0, f"GENERATED area_m2 is 0 for warehouse {code}"
    assert centroid_wkt is not None, f"GENERATED centroid is NULL for warehouse {code}"
    assert centroid_wkt.startswith("POINT("), f"Centroid is not a POINT: {centroid_wkt}"

    # StorageArea: area_m2 should be > 0, centroid should exist
    result = await db_session.execute(
        text(
            """
        SELECT code, area_m2, ST_AsText(centroid) AS centroid_wkt
        FROM storage_areas
        WHERE code = 'GH-BA-001-NORTH'
    """
        )
    )
    row = result.fetchone()
    assert row is not None
    code, area_m2, centroid_wkt = row
    assert area_m2 is not None, f"GENERATED area_m2 is NULL for area {code}"
    assert area_m2 > 0, f"GENERATED area_m2 is 0 for area {code}"
    assert centroid_wkt is not None, f"GENERATED centroid is NULL for area {code}"

    # StorageLocation: area_m2 = 0 (POINT has no area), centroid = coordinates
    result = await db_session.execute(
        text(
            """
        SELECT code, area_m2, ST_AsText(centroid) AS centroid_wkt
        FROM storage_locations
        WHERE code = 'GH-BA-001-NORTH-A1'
    """
        )
    )
    row = result.fetchone()
    assert row is not None
    code, area_m2, centroid_wkt = row
    # Note: area_m2 is GENERATED as 0 for storage_locations (POINT has no area)
    assert area_m2 == 0, f"GENERATED area_m2 should be 0 for location {code} (POINT geometry)"
    assert centroid_wkt is not None, f"GENERATED centroid is NULL for location {code}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_foreign_keys_satisfied(sql_fixtures, db_session):
    """Verify all foreign keys are satisfied (referential integrity)."""
    # Verify storage_area.warehouse_id → warehouses.warehouse_id
    result = await db_session.execute(
        text(
            """
        SELECT sa.code, sa.warehouse_id, w.warehouse_id
        FROM storage_areas sa
        JOIN warehouses w ON sa.warehouse_id = w.warehouse_id
        WHERE sa.code = 'GH-BA-001-NORTH'
    """
        )
    )
    row = result.fetchone()
    assert row is not None, "StorageArea FK to Warehouse not satisfied"

    # Verify storage_location.storage_area_id → storage_areas.storage_area_id
    result = await db_session.execute(
        text(
            """
        SELECT sl.code, sl.storage_area_id, sa.storage_area_id
        FROM storage_locations sl
        JOIN storage_areas sa ON sl.storage_area_id = sa.storage_area_id
        WHERE sl.code = 'GH-BA-001-NORTH-A1'
    """
        )
    )
    row = result.fetchone()
    assert row is not None, "StorageLocation FK to StorageArea not satisfied"

    # Verify storage_bin.storage_location_id → storage_locations.location_id
    result = await db_session.execute(
        text(
            """
        SELECT sb.code, sb.storage_location_id, sl.location_id
        FROM storage_bins sb
        JOIN storage_locations sl ON sb.storage_location_id = sl.location_id
        WHERE sb.code = 'GH-BA-001-NORTH-A1-SEG001'
    """
        )
    )
    row = result.fetchone()
    assert row is not None, "StorageBin FK to StorageLocation not satisfied"

    # Verify product.family_id → product_families.family_id
    result = await db_session.execute(
        text(
            """
        SELECT p.sku, p.family_id, pf.family_id
        FROM products p
        JOIN product_families pf ON p.family_id = pf.family_id
        WHERE p.sku = 'ECHEV-LOLA-001'
    """
        )
    )
    row = result.fetchone()
    assert row is not None, "Product FK to ProductFamily not satisfied"

    # Verify product_family.category_id → product_categories.category_id
    result = await db_session.execute(
        text(
            """
        SELECT pf.name, pf.category_id, pc.category_id
        FROM product_families pf
        JOIN product_categories pc ON pf.category_id = pc.category_id
        WHERE pf.name = 'Echeveria'
    """
        )
    )
    row = result.fetchone()
    assert row is not None, "ProductFamily FK to ProductCategory not satisfied"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_seed_data_loaded(sql_fixtures, db_session):
    """Verify seed data (product_states, product_sizes) is loaded."""
    # Verify product_states (4 states)
    result = await db_session.execute(select(ProductState))
    states = result.scalars().all()
    assert len(states) >= 4, f"Expected at least 4 product_states, got {len(states)}"
    state_codes = {s.code for s in states}
    assert "SEMILLA" in state_codes
    assert "PLANTULA" in state_codes
    assert "CRECIMIENTO" in state_codes
    assert "VENTA" in state_codes

    # Verify product_sizes (5 sizes)
    # NOTE: Codes changed to SIZE_XS, SIZE_S, etc. (3+ chars per validator)
    result = await db_session.execute(select(ProductSize))
    sizes = result.scalars().all()
    assert len(sizes) >= 5, f"Expected at least 5 product_sizes, got {len(sizes)}"
    size_codes = {s.code for s in sizes}
    assert "SIZE_XS" in size_codes
    assert "SIZE_S" in size_codes
    assert "SIZE_M" in size_codes
    assert "SIZE_L" in size_codes
    assert "SIZE_XL" in size_codes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_storage_location_config(sql_fixtures, db_session):
    """Verify StorageLocationConfig links location → product → packaging → state."""
    result = await db_session.execute(
        select(StorageLocationConfig)
        .join(StorageLocation)
        .join(Product)
        .join(PackagingCatalog)
        .join(ProductState)
        .where(StorageLocation.code == "GH-BA-001-NORTH-A1")
    )
    config = result.scalar_one_or_none()
    assert config is not None, "StorageLocationConfig not loaded"
    assert config.active is True
    assert config.area_cm2 == 500.00

    # Verify relationships
    assert config.storage_location.code == "GH-BA-001-NORTH-A1"
    assert config.product.sku == "ECHEV-LOLA-001"
    assert config.packaging_catalog.sku == "POT-8CM-BLACK"
    assert config.expected_product_state.code == "CRECIMIENTO"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_relationships_work(sql_fixtures, db_session):
    """Verify SQLAlchemy relationships work correctly."""
    # Load warehouse with relationships
    result = await db_session.execute(
        select(Warehouse)
        .where(Warehouse.code == "GH-BA-001")
        .options(select(StorageArea).where(StorageArea.warehouse_id == Warehouse.warehouse_id))
    )
    warehouse = result.scalar_one_or_none()
    assert warehouse is not None

    # Access storage_areas relationship
    result = await db_session.execute(
        select(StorageArea).where(StorageArea.warehouse_id == warehouse.warehouse_id)
    )
    areas = result.scalars().all()
    assert len(areas) >= 1, "Warehouse should have at least 1 storage_area"
    assert any(a.code == "GH-BA-001-NORTH" for a in areas)

    # Load product with family → category chain
    result = await db_session.execute(select(Product).where(Product.sku == "ECHEV-LOLA-001"))
    product = result.scalar_one_or_none()
    assert product is not None

    # Access family relationship
    result = await db_session.execute(
        select(ProductFamily).where(ProductFamily.family_id == product.family_id)
    )
    family = result.scalar_one_or_none()
    assert family is not None
    assert family.name == "Echeveria"

    # Access category relationship
    result = await db_session.execute(
        select(ProductCategory).where(ProductCategory.category_id == family.category_id)
    )
    category = result.scalar_one_or_none()
    assert category is not None
    assert category.code == "SUCCULENT"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sql_fixtures_bin_type_configuration(sql_fixtures, db_session):
    """Verify StorageBinType fixtures (SEGMENT_STANDARD, PLUG_TRAY_288)."""
    # SEGMENT_STANDARD (non-grid)
    result = await db_session.execute(
        select(StorageBinType).where(StorageBinType.code == "SEGMENT_STANDARD")
    )
    segment = result.scalar_one_or_none()
    assert segment is not None
    assert segment.category.value == "segment"
    assert segment.is_grid is False
    assert segment.rows is None
    assert segment.columns is None

    # PLUG_TRAY_288 (grid)
    result = await db_session.execute(
        select(StorageBinType).where(StorageBinType.code == "PLUG_TRAY_288")
    )
    plug = result.scalar_one_or_none()
    assert plug is not None
    assert plug.category.value == "plug"
    assert plug.is_grid is True
    assert plug.rows == 18
    assert plug.columns == 16
    assert plug.capacity == 288
