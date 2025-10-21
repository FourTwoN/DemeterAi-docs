# ENUM Conflict Diagnostic Report - DemeterAI
**Date**: 2025-10-21
**Database**: demeterai_test (PostgreSQL 18 + PostGIS 3.6)
**Issue**: Type "warehouse_type_enum" already exists (prevents migration)

---

## Executive Summary

**ROOT CAUSE**: The database has **partial migration state** from previous runs. Specifically:
- Migration `8807863f7d8c` is recorded in `alembic_version` table
- But migration `2f68e3f132f5` (warehouses table) was **partially applied**
- The `warehouses` table exists **WITHOUT** the `warehouse_type` ENUM column
- Alembic tries to re-run from the beginning, causing ENUM conflicts

**IMPACT**: Cannot apply migrations (blocks all tests requiring database)

---

## 1. Current Database State

### Alembic Version
```
Current migration: 8807863f7d8c (add location_relationships table)
Expected next: 9f8e7d6c5b4a (create remaining tables)
```

### Existing ENUM Types (2 total)
```sql
-- Only 2 ENUMs exist in the database
1. relationshiptypeenum
   - contains
   - adjacent_to

2. user_role_enum
   - admin
   - supervisor
   - worker
   - viewer
```

### Existing Tables (14 total)
```
1. alembic_version
2. location_relationships
3. product_categories
4. product_families
5. product_sizes
6. product_states
7. products
8. s3_images
9. storage_areas
10. storage_bin_types
11. storage_bins
12. storage_locations
13. users
14. warehouses ⚠️ (MISSING warehouse_type column)
```

### Warehouses Table Schema (Current)
```sql
-- PROBLEM: Missing warehouse_type column!
warehouses {
    warehouse_id: INTEGER PRIMARY KEY
    code: VARCHAR(50) UNIQUE NOT NULL
    name: VARCHAR(200) NOT NULL
    -- ❌ MISSING: warehouse_type ENUM (should be here)
    geojson_coordinates: GEOMETRY(POLYGON, 4326) NOT NULL
    centroid: GEOMETRY(POINT, 4326)
    active: BOOLEAN NOT NULL DEFAULT TRUE
    created_at: TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    updated_at: TIMESTAMP WITH TIME ZONE
    area_m2: NUMERIC(10,2) GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
}
```

### Expected Schema (from database.mmd)
```sql
warehouses {
    id: INT PRIMARY KEY
    code: VARCHAR UNIQUE
    name: VARCHAR
    type: VARCHAR "greenhouse|shadehouse|open_field|tunnel"  ⬅️ SHOULD BE ENUM
    geojson_coordinates: GEOMETRY(POLYGON)
    centroid: GEOMETRY(POINT)
    area_m2: NUMERIC GENERATED
    active: BOOLEAN DEFAULT TRUE
    created_at: TIMESTAMP
    updated_at: TIMESTAMP
}
```

---

## 2. ENUMs That Migrations Try to Create

### From Migration Files

**Migration: 2f68e3f132f5 (warehouses)**
```python
sa.Enum('greenhouse', 'shadehouse', 'open_field', 'tunnel', name='warehouse_type_enum')
```

**Migration: 742a3bebd3a8 (storage_areas)**
```python
sa.Enum('N', 'S', 'E', 'W', 'C', name='position_enum')
```

**Migration: 2wh7p3r9bm6t (storage_bin_types)**
```python
sa.Enum('plug', 'seedling_tray', 'box', 'segment', 'pot', name='bin_category_enum')
```

**Migration: 1wgcfiexamud (storage_bins)**
```python
sa.Enum('active', 'maintenance', 'retired', name='storage_bin_status_enum')
```

**Migration: 440n457t9cnp (s3_images)**
```python
sa.Enum('image/jpeg', 'image/png', name='content_type_enum')
sa.Enum('web', 'mobile', 'api', name='upload_source_enum')
sa.Enum('uploaded', 'processing', 'ready', 'failed', name='processing_status_enum')
```

**Migration: 6kp8m3q9n5rt (users)** ✅ EXISTS
```python
sa.Enum('admin', 'supervisor', 'worker', 'viewer', name='user_role_enum')
```

**Migration: 8807863f7d8c (location_relationships)** ✅ EXISTS
```python
sa.Enum('contains', 'adjacent_to', name='relationshiptypeenum')
```

**Migration: 9f8e7d6c5b4a (remaining tables)**
```python
sa.Enum('pending', 'processing', 'completed', 'failed', name='sessionstatusenum')
sa.Enum('reference', 'growth_stage', 'quality_check', 'monthly_sample', name='sampletypeenum')
sa.Enum('plantar', 'sembrar', 'transplante', 'muerte', 'ventas', 'foto', 'ajuste', 'manual_init', name='movementtypeenum')
sa.Enum('manual', 'ia', name='sourcetypeenum')
sa.Enum('band_estimation', 'density_estimation', 'grid_analysis', name='calculationmethodenum')
```

**Total ENUMs Expected**: 15
**Total ENUMs Exist**: 2 (user_role_enum, relationshiptypeenum)
**Missing ENUMs**: 13

---

## 3. Root Cause Analysis

### What Happened?

1. **Partial Migration Run**:
   - Someone ran `alembic upgrade head`
   - Migration `2f68e3f132f5` (warehouses) started executing
   - It created the `warehouses` table
   - **BUT** it failed before creating the ENUM or adding the column
   - SQLAlchemy's `checkfirst=False` (default) causes duplicate ENUM error

2. **State Mismatch**:
   - `alembic_version` says: "I'm at 8807863f7d8c"
   - Actual database has: warehouses table from `2f68e3f132f5` (next migration)
   - **Alembic doesn't know the table exists**

3. **Re-run Attempt**:
   - Alembic tries to run from the beginning
   - Tries to create `warehouse_type_enum` again
   - PostgreSQL says: "type already exists" (even though it doesn't!)
   - **Actually**: Some ENUMs exist in cache, others in failed state

### Why the Error?

```python
# In migration 2f68e3f132f5_create_warehouses_table.py line 59:
sa.Enum('greenhouse', 'shadehouse', 'open_field', 'tunnel', name='warehouse_type_enum')

# SQLAlchemy's default behavior:
# 1. Try to CREATE TYPE warehouse_type_enum
# 2. If already exists → ERROR (no checkfirst=True flag)
# 3. Migration fails, but table already created
```

**Key Issue**: SQLAlchemy Enum creates the PostgreSQL TYPE **before** creating the table. If migration fails mid-way:
- TYPE might be created
- Column might not be added
- Table exists in inconsistent state

---

## 4. Comparison: Expected vs Actual

### Expected ENUMs (15 total)

| ENUM Name | Migration | Status | Values |
|-----------|-----------|--------|--------|
| warehouse_type_enum | 2f68e3f132f5 | ❌ MISSING | greenhouse, shadehouse, open_field, tunnel |
| position_enum | 742a3bebd3a8 | ❌ MISSING | N, S, E, W, C |
| bin_category_enum | 2wh7p3r9bm6t | ❌ MISSING | plug, seedling_tray, box, segment, pot |
| storage_bin_status_enum | 1wgcfiexamud | ❌ MISSING | active, maintenance, retired |
| content_type_enum | 440n457t9cnp | ❌ MISSING | image/jpeg, image/png |
| upload_source_enum | 440n457t9cnp | ❌ MISSING | web, mobile, api |
| processing_status_enum | 440n457t9cnp | ❌ MISSING | uploaded, processing, ready, failed |
| user_role_enum | 6kp8m3q9n5rt | ✅ EXISTS | admin, supervisor, worker, viewer |
| relationshiptypeenum | 8807863f7d8c | ✅ EXISTS | contains, adjacent_to |
| sessionstatusenum | 9f8e7d6c5b4a | ❌ MISSING | pending, processing, completed, failed |
| sampletypeenum | 9f8e7d6c5b4a | ❌ MISSING | reference, growth_stage, quality_check, monthly_sample |
| movementtypeenum | 9f8e7d6c5b4a | ❌ MISSING | plantar, sembrar, transplante, muerte, ventas, foto, ajuste, manual_init |
| sourcetypeenum | 9f8e7d6c5b4a | ❌ MISSING | manual, ia |
| calculationmethodenum | 9f8e7d6c5b4a | ❌ MISSING | band_estimation, density_estimation, grid_analysis |

### Actual ENUMs (2 total)

| ENUM Name | Values |
|-----------|--------|
| relationshiptypeenum | contains, adjacent_to |
| user_role_enum | admin, supervisor, worker, viewer |

---

## 5. Solutions (Ranked by Safety)

### Option 1: Clean Database Recreation (RECOMMENDED) ✅

**Pros**:
- Clean slate, no corruption
- Ensures all migrations run correctly
- Fast (no data to preserve in test DB)

**Cons**:
- Loses any test data (acceptable for test DB)

**Steps**:
```bash
# 1. Drop and recreate test database
docker compose down db_test
docker volume rm demeterai_db_test_data  # If exists
docker compose up db_test -d

# 2. Wait for PostgreSQL ready
docker exec demeterai-db-test pg_isready -U demeter_test

# 3. Run migrations from scratch
alembic upgrade head

# 4. Verify all ENUMs created
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test -c "SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname;"

# Expected: 15 ENUMs (see table above)
```

---

### Option 2: Fix Warehouse Table Manually (RISKY) ⚠️

**Pros**:
- Preserves existing data
- Faster than full recreation

**Cons**:
- Manual intervention required
- Risk of missing other inconsistencies
- Doesn't fix root cause

**Steps**:
```sql
-- 1. Create missing ENUM
CREATE TYPE warehouse_type_enum AS ENUM ('greenhouse', 'shadehouse', 'open_field', 'tunnel');

-- 2. Add missing column
ALTER TABLE warehouses
ADD COLUMN warehouse_type warehouse_type_enum NOT NULL DEFAULT 'greenhouse';

-- 3. Update alembic version to reflect reality
UPDATE alembic_version SET version_num = '2f68e3f132f5';

-- 4. Continue with remaining migrations
```

**Then run**:
```bash
alembic upgrade head
```

---

### Option 3: Alembic Stamp + Manual Fix (ADVANCED) ⚠️

**Use case**: When database is in production with data to preserve

**Steps**:
```bash
# 1. Manually fix all inconsistencies (see Option 2)

# 2. Stamp Alembic to current state
alembic stamp 8807863f7d8c  # Current version

# 3. Run forward migrations
alembic upgrade head

# 4. Verify
alembic current
```

---

### Option 4: Modify Migrations to Use `checkfirst=True` (PREVENTIVE) 🛡️

**Purpose**: Prevent future conflicts

**Change in all migration files**:
```python
# OLD (causes conflicts)
sa.Enum('greenhouse', 'shadehouse', 'open_field', 'tunnel', name='warehouse_type_enum')

# NEW (idempotent)
from sqlalchemy.dialects.postgresql import ENUM

warehouse_type_enum = ENUM(
    'greenhouse', 'shadehouse', 'open_field', 'tunnel',
    name='warehouse_type_enum',
    create_type=True,  # Create if doesn't exist
    checkfirst=True    # ⬅️ KEY: Check before creating
)

sa.Column('warehouse_type', warehouse_type_enum, nullable=False)
```

**Note**: This requires rewriting 15 migrations! Only do this AFTER fixing current state.

---

## 6. Recommended Action Plan

### Phase 1: Immediate Fix (TODAY)

**Use Option 1 (Clean Recreation)**:

```bash
# Terminal 1: Stop and clean
docker compose down db_test
docker volume rm $(docker volume ls -q | grep demeterai_db_test) 2>/dev/null || true
docker compose up db_test -d

# Wait 10 seconds for PostgreSQL startup
sleep 10

# Terminal 2: Run migrations
cd /home/lucasg/proyectos/DemeterDocs
alembic upgrade head

# Verify ENUMs
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test -c \
  "SELECT COUNT(*) as enum_count FROM pg_type WHERE typtype = 'e';"

# Expected output: enum_count = 15 (or close)
```

### Phase 2: Verification (AFTER Phase 1)

```bash
# 1. Check all tables exist
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test -c \
  "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"

# Expected: ~30 tables (all from database.mmd)

# 2. Check warehouses table schema
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test -c "\d warehouses"

# Expected: Should include warehouse_type column

# 3. Run pytest to verify
pytest tests/unit/models/test_warehouse.py -v

# Expected: All tests pass
```

### Phase 3: Prevention (NEXT SPRINT)

**Task**: Create migration improvement task

**Proposed Task**: `DB029-fix-enum-idempotency.md`

**Content**:
```markdown
# [DB029] Fix ENUM Idempotency in Migrations

## Priority: MEDIUM
## Complexity: M (8 story points)
## Sprint: Sprint 04

## Problem
Current migrations use `sa.Enum()` without `checkfirst=True`, causing:
- Duplicate ENUM errors on re-runs
- Partial migration state corruption
- Manual intervention required

## Solution
Rewrite 15 migrations to use `checkfirst=True` pattern:

**Files to modify**:
- alembic/versions/2f68e3f132f5_create_warehouses_table.py
- alembic/versions/742a3bebd3a8_create_storage_areas_table.py
- alembic/versions/2wh7p3r9bm6t_create_storage_bin_types_table.py
- ... (12 more)

**Pattern**:
```python
from sqlalchemy.dialects.postgresql import ENUM

enum_type = ENUM('val1', 'val2', name='my_enum', create_type=True, checkfirst=True)
sa.Column('my_col', enum_type, nullable=False)
```

## Acceptance Criteria
- [ ] All 15 ENUMs use checkfirst=True
- [ ] Migrations are idempotent (can run multiple times)
- [ ] Tests pass after drop/recreate
- [ ] Documentation updated
```

---

## 7. Summary

### Current State
- **Alembic Version**: 8807863f7d8c (location_relationships)
- **Tables**: 14 (including warehouses WITHOUT warehouse_type)
- **ENUMs**: 2 (user_role_enum, relationshiptypeenum)
- **Status**: ❌ BROKEN (cannot apply migrations)

### Root Cause
- **Partial migration state** from previous failed run
- `warehouses` table exists without `warehouse_type` ENUM column
- SQLAlchemy tries to recreate ENUM, conflicts occur

### Recommended Fix
**Option 1**: Clean database recreation (safest, fastest for test DB)

### Long-term Prevention
- Add `checkfirst=True` to all ENUM definitions
- Use idempotent migration patterns
- Add pre-commit hook to verify migration syntax

---

## Appendix A: Full ENUM Inventory

### Expected ENUMs (from migrations)

```python
# 15 total ENUMs across 5 migrations:

# Migration 2f68e3f132f5 (warehouses)
1. warehouse_type_enum: ['greenhouse', 'shadehouse', 'open_field', 'tunnel']

# Migration 742a3bebd3a8 (storage_areas)
2. position_enum: ['N', 'S', 'E', 'W', 'C']

# Migration 2wh7p3r9bm6t (storage_bin_types)
3. bin_category_enum: ['plug', 'seedling_tray', 'box', 'segment', 'pot']

# Migration 1wgcfiexamud (storage_bins)
4. storage_bin_status_enum: ['active', 'maintenance', 'retired']

# Migration 440n457t9cnp (s3_images)
5. content_type_enum: ['image/jpeg', 'image/png']
6. upload_source_enum: ['web', 'mobile', 'api']
7. processing_status_enum: ['uploaded', 'processing', 'ready', 'failed']

# Migration 6kp8m3q9n5rt (users)
8. user_role_enum: ['admin', 'supervisor', 'worker', 'viewer'] ✅ EXISTS

# Migration 8807863f7d8c (location_relationships)
9. relationshiptypeenum: ['contains', 'adjacent_to'] ✅ EXISTS

# Migration 9f8e7d6c5b4a (remaining tables)
10. sessionstatusenum: ['pending', 'processing', 'completed', 'failed']
11. sampletypeenum: ['reference', 'growth_stage', 'quality_check', 'monthly_sample']
12. movementtypeenum: ['plantar', 'sembrar', 'transplante', 'muerte', 'ventas', 'foto', 'ajuste', 'manual_init']
13. sourcetypeenum: ['manual', 'ia']
14. calculationmethodenum: ['band_estimation', 'density_estimation', 'grid_analysis']
```

### Actual ENUMs (from database)

```sql
-- Only 2 ENUMs exist:

SELECT enumlabel
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role_enum')
ORDER BY enumsortorder;
-- Result: admin, supervisor, worker, viewer

SELECT enumlabel
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'relationshiptypeenum')
ORDER BY enumsortorder;
-- Result: contains, adjacent_to
```

---

**Report Generated**: 2025-10-21
**Database Expert**: Database Schema Authority
**Next Step**: Execute Option 1 (Clean Recreation) to unblock tests
