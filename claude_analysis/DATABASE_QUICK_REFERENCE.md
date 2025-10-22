# DemeterAI Database Quick Reference

**Last Updated**: 2025-10-21
**Migration Version**: `8807863f7d8c` (head)

---

## Database Connections

### Main Database (Development)
```bash
Host: localhost
Port: 5432
Database: demeterai
User: demeter
Password: demeter_dev_password

# psql connection
PGPASSWORD=demeter_dev_password psql -U demeter -d demeterai -h localhost -p 5432

# Python connection strings
DATABASE_URL="postgresql+asyncpg://demeter:demeter_dev_password@localhost:5432/demeterai"
DATABASE_URL_SYNC="postgresql+psycopg2://demeter:demeter_dev_password@localhost:5432/demeterai"
```

### Test Database
```bash
Host: localhost
Port: 5434
Database: demeterai_test
User: demeter_test
Password: demeter_test_password

# psql connection
PGPASSWORD=demeter_test_password psql -U demeter_test -d demeterai_test -h localhost -p 5434

# Python connection strings (for testing)
DATABASE_URL="postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
```

---

## Docker Commands

```bash
# Start both databases
docker compose up db db_test -d

# Stop both databases
docker compose down db db_test

# Stop and remove volumes (DANGER: deletes all data)
docker compose down db db_test -v

# View logs
docker logs demeterai-db
docker logs demeterai-db-test

# Check status
docker compose ps
```

---

## Alembic Migration Commands

### Main Database (default)
```bash
# Check current version
alembic current

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Downgrade to base (DANGER: drops all tables)
alembic downgrade base

# Generate new migration
alembic revision --autogenerate -m "description"

# View migration history
alembic history --verbose
```

### Test Database (requires env override)
```bash
# Set environment variable for test DB
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"

# Then run any alembic command
alembic current
alembic upgrade head
```

---

## Database Schema Summary

### Current State
- **Migration Version**: `8807863f7d8c`
- **Total Tables**: 15 (14 app + 1 metadata)
- **Total Indexes**: 73
- **Foreign Keys**: 10
- **Enum Types**: 9
- **PostGIS Version**: 3.6.0
- **Database Size**: ~20 MB (fresh)

### Tables by Category

#### Geospatial Hierarchy (4 levels)
1. `warehouses` (Level 1) - Root of geospatial hierarchy
2. `storage_areas` (Level 2) - Areas within warehouses
3. `storage_locations` (Level 3) - Locations within areas
4. `storage_bins` (Level 4) - Bins within locations

#### Configuration & Support
5. `storage_bin_types` - Bin type definitions
6. `location_relationships` - Custom location relationships (NEW)

#### Product Taxonomy (3 levels)
7. `product_categories` (Level 1) - Top-level categories
8. `product_families` (Level 2) - Families within categories
9. `products` (Level 3) - Individual products

#### Product Attributes
10. `product_sizes` - Size definitions
11. `product_states` - State definitions

#### User & Media
12. `users` - User management
13. `s3_images` - Image metadata (NEW)

#### System
14. `alembic_version` - Migration tracking
15. `spatial_ref_sys` - PostGIS spatial references

---

## Common SQL Queries

### Check Migration Status
```sql
SELECT version_num FROM alembic_version;
```

### List All Tables
```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### Count Records by Table
```sql
SELECT
  schemaname,
  tablename,
  n_tup_ins - n_tup_del as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### Check Enum Types
```sql
SELECT typname as enum_type
FROM pg_type
WHERE typtype = 'e'
AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
ORDER BY typname;
```

### List Foreign Keys
```sql
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'public'
ORDER BY tc.table_name;
```

### Check Database Size
```sql
SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;
```

### List Indexes by Table
```sql
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

---

## Testing Commands

### Run All Tests
```bash
pytest tests/ -v
```

### Run Model Tests Only
```bash
pytest tests/unit/models/ -v
```

### Run Repository Tests Only
```bash
pytest tests/integration/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Run Specific Test File
```bash
pytest tests/unit/models/test_warehouse.py -v
```

---

## Diagnostic Commands

### Quick Health Check
```bash
# Main DB
PGPASSWORD=demeter_dev_password psql -U demeter -d demeterai -h localhost -p 5432 -c "
SELECT
  'Tables: ' || COUNT(*)
FROM pg_tables
WHERE schemaname='public' AND tablename != 'spatial_ref_sys';
"

# Test DB
PGPASSWORD=demeter_test_password psql -U demeter_test -d demeterai_test -h localhost -p 5434 -c "
SELECT
  'Tables: ' || COUNT(*)
FROM pg_tables
WHERE schemaname='public' AND tablename != 'spatial_ref_sys';
"
```

### Full Diagnostic (uses script from /tmp/db_diagnostic.sql)
```bash
# Main DB
PGPASSWORD=demeter_dev_password psql -U demeter -d demeterai -h localhost -p 5432 -f /tmp/db_diagnostic.sql

# Test DB
PGPASSWORD=demeter_test_password psql -U demeter_test -d demeterai_test -h localhost -p 5434 -f /tmp/db_diagnostic.sql
```

---

## Troubleshooting

### Issue: Alembic connects to wrong database
**Solution:** Override DATABASE_URL_SYNC environment variable
```bash
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
alembic current
```

### Issue: Enum type already exists
**Solution:** Drop and recreate database
```bash
docker compose down db_test -v
docker compose up db_test -d
sleep 10
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
alembic upgrade head
```

### Issue: Connection refused
**Solution:** Ensure Docker containers are running
```bash
docker compose ps
docker compose up db db_test -d
sleep 10  # Wait for PostgreSQL to initialize
```

### Issue: Authentication failed
**Solution:** Check passwords in docker-compose.yml
```bash
# For main DB
PGPASSWORD=demeter_dev_password psql -U demeter -d demeterai -h localhost -p 5432 -c "SELECT 1;"

# For test DB
PGPASSWORD=demeter_test_password psql -U demeter_test -d demeterai_test -h localhost -p 5434 -c "SELECT 1;"
```

---

## Model Import Verification

```bash
# Verify all models import correctly
python -c "
from app.models.warehouse import Warehouse
from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.storage_bin import StorageBin
from app.models.storage_bin_type import StorageBinType
from app.models.location_relationship import LocationRelationship
from app.models.product_category import ProductCategory
from app.models.product_family import ProductFamily
from app.models.product import Product
from app.models.product_size import ProductSize
from app.models.product_state import ProductState
from app.models.user import User
from app.models.s3_image import S3Image
print('✅ All models imported successfully')
"
```

---

## Repository Import Verification

```bash
# Verify all repositories import correctly
python -c "
from app.repositories.warehouse_repository import WarehouseRepository
from app.repositories.storage_area_repository import StorageAreaRepository
from app.repositories.storage_location_repository import StorageLocationRepository
from app.repositories.storage_bin_repository import StorageBinRepository
from app.repositories.product_repository import ProductRepository
print('✅ All repositories imported successfully')
"
```

---

## Complete Database Reset (DANGER)

**⚠️ WARNING: This will delete ALL data!**

```bash
# Full reset procedure
echo "Dropping databases..."
docker compose down db db_test -v

echo "Waiting for cleanup..."
sleep 3

echo "Recreating databases..."
docker compose up db db_test -d

echo "Waiting for PostgreSQL initialization..."
sleep 10

echo "Applying migrations to main DB..."
alembic upgrade head

echo "Applying migrations to test DB..."
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
alembic upgrade head

echo "Verifying migration status..."
alembic current
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
alembic current

echo "✅ Database reset complete"
```

---

## Key File Locations

```
Database Schema & Migrations:
  /home/lucasg/proyectos/DemeterDocs/database/database.mmd - ERD (source of truth)
  /home/lucasg/proyectos/DemeterDocs/alembic/versions/ - Migration files (14 migrations)
  /home/lucasg/proyectos/DemeterDocs/alembic.ini - Alembic configuration
  /home/lucasg/proyectos/DemeterDocs/alembic/env.py - Alembic environment

Models:
  /home/lucasg/proyectos/DemeterDocs/app/models/ - SQLAlchemy models (13 models)
  /home/lucasg/proyectos/DemeterDocs/app/db/base.py - Base class for all models

Repositories:
  /home/lucasg/proyectos/DemeterDocs/app/repositories/ - Repository pattern (27 repositories)

Configuration:
  /home/lucasg/proyectos/DemeterDocs/app/core/config.py - Database URLs and settings
  /home/lucasg/proyectos/DemeterDocs/docker-compose.yml - Docker database configuration

Tests:
  /home/lucasg/proyectos/DemeterDocs/tests/unit/models/ - Model unit tests
  /home/lucasg/proyectos/DemeterDocs/tests/integration/ - Integration tests with real DB
  /home/lucasg/proyectos/DemeterDocs/tests/conftest.py - Test fixtures and DB session

Reports:
  /home/lucasg/proyectos/DemeterDocs/DATABASE_RECREATION_REPORT_2025-10-21.md - Full recreation report
  /home/lucasg/proyectos/DemeterDocs/DATABASE_QUICK_REFERENCE.md - This file
```

---

## Useful Environment Variables

```bash
# Main database (default)
export DATABASE_URL="postgresql+asyncpg://demeter:demeter_dev_password@localhost:5432/demeterai"
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter:demeter_dev_password@localhost:5432/demeterai"

# Test database
export DATABASE_URL="postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
export DATABASE_URL_SYNC="postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test"

# PostgreSQL passwords
export PGPASSWORD=demeter_dev_password      # For main DB
export PGPASSWORD=demeter_test_password     # For test DB

# Logging
export LOG_LEVEL=DEBUG                      # Enable debug logging
export DB_ECHO_SQL=true                     # Log all SQL queries
```

---

## Next Steps After Database Recreation

1. ✅ Verify model imports: `python -c "from app.models import *"`
2. ✅ Verify repository imports: `python -c "from app.repositories import *"`
3. ⏳ Run full test suite: `pytest tests/ -v --cov=app`
4. ⏳ Seed development data (if applicable)
5. ⏳ Verify API endpoints work with new schema

---

**Quick Reference Version**: 1.0
**Last Database Recreation**: 2025-10-21
**Schema Status**: ✅ CLEAN - Both databases recreated and verified
