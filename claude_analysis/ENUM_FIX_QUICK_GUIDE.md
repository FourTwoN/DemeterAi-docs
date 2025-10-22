# ENUM Conflict - Quick Fix Guide

**Problem**: `type warehouse_type_enum already exists` error when running migrations

**Root Cause**: Partial migration state - warehouses table exists WITHOUT warehouse_type column

---

## Option 1: Clean Database Recreation (RECOMMENDED) ⚡

**Time**: ~2 minutes
**Risk**: NONE (test database only)
**Data Loss**: YES (acceptable for test DB)

```bash
# 1. Stop and clean
docker compose down db_test
docker volume rm $(docker volume ls -q | grep demeterai_db_test) 2>/dev/null || true

# 2. Start fresh
docker compose up db_test -d
sleep 10  # Wait for PostgreSQL

# 3. Run migrations
cd /home/lucasg/proyectos/DemeterDocs
alembic upgrade head

# 4. Verify (should show 15 ENUMs)
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test \
  -c "SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname;"

# 5. Run tests
pytest tests/unit/models/ -v
```

**Expected Result**: All migrations apply cleanly, tests pass ✅

---

## Option 2: Manual Fix (ONLY if data must be preserved)

**Time**: ~5 minutes
**Risk**: MEDIUM (manual SQL intervention)
**Data Loss**: NO

```bash
# 1. Check current state
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test \
  -c "\d warehouses"

# 2. Create missing ENUM
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test <<EOF
CREATE TYPE warehouse_type_enum AS ENUM ('greenhouse', 'shadehouse', 'open_field', 'tunnel');
EOF

# 3. Add missing column (if warehouses table exists)
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test <<EOF
ALTER TABLE warehouses
ADD COLUMN warehouse_type warehouse_type_enum NOT NULL DEFAULT 'greenhouse';
EOF

# 4. Update Alembic version
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test <<EOF
UPDATE alembic_version SET version_num = '2f68e3f132f5';
EOF

# 5. Continue migrations
alembic upgrade head

# 6. Verify
alembic current
```

---

## Verification Checklist

After either option:

```bash
# ✅ Check Alembic version
alembic current
# Expected: 9f8e7d6c5b4a (head)

# ✅ Count ENUMs (should be ~15)
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test \
  -c "SELECT COUNT(*) FROM pg_type WHERE typtype = 'e';"

# ✅ Count tables (should be ~30)
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test \
  -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"

# ✅ Check warehouses schema (should include warehouse_type)
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test \
  -c "\d warehouses" | grep warehouse_type

# ✅ Run tests
pytest tests/unit/models/test_warehouse.py -v
```

---

## What Went Wrong?

**Diagnosis**: Database has partial state from failed migration

**Evidence**:
- Alembic says: "I'm at version 8807863f7d8c"
- Database has: warehouses table (from version 2f68e3f132f5)
- warehouses table is MISSING: warehouse_type column
- Only 2 ENUMs exist (should be 15)

**Fix**: Clean slate (Option 1) or manual repair (Option 2)

---

## For Full Details

See: `/home/lucasg/proyectos/DemeterDocs/ENUM_CONFLICT_DIAGNOSTIC_REPORT.md`

**Report includes**:
- Complete ENUM inventory (15 expected vs 2 actual)
- Table-by-table comparison
- Root cause analysis
- Long-term prevention strategy
