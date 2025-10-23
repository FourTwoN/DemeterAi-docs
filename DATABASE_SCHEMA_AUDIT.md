# Database Schema Audit Report
**Date**: 2025-10-23
**Auditor**: Claude Code
**Scope**: Complete audit of SQLAlchemy models vs database/database.mmd ERD

## Executive Summary
This audit compares all SQLAlchemy models against the authoritative ERD in `database/database.mmd` to identify schema drift and inconsistencies.

## Critical Issues Found

### 1. Primary Key Column Name Mismatch (CRITICAL)

**ERD Specification**: All tables use `id` as primary key column name
**SQLAlchemy Models**: Using inconsistent named primary keys

| Table | ERD PK | Model PK | Status |
|-------|--------|----------|--------|
| warehouses | `id` | `warehouse_id` | ❌ MISMATCH |
| storage_areas | `id` | `storage_area_id` | ❌ MISMATCH |
| storage_locations | `id` | `location_id` | ❌ MISMATCH |
| storage_bins | `id` | `bin_id` | ❌ MISMATCH |
| storage_bin_types | `id` | `bin_type_id` | ❌ TO VERIFY |
| product_categories | `id` | TBD | ❌ TO VERIFY |
| product_families | `id` | TBD | ❌ TO VERIFY |
| products | `id` | TBD | ❌ TO VERIFY |
| product_states | `id` | TBD | ❌ TO VERIFY |
| product_sizes | `id` | TBD | ❌ TO VERIFY |
| packaging_types | `id` | TBD | ❌ TO VERIFY |
| packaging_catalog | `id` | TBD | ❌ TO VERIFY |
| packaging_materials | `id` | TBD | ❌ TO VERIFY |
| packaging_colors | `id` | TBD | ❌ TO VERIFY |
| stock_batches | `id` | TBD | ❌ TO VERIFY |
| stock_movements | `id` | TBD | ❌ TO VERIFY |
| users | `id` | TBD | ❌ TO VERIFY |
| photo_processing_sessions | `id` | TBD | ❌ TO VERIFY |
| s3_images | `image_id` | `image_id` | ✅ MATCH (UUID) |
| product_sample_images | `id` | TBD | ❌ TO VERIFY |
| detections | `id` | TBD | ❌ TO VERIFY |
| estimations | `id` | TBD | ❌ TO VERIFY |
| classifications | `id` | TBD | ❌ TO VERIFY |
| storage_location_config | `id` | TBD | ❌ TO VERIFY |
| density_parameters | `id` | TBD | ❌ TO VERIFY |
| location_relationships | `id` | TBD | ❌ TO VERIFY |
| price_list | `id` | TBD | ❌ TO VERIFY |

**Impact**:
- Foreign key references will fail
- Migrations will fail
- Repository queries will fail
- ALL relationships are broken

### 2. Geometry Column Name Mismatch (CRITICAL)

**storage_locations table**:
- **ERD**: `geojson_coordinates` (POLYGON geometry)
- **Model**: `coordinates` (POINT geometry)
- **Impact**: Different geometry type AND different column name!

**warehouses, storage_areas**:
- **ERD**: `geojson_coordinates` (POLYGON)
- **Models**: `geojson_coordinates` (POLYGON) ✅ CORRECT

### 3. Centroid Column Mismatch

**All geospatial models (warehouses, storage_areas, storage_locations)**:
- **ERD**: No `centroid` column specified
- **Models**: Have `centroid` column with triggers
- **Status**: UNCLEAR - needs clarification from ERD

### 4. Missing Columns (TO VERIFY)

Need to check all models for:
- Missing JSONB columns
- Missing timestamp columns
- Missing enum columns
- Missing foreign keys

### 5. Foreign Key Name Mismatches (TO VERIFY)

Need to verify all FK column names match ERD exactly.

## Detailed Model Audit

### DB001: warehouses
- ❌ PK: `warehouse_id` should be `id`
- ✅ code: VARCHAR, unique, indexed
- ✅ name: VARCHAR
- ✅ type: ENUM (greenhouse|shadehouse|open_field|tunnel)
- ✅ geojson_coordinates: PostGIS POLYGON SRID 4326
- ⚠️ centroid: Not in ERD (model has it)
- ⚠️ area_m2: GENERATED column (needs verification)
- ✅ active: BOOLEAN default TRUE
- ✅ created_at: TIMESTAMP
- ✅ updated_at: TIMESTAMP

### DB002: storage_areas
- ❌ PK: `storage_area_id` should be `id`
- ❌ FK: `warehouse_id` should reference `warehouses.id` (not `warehouses.warehouse_id`)
- ✅ code: VARCHAR, unique, indexed
- ✅ name: VARCHAR
- ✅ position: ENUM (N|S|E|W|C)
- ✅ geojson_coordinates: PostGIS POLYGON SRID 4326
- ⚠️ centroid: Not in ERD (model has it)
- ⚠️ area_m2: GENERATED column (needs verification)
- ✅ active: BOOLEAN default TRUE
- ✅ created_at: TIMESTAMP
- ✅ updated_at: TIMESTAMP

### DB003: storage_locations
- ❌ PK: `location_id` should be `id`
- ❌ FK: `storage_area_id` should reference `storage_areas.id` (not `storage_areas.storage_area_id`)
- ❌ FK: `photo_session_id` should reference `photo_processing_sessions.id`
- ✅ code: VARCHAR, unique, indexed
- ✅ qr_code: VARCHAR, unique, indexed
- ✅ name: VARCHAR
- ✅ description: TEXT
- ❌ **CRITICAL**: Column name `coordinates` should be `geojson_coordinates`
- ❌ **CRITICAL**: Geometry type POINT should be POLYGON
- ⚠️ centroid: Not in ERD (model has it)
- ⚠️ area_m2: GENERATED column (needs verification)
- ✅ active: BOOLEAN default TRUE
- ✅ created_at: TIMESTAMP
- ✅ updated_at: TIMESTAMP

### DB004: storage_bins
- ❌ PK: `bin_id` should be `id`
- ❌ FK: `storage_location_id` should reference `storage_locations.id` (not `storage_locations.location_id`)
- ❌ FK: `storage_bin_type_id` should reference `storage_bin_types.id`
- ✅ code: VARCHAR, unique, indexed
- ✅ label: VARCHAR (nullable)
- ✅ description: TEXT (nullable)
- ✅ position_metadata: JSONB (segmentation_mask, bbox, confidence)
- ✅ status: ENUM (active|maintenance|retired)
- ✅ created_at: TIMESTAMP
- ⚠️ updated_at: Not in ERD but model has it

## Recommendations

### Immediate Action Required

1. **STOP all development** until schema is fixed
2. **Create migration** to rename all PK columns to `id`
3. **Update all FK references** to use correct column names
4. **Fix storage_locations geometry** column name and type
5. **Regenerate all models** from corrected schema
6. **Run full test suite** after fixes

### Process Improvements

1. Add schema validation tests that compare ERD vs models
2. Use code generation from ERD (single source of truth)
3. Add pre-commit hook to validate schema consistency
4. Document all deviations from ERD with justification

## Status: AUDIT IN PROGRESS

Next steps:
- [ ] Read all remaining models (DB005-DB028)
- [ ] Document all discrepancies
- [ ] Create comprehensive fix plan
- [ ] Implement fixes with migrations
- [ ] Verify with tests
