-- ============================================================================
-- DemeterAI v2.0 - Test Fixtures SQL
-- ============================================================================
-- Purpose: Load realistic test data for E2E testing of Flujo Principal V3
-- Author: Python Expert (DemeterAI Team)
-- Date: 2025-10-22
--
-- IMPORTANT: This file contains VALID PostGIS geometries and respects all
-- constraints defined in database/database.mmd (28 tables)
--
-- Usage:
--   1. Via Python: python tests/fixtures/load_fixtures.py
--   2. Via psql: psql -U demeter_test -d demeterai_test -f tests/fixtures/test_fixtures.sql
--
-- Data includes:
--   - 1 warehouse (greenhouse in Buenos Aires, Argentina)
--   - 1 storage_area (North section)
--   - 1 storage_location (Mesa Norte A1)
--   - 1 storage_bin (Segment 001)
--   - Product taxonomy: 1 category, 1 family, 1 product (Echeveria 'Lola')
--   - Packaging: 1 type, 1 material, 1 color, 1 catalog item (8cm black pot)
--   - 1 user (admin)
--   - Product states: semilla, plantula, crecimiento, venta (SEED DATA)
--   - Product sizes: XS, S, M, L, XL (SEED DATA)
--   - Storage bin types: SEGMENT_STANDARD, PLUG_TRAY_288
-- ============================================================================

-- ============================================================================
-- 1. USERS (DB028) - Required for stock_movements.user_id
-- ============================================================================
INSERT INTO users (email, password_hash, first_name, last_name, role, active, created_at)
VALUES (
    'admin@demeter.ai',
    -- bcrypt hash for 'test_password_123' (cost=12)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5LE2KBfZSTNx6',
    'System',
    'Administrator',
    'admin',
    true,
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- 2. PRODUCT STATES (DB019) - SEED DATA (required for stock_batches)
-- ============================================================================
INSERT INTO product_states (code, name, description, is_sellable, sort_order)
VALUES
    ('SEMILLA', 'Semilla', 'Etapa de semilla (pre-germinación)', false, 1),
    ('PLANTULA', 'Plántula', 'Etapa de plántula (post-germinación, pre-transplante)', false, 2),
    ('CRECIMIENTO', 'Crecimiento', 'Etapa de crecimiento vegetativo', false, 3),
    ('VENTA', 'Listo para venta', 'Producto terminado en condiciones de venta', true, 4)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 3. PRODUCT SIZES (DB018) - SEED DATA (required for stock_batches)
-- ============================================================================
INSERT INTO product_sizes (code, name, description, min_height_cm, max_height_cm, sort_order)
VALUES
    ('XS', 'Extra Small', 'Altura 0-5 cm', 0, 5, 1),
    ('S', 'Small', 'Altura 5-10 cm', 5, 10, 2),
    ('M', 'Medium', 'Altura 10-20 cm', 10, 20, 3),
    ('L', 'Large', 'Altura 20-40 cm', 20, 40, 4),
    ('XL', 'Extra Large', 'Altura 40+ cm', 40, NULL, 5)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 4. WAREHOUSE (DB001) - Greenhouse in Buenos Aires, Argentina
-- ============================================================================
-- Coordinates: Palermo, Buenos Aires (realistic greenhouse location)
-- Polygon: 100m x 50m rectangular greenhouse
-- SRID: 4326 (WGS84 - GPS coordinates)
INSERT INTO warehouses (code, name, warehouse_type, geojson_coordinates, active, created_at)
VALUES (
    'GH-BA-001',
    'Greenhouse Buenos Aires - Palermo',
    'greenhouse',
    ST_GeomFromText(
        'POLYGON((
            -58.42000 -34.57500,
            -58.41900 -34.57500,
            -58.41900 -34.57550,
            -58.42000 -34.57550,
            -58.42000 -34.57500
        ))',
        4326
    ),
    true,
    NOW()
) ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 5. STORAGE AREA (DB002) - North section inside warehouse
-- ============================================================================
-- Polygon: 50m x 25m area INSIDE warehouse bounds
INSERT INTO storage_areas (warehouse_id, code, name, position, geojson_coordinates, active, created_at)
SELECT
    w.warehouse_id,
    'GH-BA-001-NORTH',
    'North Propagation Zone',
    'N',
    ST_GeomFromText(
        'POLYGON((
            -58.41980 -34.57510,
            -58.41950 -34.57510,
            -58.41950 -34.57530,
            -58.41980 -34.57530,
            -58.41980 -34.57510
        ))',
        4326
    ),
    true,
    NOW()
FROM warehouses w
WHERE w.code = 'GH-BA-001'
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 6. STORAGE LOCATION (DB003) - Mesa Norte A1 (POINT geometry)
-- ============================================================================
-- Point: Center of storage area (realistic table location)
INSERT INTO storage_locations (storage_area_id, code, name, qr_code, geojson_coordinates, active, created_at)
SELECT
    sa.storage_area_id,
    'GH-BA-001-NORTH-A1',
    'Mesa Norte A1',
    'QR-MESA-A1',
    ST_GeomFromText('POINT(-58.41965 -34.57520)', 4326),
    true,
    NOW()
FROM storage_areas sa
WHERE sa.code = 'GH-BA-001-NORTH'
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 7. STORAGE BIN TYPES (DB005) - Reference data
-- ============================================================================
INSERT INTO storage_bin_types (code, name, category, description, rows, columns, capacity, is_grid, created_at)
VALUES
    (
        'SEGMENT_STANDARD',
        'Individual Segment',
        'segment',
        'Individual segment detected by ML (no fixed dimensions)',
        NULL,
        NULL,
        NULL,
        false,
        NOW()
    ),
    (
        'PLUG_TRAY_288',
        '288-Cell Plug Tray',
        'plug',
        'Standard 288-cell plug tray (18 rows × 16 columns)',
        18,
        16,
        288,
        true,
        NOW()
    )
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 8. STORAGE BIN (DB004) - Segment 001 with ML metadata
-- ============================================================================
INSERT INTO storage_bins (storage_location_id, storage_bin_type_id, code, label, description, position_metadata, status, created_at)
SELECT
    sl.location_id,
    bt.bin_type_id,
    'GH-BA-001-NORTH-A1-SEG001',
    'Segment 001',
    'Segment detected by ML segmentation pipeline',
    jsonb_build_object(
        'bbox', jsonb_build_object('x', 100, 'y', 200, 'width', 300, 'height', 150),
        'confidence', 0.92,
        'container_type', 'segmento',
        'ml_model_version', 'yolov11-seg-v2.3',
        'detected_at', NOW()::text
    ),
    'active',
    NOW()
FROM storage_locations sl
CROSS JOIN storage_bin_types bt
WHERE sl.code = 'GH-BA-001-NORTH-A1'
  AND bt.code = 'SEGMENT_STANDARD'
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 9. PRODUCT CATEGORY (DB015) - Succulent category
-- ============================================================================
INSERT INTO product_categories (code, name, description)
VALUES (
    'SUCCULENT',
    'Suculentas',
    'Plantas suculentas (cactáceas, crasuláceas, etc.)'
) ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 10. PRODUCT FAMILY (DB016) - Echeveria family
-- ============================================================================
INSERT INTO product_families (category_id, name, scientific_name, description)
SELECT
    pc.category_id,
    'Echeveria',
    'Echeveria sp.',
    'Género de suculentas con rosetas compactas (Familia Crassulaceae)'
FROM product_categories pc
WHERE pc.code = 'SUCCULENT'
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- 11. PRODUCT (DB017) - Echeveria 'Lola'
-- ============================================================================
INSERT INTO products (family_id, sku, common_name, scientific_name, description, custom_attributes)
SELECT
    pf.family_id,
    'ECHEV-LOLA-001',
    'Echeveria ''Lola''',
    'Echeveria lilacina × Echeveria derenbergii',
    'Suculenta roseta compacta con hojas azul-grisáceas',
    jsonb_build_object(
        'color', 'blue-gray',
        'variegation', false,
        'growth_rate', 'slow',
        'bloom_season', 'spring',
        'cold_hardy', false
    )
FROM product_families pf
WHERE pf.name = 'Echeveria'
ON CONFLICT (sku) DO NOTHING;

-- ============================================================================
-- 12. PACKAGING TYPE (DB009) - Pot type
-- ============================================================================
INSERT INTO packaging_types (code, name, description)
VALUES (
    'POT',
    'Maceta',
    'Maceta plástica redonda estándar'
) ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 13. PACKAGING MATERIAL (DB021) - Plastic material
-- ============================================================================
INSERT INTO packaging_materials (code, name, description)
VALUES (
    'PLASTIC',
    'Plástico',
    'Material plástico estándar (polipropileno)'
) ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- 14. PACKAGING COLOR (DB010) - Black color
-- ============================================================================
INSERT INTO packaging_colors (name, hex_code)
VALUES (
    'Black',
    '#000000'
) ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- 15. PACKAGING CATALOG (DB022) - 8cm black plastic pot
-- ============================================================================
INSERT INTO packaging_catalog (packaging_type_id, packaging_material_id, packaging_color_id, sku, name, volume_liters, diameter_cm, height_cm)
SELECT
    pt.packaging_type_id,
    pm.packaging_material_id,
    pc.packaging_color_id,
    'POT-8CM-BLACK',
    'Maceta 8cm negra',
    0.25,
    8.0,
    8.0
FROM packaging_types pt
CROSS JOIN packaging_materials pm
CROSS JOIN packaging_colors pc
WHERE pt.code = 'POT'
  AND pm.code = 'PLASTIC'
  AND pc.name = 'Black'
ON CONFLICT (sku) DO NOTHING;

-- ============================================================================
-- 16. STORAGE LOCATION CONFIG (DB024) - Expected product configuration
-- ============================================================================
-- This links the storage location to expected product/packaging/state
INSERT INTO storage_location_config (storage_location_id, product_id, packaging_catalog_id, expected_product_state_id, area_cm2, active, notes, created_at)
SELECT
    sl.location_id,
    p.id,
    pkg.packaging_catalog_id,
    ps.product_state_id,
    500.00,  -- 500 cm² available area
    true,
    'Configuration for Echeveria Lola in 8cm pots (growth stage)',
    NOW()
FROM storage_locations sl
CROSS JOIN products p
CROSS JOIN packaging_catalog pkg
CROSS JOIN product_states ps
WHERE sl.code = 'GH-BA-001-NORTH-A1'
  AND p.sku = 'ECHEV-LOLA-001'
  AND pkg.sku = 'POT-8CM-BLACK'
  AND ps.code = 'CRECIMIENTO';

-- ============================================================================
-- VERIFICATION QUERIES (commented out for production use)
-- ============================================================================
-- Run these manually to verify data was loaded correctly:

-- SELECT 'warehouses' AS table_name, COUNT(*) FROM warehouses;
-- SELECT 'storage_areas' AS table_name, COUNT(*) FROM storage_areas;
-- SELECT 'storage_locations' AS table_name, COUNT(*) FROM storage_locations;
-- SELECT 'storage_bins' AS table_name, COUNT(*) FROM storage_bins;
-- SELECT 'storage_bin_types' AS table_name, COUNT(*) FROM storage_bin_types;
-- SELECT 'product_categories' AS table_name, COUNT(*) FROM product_categories;
-- SELECT 'product_families' AS table_name, COUNT(*) FROM product_families;
-- SELECT 'products' AS table_name, COUNT(*) FROM products;
-- SELECT 'product_states' AS table_name, COUNT(*) FROM product_states;
-- SELECT 'product_sizes' AS table_name, COUNT(*) FROM product_sizes;
-- SELECT 'packaging_types' AS table_name, COUNT(*) FROM packaging_types;
-- SELECT 'packaging_materials' AS table_name, COUNT(*) FROM packaging_materials;
-- SELECT 'packaging_colors' AS table_name, COUNT(*) FROM packaging_colors;
-- SELECT 'packaging_catalog' AS table_name, COUNT(*) FROM packaging_catalog;
-- SELECT 'users' AS table_name, COUNT(*) FROM users;
-- SELECT 'storage_location_config' AS table_name, COUNT(*) FROM storage_location_config;

-- Verify geometry is valid:
-- SELECT code, ST_IsValid(geojson_coordinates) AS is_valid, ST_GeometryType(geojson_coordinates) AS geom_type
-- FROM warehouses;

-- Verify GENERATED columns (area_m2, centroid):
-- SELECT code, area_m2, ST_AsText(centroid) AS centroid_wkt FROM warehouses;
-- SELECT code, area_m2, ST_AsText(centroid) AS centroid_wkt FROM storage_areas;
-- SELECT code, area_m2, ST_AsText(centroid) AS centroid_wkt FROM storage_locations;

-- ============================================================================
-- END OF FIXTURES
-- ============================================================================
