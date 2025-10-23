# DemeterAI v2.0 - Test Fixtures

**Version**: 1.0
**Last Updated**: 2025-10-22
**Author**: Python Expert (DemeterAI Team)

---

## Overview

This directory contains **realistic test fixtures** for E2E testing of the **Flujo Principal V3** (Photo Upload → ML Processing → Stock Initialization).

**Problem Solved**: PostgreSQL GENERATED columns (`area_m2`) and triggers (`centroid`) prevent simple ORM inserts. These SQL fixtures bypass that limitation by using raw SQL with valid PostGIS geometries.

---

## Files

```
tests/fixtures/
├── README.md                   # This file
├── test_fixtures.sql           # SQL with realistic test data
└── load_fixtures.py            # Python script to load/cleanup fixtures
```

---

## Data Included

### Geospatial Hierarchy (4 levels)

- **1 Warehouse**: `GH-BA-001` (Greenhouse Buenos Aires - Palermo)
  - Coordinates: `-58.42, -34.575` (Buenos Aires, Argentina)
  - Type: `greenhouse`
  - Area: ~5000 m² (calculated via GENERATED column)

- **1 StorageArea**: `GH-BA-001-NORTH` (North Propagation Zone)
  - Position: `N` (North)
  - Area: ~1250 m² (calculated via GENERATED column)

- **1 StorageLocation**: `GH-BA-001-NORTH-A1` (Mesa Norte A1)
  - QR Code: `QR-MESA-A1`
  - Geometry: `POINT(-58.41965, -34.57520)`
  - Area: 0 m² (POINT geometry)

- **1 StorageBin**: `GH-BA-001-NORTH-A1-SEG001` (Segment 001)
  - Type: `SEGMENT_STANDARD`
  - Status: `active`
  - ML metadata: confidence=0.92, container_type='segmento'

### Product Catalog (3-level taxonomy)

- **1 ProductCategory**: `SUCCULENT` (Suculentas)
- **1 ProductFamily**: `Echeveria` (Echeveria sp.)
- **1 Product**: `ECHEV-LOLA-001` (Echeveria 'Lola')
  - SKU: `ECHEV-LOLA-001`
  - Common name: `Echeveria 'Lola'`
  - Scientific name: `Echeveria lilacina × Echeveria derenbergii`
  - Custom attributes: color='blue-gray', growth_rate='slow'

### Packaging

- **1 PackagingType**: `POT` (Maceta)
- **1 PackagingMaterial**: `PLASTIC` (Plástico)
- **1 PackagingColor**: `Black` (#000000)
- **1 PackagingCatalog**: `POT-8CM-BLACK` (Maceta 8cm negra)
  - Volume: 0.25 L
  - Diameter: 8 cm
  - Height: 8 cm

### Seed Data

- **4 ProductStates**: `SEMILLA`, `PLANTULA`, `CRECIMIENTO`, `VENTA`
- **5 ProductSizes**: `XS`, `S`, `M`, `L`, `XL`
- **2 StorageBinTypes**: `SEGMENT_STANDARD`, `PLUG_TRAY_288`

### Users

- **1 User**: `admin@demeter.ai`
  - Password: `test_password_123` (bcrypt hash)
  - Role: `admin`
  - Name: System Administrator

### Configuration

- **1 StorageLocationConfig**: Links `GH-BA-001-NORTH-A1` → `ECHEV-LOLA-001` → `POT-8CM-BLACK` → `CRECIMIENTO`

---

## Usage

### Option 1: pytest fixture (Recommended)

```python
# tests/integration/test_my_e2e_workflow.py
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_workflow(sql_fixtures, db_session):
    """Test E2E workflow with pre-loaded fixtures."""
    # All data is pre-loaded:
    # - Warehouse, area, location, bin
    # - Product, user, packaging
    # - Product states, sizes, bin types

    # Query warehouse
    from app.models.warehouse import Warehouse
    from sqlalchemy import select

    result = await db_session.execute(
        select(Warehouse).where(Warehouse.code == "GH-BA-001")
    )
    warehouse = result.scalar_one_or_none()
    assert warehouse is not None

    # Your E2E test logic here...
    # Data is automatically cleaned up after test (db_session rollback)
```

### Option 2: Standalone script

```bash
# Load fixtures into test database
python tests/fixtures/load_fixtures.py

# Load + verify data
python tests/fixtures/load_fixtures.py --verify

# Cleanup all test data
python tests/fixtures/load_fixtures.py --cleanup

# Load into custom database
python tests/fixtures/load_fixtures.py --db-url="postgresql+asyncpg://user:pass@localhost/db"
```

### Option 3: Raw SQL (manual)

```bash
# Via psql
psql -U demeter_test -d demeterai_test -f tests/fixtures/test_fixtures.sql

# Via docker exec
docker exec -i demeterai-db-test psql -U demeter_test -d demeterai_test < tests/fixtures/test_fixtures.sql
```

---

## Verification

### Verify fixtures loaded successfully

```bash
# Via Python script
python tests/fixtures/load_fixtures.py --verify

# Via pytest
pytest tests/integration/test_sql_fixtures_e2e.py -v
```

### Expected output

```
📂 Loading fixtures from: tests/fixtures/test_fixtures.sql
🔗 Database URL: postgresql+asyncpg://demeter_test:***@localhost:5434/demeterai_test
⏳ Executing SQL fixtures...
✅ Fixtures loaded successfully!

🔍 Verifying fixtures...

📊 Row counts:
   warehouses                       1 rows
   storage_areas                    1 rows
   storage_locations                1 rows
   storage_bins                     1 rows
   storage_bin_types                2 rows
   product_categories               1 rows
   product_families                 1 rows
   products                         1 rows
   product_states                   4 rows
   product_sizes                    5 rows
   packaging_types                  1 rows
   packaging_materials              1 rows
   packaging_colors                 1 rows
   packaging_catalog                1 rows
   users                            1 rows
   storage_location_config          1 rows

🌍 PostGIS geometry validation:
   ✅ warehouses.GH-BA-001: ST_Polygon (valid)
   ✅ storage_areas.GH-BA-001-NORTH: ST_Polygon (valid)
   ✅ storage_locations.GH-BA-001-NORTH-A1: ST_Point (valid)

📐 GENERATED columns (area_m2, centroid):
   ✅ warehouses.GH-BA-001: area_m2=5000.00, centroid=POINT(...)
   ✅ storage_areas.GH-BA-001-NORTH: area_m2=1250.00, centroid=POINT(...)
   ✅ storage_locations.GH-BA-001-NORTH-A1: area_m2=0, centroid=POINT(...)

✅ All verifications passed!
```

---

## Important Notes

### PostGIS Geometries

All geometries are **VALID PostGIS** with **SRID 4326** (WGS84):

- **Warehouses**: `POLYGON` (5-point closed polygon)
- **StorageAreas**: `POLYGON` (5-point closed polygon)
- **StorageLocations**: `POINT` (single coordinate)

### GENERATED Columns

The following columns are **GENERATED ALWAYS** by PostgreSQL:

- `warehouses.area_m2`: Auto-calculated from `geojson_coordinates::geography`
- `storage_areas.area_m2`: Auto-calculated from `geojson_coordinates::geography`
- `storage_locations.area_m2`: Hard-coded to `0` (POINT has no area)

### Triggers

The following triggers auto-populate centroid:

- `warehouses.centroid`: `ST_Centroid(geojson_coordinates)`
- `storage_areas.centroid`: `ST_Centroid(geojson_coordinates)`
- `storage_locations.centroid`: Same as `geojson_coordinates` (POINT)

### Foreign Keys

All foreign keys are **SATISFIED** (no orphaned records):

- `storage_areas.warehouse_id` → `warehouses.warehouse_id`
- `storage_locations.storage_area_id` → `storage_areas.storage_area_id`
- `storage_bins.storage_location_id` → `storage_locations.location_id`
- `storage_bins.storage_bin_type_id` → `storage_bin_types.bin_type_id`
- `products.family_id` → `product_families.family_id`
- `product_families.category_id` → `product_categories.category_id`
- `packaging_catalog.packaging_type_id` → `packaging_types.packaging_type_id`
- `packaging_catalog.packaging_material_id` → `packaging_materials.packaging_material_id`
- `packaging_catalog.packaging_color_id` → `packaging_colors.packaging_color_id`
- `storage_location_config.storage_location_id` → `storage_locations.location_id`
- `storage_location_config.product_id` → `products.id`
- `storage_location_config.packaging_catalog_id` → `packaging_catalog.packaging_catalog_id`
- `storage_location_config.expected_product_state_id` → `product_states.product_state_id`

---

## Cleanup

Fixtures are automatically cleaned up after each test (via `db_session` rollback in `tests/conftest.py`).

To manually cleanup:

```bash
# Via Python script
python tests/fixtures/load_fixtures.py --cleanup

# Via SQL (DANGEROUS - deletes ALL data!)
psql -U demeter_test -d demeterai_test -c "DELETE FROM storage_location_config; DELETE FROM storage_bins; DELETE FROM storage_locations; DELETE FROM storage_areas; DELETE FROM warehouses; DELETE FROM packaging_catalog; DELETE FROM packaging_colors; DELETE FROM packaging_materials; DELETE FROM packaging_types; DELETE FROM products; DELETE FROM product_families; DELETE FROM product_categories; DELETE FROM product_states; DELETE FROM product_sizes; DELETE FROM storage_bin_types; DELETE FROM users;"
```

---

## Troubleshooting

### Error: "Fixtures file not found"

```bash
# Verify file exists
ls -la tests/fixtures/test_fixtures.sql

# If missing, re-create from this directory
cd /home/lucasg/proyectos/DemeterDocs
python tests/fixtures/load_fixtures.py
```

### Error: "Invalid geometry"

```sql
-- Check geometry validity
SELECT code, ST_IsValid(geojson_coordinates), ST_GeometryType(geojson_coordinates)
FROM warehouses;

-- If invalid, re-run fixtures
python tests/fixtures/load_fixtures.py --cleanup
python tests/fixtures/load_fixtures.py --verify
```

### Error: "Foreign key violation"

This means fixtures were loaded in wrong order. Solution:

```bash
# Cleanup + reload
python tests/fixtures/load_fixtures.py --cleanup
python tests/fixtures/load_fixtures.py --verify
```

### Error: "Connection refused"

```bash
# Start test database
docker compose up db_test -d

# Verify connection
psql -U demeter_test -h localhost -p 5434 -d demeterai_test -c "SELECT version();"
```

---

## Next Steps

1. **Run E2E tests**: Use `sql_fixtures` fixture in your E2E tests
2. **Add more fixtures**: Extend `test_fixtures.sql` with additional scenarios
3. **Test Flujo Principal V3**: Photo upload → ML processing → Stock initialization

---

**Questions?** Contact Python Expert or Team Leader.
