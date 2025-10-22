# Database Recreation & Diagnostic Report

**Date**: 2025-10-21
**Project**: DemeterAI v2.0
**Status**: ✅ SUCCESSFUL - Both databases fully recreated and verified

---

## Executive Summary

Both the **main database** (demeterai) and **test database** (demeterai_test) have been completely dropped, recreated, and migrated to the latest schema version. All migrations applied successfully without errors.

---

## Execution Steps Completed

### Step 1: Verify Initial State
- **Main DB Migration**: `8807863f7d8c` (head)
- **Alembic History**: 14 migrations from initial PostGIS setup to location_relationships

### Step 2: Database Recreation
- **Action**: Dropped both databases with volumes (`docker compose down db db_test -v`)
- **Result**: All data and volumes successfully removed
- **Recreation**: Both containers recreated with fresh volumes
- **Wait Time**: 10 seconds for PostgreSQL initialization

### Step 3: Database Verification
- **Main DB**: PostgreSQL 18.0, Port 5432 ✅
- **Test DB**: PostgreSQL 18.0, Port 5434 ✅
- **Connectivity**: Both databases accepting connections

### Step 4: Migration Application

#### Main Database (demeterai)
```bash
Connection: postgresql+psycopg2://demeter:demeter_dev_password@localhost:5432/demeterai
Status: ✅ SUCCESS
Migrations Applied: 14 (base → 8807863f7d8c)
Duration: ~15 seconds
Errors: None
```

**Migration Sequence:**
1. `6f1b94ebef45` - initial_setup_enable_postgis
2. `2f68e3f132f5` - create warehouses table
3. `742a3bebd3a8` - create storage_areas table
4. `sof6kow8eu3r` - create storage_locations table
5. `2wh7p3r9bm6t` - create_storage_bin_types_table
6. `1wgcfiexamud` - create storage_bins table
7. `3xy8k1m9n4pq` - create_product_states_table
8. `4ab9c2d8e5fg` - create_product_sizes_table
9. `0fc9cac096f2` - create product_categories table
10. `1a2b3c4d5e6f` - create product_families table
11. `5gh9j2n4k7lm` - create products table
12. `6kp8m3q9n5rt` - create users table
13. `440n457t9cnp` - create s3_images table
14. `8807863f7d8c` - add location_relationships table

#### Test Database (demeterai_test)
```bash
Connection: postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test
Status: ✅ SUCCESS
Migrations Applied: 14 (base → 8807863f7d8c)
Duration: ~15 seconds
Errors: None
Environment Variable: DATABASE_URL_SYNC overridden for test DB
```

**Same migration sequence as main database** ✅

---

## Database Configuration Summary

### Tables Created: 15 (14 application + 1 metadata)

| # | Table Name | Purpose | Foreign Keys |
|---|------------|---------|--------------|
| 1 | `warehouses` | 4-level geospatial hierarchy (Level 1) | - |
| 2 | `storage_areas` | Storage areas within warehouses (Level 2) | warehouse_id, parent_area_id |
| 3 | `storage_locations` | Storage locations within areas (Level 3) | storage_area_id |
| 4 | `storage_bin_types` | Bin type definitions | - |
| 5 | `storage_bins` | Individual storage bins (Level 4) | storage_location_id, storage_bin_type_id |
| 6 | `location_relationships` | Custom location relationships | parent_location_id, child_location_id |
| 7 | `product_categories` | Product taxonomy (Level 1) | - |
| 8 | `product_families` | Product taxonomy (Level 2) | category_id |
| 9 | `products` | Product master data (Level 3) | family_id |
| 10 | `product_sizes` | Product size attributes | - |
| 11 | `product_states` | Product state definitions | - |
| 12 | `users` | User management | - |
| 13 | `s3_images` | Image storage metadata | uploaded_by_user_id |
| 14 | `alembic_version` | Migration tracking (metadata) | - |
| 15 | `spatial_ref_sys` | PostGIS spatial references (system) | - |

### Enum Types: 9

| Enum Type | Values | Used In |
|-----------|--------|---------|
| `warehouse_type_enum` | greenhouse, shadehouse, open_field, tunnel | warehouses.warehouse_type |
| `bin_category_enum` | harvest, packing, storage, quarantine | storage_bin_types.category |
| `position_enum` | floor, shelf, overhead | storage_bin_types.position |
| `storage_bin_status_enum` | available, occupied, reserved, maintenance | storage_bins.status |
| `relationshiptypeenum` | adjacent, opposite, shares_wall | location_relationships.relationship_type |
| `user_role_enum` | admin, supervisor, operator, viewer | users.role |
| `content_type_enum` | image/jpeg, image/png, image/heic | s3_images.content_type |
| `upload_source_enum` | web, mobile, api | s3_images.upload_source |
| `processing_status_enum` | uploaded, processing, completed, failed | s3_images.status |

### Foreign Key Constraints: 10

1. `storage_areas.warehouse_id` → `warehouses.warehouse_id` (CASCADE)
2. `storage_areas.parent_area_id` → `storage_areas.storage_area_id` (CASCADE)
3. `storage_locations.storage_area_id` → `storage_areas.storage_area_id` (CASCADE)
4. `storage_bins.storage_location_id` → `storage_locations.location_id` (CASCADE)
5. `storage_bins.storage_bin_type_id` → `storage_bin_types.bin_type_id` (RESTRICT)
6. `location_relationships.parent_location_id` → `storage_locations.location_id` (CASCADE)
7. `location_relationships.child_location_id` → `storage_locations.location_id` (CASCADE)
8. `product_families.category_id` → `product_categories.product_category_id` (CASCADE)
9. `products.family_id` → `product_families.family_id` (CASCADE)
10. `s3_images.uploaded_by_user_id` → `users.id` (SET NULL)

### Indexes: 73 total

**Distribution by table:**
- `warehouses`: 7 indexes (PK, unique code, geom, centroid, type, active)
- `storage_areas`: 9 indexes (PK, unique code, FK indexes, geom, active)
- `storage_locations`: 10 indexes (PK, unique code, FK indexes, geom, active)
- `storage_bins`: 7 indexes (PK, FK indexes, status, active)
- `storage_bin_types`: 4 indexes (PK, unique code, category)
- `location_relationships`: 4 indexes (PK, unique pair, parent/child FKs)
- `product_categories`: 3 indexes (PK, unique code)
- `product_families`: 2 indexes (PK, FK to category)
- `products`: 5 indexes (PK, unique code, family FK)
- `product_sizes`: 4 indexes (PK, unique code)
- `product_states`: 5 indexes (PK, unique code)
- `users`: 5 indexes (PK, unique email, role, active)
- `s3_images`: 6 indexes (PK, unique s3_key, status, user FK, created_at, GIN on gps)
- `alembic_version`: 1 index (PK)
- `spatial_ref_sys`: 1 index (PK)

### PostGIS Extensions: 2

| Extension | Version | Purpose |
|-----------|---------|---------|
| `postgis` | 3.6.0 | Geospatial geometry support |
| `postgis_topology` | 3.6.0 | Topology support for spatial relationships |

---

## Verification Results

### ✅ Main Database (demeterai)

```
Migration Version: 8807863f7d8c (head)
Total Tables: 15
Total Indexes: 73
Foreign Keys: 10
Enum Types: 9
PostGIS Version: 3.6.0
Database Size: 20 MB
Status: READY FOR USE
```

### ✅ Test Database (demeterai_test)

```
Migration Version: 8807863f7d8c (head)
Total Tables: 15
Total Indexes: 73
Foreign Keys: 10
Enum Types: 9
PostGIS Version: 3.6.0
Database Size: 20 MB
Status: READY FOR USE
```

### Schema Parity Verification

| Metric | Main DB | Test DB | Match |
|--------|---------|---------|-------|
| Migration Version | 8807863f7d8c | 8807863f7d8c | ✅ |
| Total Tables | 15 | 15 | ✅ |
| Total Indexes | 73 | 73 | ✅ |
| Foreign Keys | 10 | 10 | ✅ |
| Enum Types | 9 | 9 | ✅ |
| PostGIS Version | 3.6.0 | 3.6.0 | ✅ |
| Database Size | 20 MB | 20 MB | ✅ |

**Result**: Both databases are **IDENTICAL** in structure ✅

---

## Key Table Structures

### Warehouses Table (Geospatial Root)

```sql
warehouses:
  - warehouse_id (PK, serial)
  - code (VARCHAR(50), unique)
  - name (VARCHAR(200))
  - warehouse_type (warehouse_type_enum)
  - geojson_coordinates (geometry(Polygon,4326))
  - centroid (geometry(Point,4326)) -- auto-calculated
  - area_m2 (NUMERIC, generated) -- auto-calculated from geometry
  - active (BOOLEAN, default: true)
  - created_at (TIMESTAMPTZ)
  - updated_at (TIMESTAMPTZ)

Constraints:
  - PK: warehouse_id
  - UNIQUE: code
  - CHECK: code length 2-20 chars
  - TRIGGER: update_warehouse_centroid()

Indexes:
  - GIST: geojson_coordinates, centroid
  - BTREE: warehouse_type, active
```

### Location Relationships Table (NEW in latest migration)

```sql
location_relationships:
  - id (PK, serial)
  - parent_location_id (FK → storage_locations)
  - child_location_id (FK → storage_locations)
  - relationship_type (relationshiptypeenum)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

Constraints:
  - PK: id
  - UNIQUE: (parent_location_id, child_location_id)
  - CHECK: parent_location_id ≠ child_location_id (no self-reference)
  - FK: parent_location_id CASCADE
  - FK: child_location_id CASCADE

Indexes:
  - BTREE: parent_location_id, child_location_id
```

### S3 Images Table (NEW in recent migration)

```sql
s3_images:
  - image_id (PK, UUID)
  - s3_bucket (VARCHAR(255))
  - s3_key_original (VARCHAR(512), unique)
  - s3_key_thumbnail (VARCHAR(512), nullable)
  - content_type (content_type_enum)
  - file_size_bytes (BIGINT)
  - width_px (INTEGER)
  - height_px (INTEGER)
  - exif_metadata (JSONB, nullable)
  - gps_coordinates (JSONB, nullable)
  - upload_source (upload_source_enum, default: 'web')
  - uploaded_by_user_id (FK → users, nullable)
  - status (processing_status_enum, default: 'uploaded')
  - error_details (TEXT, nullable)
  - processing_status_updated_at (TIMESTAMPTZ, nullable)
  - created_at (TIMESTAMPTZ)
  - updated_at (TIMESTAMPTZ)

Constraints:
  - PK: image_id
  - UNIQUE: s3_key_original
  - FK: uploaded_by_user_id SET NULL

Indexes:
  - BTREE: status, uploaded_by_user_id, created_at DESC
  - GIN: gps_coordinates (JSONB index for geospatial queries)
```

---

## Issues Encountered & Resolved

### Issue 1: Enum Type Already Exists Error
**Error Message:**
```
psycopg2.errors.DuplicateObject: type "warehouse_type_enum" already exists
```

**Root Cause:**
- Initial downgrade command (`alembic downgrade base`) was executed against the **main database** (port 5432)
- The test database upgrade was attempted while enum types still existed from a previous session
- Alembic was connecting to the wrong database due to `DATABASE_URL_SYNC` environment variable

**Resolution:**
1. Dropped **both** databases completely with volumes
2. Recreated both databases from scratch
3. Applied migrations to main DB first (using default config)
4. Applied migrations to test DB second (using overridden `DATABASE_URL_SYNC`)
5. Result: Clean migration with no pre-existing enum types

### Issue 2: Environment Variable Override
**Challenge:**
- Alembic reads `DATABASE_URL_SYNC` from `app.core.config.settings`
- Default configuration points to main database (port 5432)
- Need to override for test database (port 5434)

**Solution:**
```bash
# Correct approach for test database migrations
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
alembic upgrade head
```

**Result:** Successfully applied migrations to both databases independently

---

## Database Connection Details

### Main Database
```
Host: localhost
Port: 5432
Database: demeterai
User: demeter
Password: demeter_dev_password
Connection String (Async): postgresql+asyncpg://demeter:demeter_dev_password@localhost:5432/demeterai
Connection String (Sync): postgresql+psycopg2://demeter:demeter_dev_password@localhost:5432/demeterai
Docker Container: demeterai-db
Volume: demeterdocs_postgres_data
```

### Test Database
```
Host: localhost
Port: 5434
Database: demeterai_test
User: demeter_test
Password: demeter_test_password
Connection String (Async): postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test
Connection String (Sync): postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test
Docker Container: demeterai-db-test
Volume: demeterdocs_postgres_test_data
```

---

## Post-Recreation Tasks

### ✅ Completed
- [x] Both databases dropped and recreated
- [x] All 14 migrations applied successfully
- [x] Schema verification completed
- [x] Index verification completed
- [x] Foreign key verification completed
- [x] Enum type verification completed
- [x] PostGIS extension verification completed
- [x] Database size verification completed
- [x] Main/Test parity verification completed

### 🔄 Next Steps (Recommended)

1. **Run Full Test Suite**
   ```bash
   pytest tests/ -v --cov=app --cov-report=term-missing
   ```
   - Verify all model tests pass
   - Verify all repository tests pass
   - Verify integration tests pass

2. **Verify Model Imports**
   ```bash
   python -c "from app.models import *; print('✅ All models imported')"
   ```

3. **Verify Repository Imports**
   ```bash
   python -c "from app.repositories import *; print('✅ All repositories imported')"
   ```

4. **Run Database Seeding (if applicable)**
   ```bash
   # Add seed data for development
   python scripts/seed_database.py
   ```

5. **Update Development Documentation**
   - Document new tables (`location_relationships`, `s3_images`)
   - Update ERD if needed
   - Update API documentation with new endpoints

---

## Technical Notes

### Migration System
- **Total Migrations**: 14
- **First Migration**: `6f1b94ebef45` (PostGIS setup)
- **Latest Migration**: `8807863f7d8c` (location_relationships)
- **Migration Tool**: Alembic 1.13+
- **SQLAlchemy Version**: 2.0+

### PostGIS Configuration
- **Version**: 3.6.0
- **SRID**: 4326 (WGS 84)
- **Geometry Types Used**:
  - `POLYGON` (warehouses)
  - `POINT` (warehouse centroids, storage areas)
- **Spatial Indexes**: GIST indexes on all geometry columns

### Performance Optimizations
- **Index Coverage**: 73 indexes across 15 tables
- **GIST Indexes**: All geospatial columns indexed
- **JSONB GIN Index**: GPS coordinates in s3_images
- **Unique Constraints**: All code/email fields enforced at DB level
- **Cascading Deletes**: Proper FK cascade rules for hierarchy cleanup

---

## Diagnostic Files Generated

1. **main_migration_output.txt** - Full migration log for main database
2. **test_migration_output.txt** - Full migration log for test database
3. **/tmp/db_diagnostic.sql** - Reusable diagnostic SQL script

---

## Validation Commands

```bash
# Verify main database
alembic current
psql -d demeterai -U demeter -c "\dt"

# Verify test database (override DATABASE_URL_SYNC)
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
alembic current
psql -U demeter_test -d demeterai_test -h localhost -p 5434 -c "\dt"

# Compare schemas
diff <(psql -d demeterai -U demeter -c "\d+ warehouses") \
     <(psql -U demeter_test -d demeterai_test -h localhost -p 5434 -c "\d+ warehouses")
```

---

## Conclusion

✅ **Database recreation completed successfully**

Both the main and test databases have been:
- Completely wiped and recreated
- Migrated to the latest schema version (`8807863f7d8c`)
- Verified for structural integrity
- Confirmed to be identical in schema

The databases are now **ready for development and testing** with a clean slate and all latest migrations applied.

---

**Report Generated**: 2025-10-21
**Total Execution Time**: ~2 minutes
**Final Status**: ✅ SUCCESS - No errors, both databases operational
