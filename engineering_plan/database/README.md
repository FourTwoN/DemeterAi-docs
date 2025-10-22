# Database Architecture

**Version:** 1.0
**Last Updated:** 2025-10-08

---

## Overview

DemeterAI uses **PostgreSQL 18 with PostGIS 3.3+** as its single source of truth. The database
schema is designed for:

- **Geospatial hierarchy:** 4 levels (warehouse → storage_area → storage_location → storage_bin)
- **Event sourcing:** `stock_movements` table for full audit trail
- **High volume:** Partitioned tables for detections/estimations (daily partitions)
- **Performance:** Strategic indexes, materialized views, query optimization

---

## Complete Schema

**See:** [../../database/database.mmd](../../database/database.mmd) for the complete
Entity-Relationship Diagram (Mermaid ERD)

**Tables:** 28 total

### Core Entity Groups

1. **Location Hierarchy (4 levels)**
    - `warehouses` (greenhouses, tunnels, shadehouses)
    - `storage_areas` (North/South zones within warehouse)
    - `storage_locations` (space between columns - photo unit)
    - `storage_bins` (containers: plugs, boxes, segments)

2. **Inventory & Movements**
    - `stock_batches` (aggregated state)
    - `stock_movements` (event sourcing - all transactions)

3. **Photo Processing**
    - `s3_images` (original + processed photos)
    - `photo_processing_sessions` (ML pipeline results)
    - `detections` (individual plant locations) **PARTITIONED**
    - `estimations` (area-based counts) **PARTITIONED**
    - `classifications` (product + packaging + size)

4. **Products & Packaging**
    - `product_categories` → `product_families` → `products`
    - `packaging_types` + `materials` + `colors` → `packaging_catalog`
    - `price_list` (wholesale + retail pricing)

5. **Configuration**
    - `storage_location_config` (expected product + packaging per location)
    - `density_parameters` (auto-calibrated from ML detections)

6. **Users**
    - `users` (admin, supervisor, worker, viewer)

---

## Critical Design Decisions

### Decision 1: Database as Source of Truth

**Principle:** ALL business logic references database schema. ML pipeline, API, frontend all derive
from DB.

**Why:**

- Single source of truth prevents inconsistencies
- Schema changes propagate to all layers
- Easy to audit and trace data flow

### Decision 2: Event Sourcing for Stock Movements

**Approach:** Hybrid - `stock_movements` (events) + `stock_batches` (state)

**Why:**

- Full audit trail (every plant movement recorded)
- Calculate current stock: `SUM(stock_movements.quantity) GROUP BY batch_id`
- Monthly reconciliation requires historical events
- Fast queries via materialized `stock_batches` table

**Trade-off:** 30% more writes, but 10-20× faster reads

### Decision 3: UUID for s3_images.image_id

**Approach:** UUID generated in API (NOT database SERIAL)

**Why:**

- Pre-generation before DB insert (idempotency)
- S3 key generation before row exists
- Prevents race conditions in distributed system
- Multiple API servers can generate UUIDs independently

**Trade-off:** 16 bytes vs 8 bytes (acceptable overhead)

### Decision 4: Daily Partitioning for Detections/Estimations

**Approach:** Native PostgreSQL partitions (pg_partman)

**Why:**

- 99% of queries filter by date range
- Partition pruning eliminates 95%+ of data
- VACUUM 100× faster on partitions
- Auto-maintenance with cron

**Trade-off:** Schema complexity vs 10-100× query speedup

**Example:**

```sql
-- Instead of scanning 10M rows
SELECT * FROM detections WHERE created_at >= '2025-10-01';

-- Scans only 1 partition (~30k rows)
SELECT * FROM detections_2025_10_01 WHERE created_at >= '2025-10-01';
```

### Decision 5: PostGIS for Geospatial Queries

**Approach:** `geometry` columns with SP-GiST indexes

**Why:**

- GPS → storage_location lookup via ST_Contains (point-in-polygon)
- Centroid generation, area calculations
- Efficient spatial indexing (SP-GiST optimal for non-overlapping polygons)

**Example:**

```sql
SELECT id, name
FROM storage_locations
WHERE ST_Contains(geojson_coordinates, ST_Point(-70.6483, -33.4489));
```

**Performance:** <50ms for 1000+ locations

---

## Indexing Strategy

### Primary Indexes (Performance-Critical)

```sql
-- Geospatial (SP-GiST)
CREATE INDEX idx_locations_geom ON storage_locations USING GIST(geojson_coordinates);
CREATE INDEX idx_areas_geom ON storage_areas USING GIST(geojson_coordinates);

-- Foreign Keys (for JOINs)
CREATE INDEX idx_batches_bin ON stock_batches(current_storage_bin_id);
CREATE INDEX idx_movements_batch ON stock_movements(batch_id);
CREATE INDEX idx_movements_session ON stock_movements(processing_session_id);

-- Partitioned tables (auto-created per partition)
CREATE INDEX idx_detections_session ON detections(session_id);
CREATE INDEX idx_detections_movement ON detections(stock_movement_id);

-- Compound index for time + spatial queries
CREATE INDEX idx_detections_time_spatial ON detections USING GIST(created_at, point_geom);

-- Unique constraints
CREATE UNIQUE INDEX idx_batches_code ON stock_batches(batch_code);
CREATE UNIQUE INDEX idx_movements_id ON stock_movements(movement_id);
```

### Index Maintenance

- **Auto-VACUUM:** Configured for 5% threshold (vs default 20%)
- **REINDEX:** Monthly on high-churn tables (detections, estimations)
- **Monitoring:** pg_stat_user_indexes to detect unused indexes

---

## Partitioning Configuration

### Detections Table (Daily Partitions)

```sql
CREATE TABLE detections (
    id SERIAL,
    session_id INT NOT NULL,
    stock_movement_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    -- ... other columns
) PARTITION BY RANGE (created_at);

-- Auto-create partitions 7 days ahead
SELECT partman.create_parent(
    'public.detections',
    'created_at',
    'native',
    'daily',
    p_premake := 7,
    p_start_partition := CURRENT_DATE
);

-- Auto-drop partitions older than 90 days
UPDATE partman.part_config
SET retention = '90 days',
    retention_keep_table = false
WHERE parent_table = 'public.detections';

-- Run maintenance every hour
SELECT cron.schedule(
    'detections-maintenance',
    '0 * * * *',
    'SELECT partman.run_maintenance(''public.detections'')'
);
```

**Result:**

- Queries filtering by date: **10-100× faster**
- VACUUM time: **100× faster** (only current partition)
- Storage: Auto-cleanup of old data

---

## N+1 Query Prevention

### Anti-Pattern (N+1)

```python
# BAD: N+1 queries
sessions = await session.execute(select(PhotoProcessingSession))
for s in sessions.scalars():
    print(s.storage_location.name)  # +1 query per session!
    for d in s.detections:  # +N queries!
        print(d.confidence)
```

### Correct Approach (3 queries total)

```python
# GOOD: Eager loading
from sqlalchemy.orm import selectinload, joinedload

stmt = (
    select(PhotoProcessingSession)
    .options(
        joinedload(PhotoProcessingSession.storage_location),  # Many-to-one
        selectinload(PhotoProcessingSession.detections)       # One-to-many
            .selectinload(Detection.classification)
    )
)
result = await session.execute(stmt)
sessions = result.unique().scalars().all()  # .unique() required with joinedload
```

---

## Bulk Insert Optimization

### ORM Approach (Sufficient for Most Cases)

```python
# SQLAlchemy bulk_insert_mappings: 2k rows/sec
await session.execute(
    insert(Detection),
    [
        {"session_id": 123, "center_x_px": 100, ...},
        {"session_id": 123, "center_x_px": 150, ...},
        # ... 1000 rows
    ]
)
```

### asyncpg COPY (350× Faster)

```python
# asyncpg COPY protocol: 714k rows/sec
import asyncpg

pool = await asyncpg.create_pool(DATABASE_URL)

async with pool.acquire() as conn:
    records = [
        (d['session_id'], d['center_x_px'], d['center_y_px'], ...)
        for d in detections
    ]

    await conn.copy_records_to_table(
        'detections',
        records=records,
        columns=['session_id', 'center_x_px', 'center_y_px', ...]
    )
```

**Use Case:** Bulk insert detections after ML processing (1000+ rows)

---

## Migration Strategy

### Alembic for Schema Migrations

**Tool:** Alembic (bundled with SQLAlchemy)

**Workflow:**

```bash
# Create migration
alembic revision --autogenerate -m "add manual_init movement type"

# Review generated migration
# Edit if needed (autogenerate not perfect)

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Best Practices:**

- Test migrations on staging database first
- Always have rollback plan
- Use transactions (default in Alembic)
- Document breaking changes in migration file

---

## Connection Pooling (PgBouncer)

**Recommended for Production**

```ini
[pgbouncer]
pool_mode = transaction               # Best for web apps
max_client_conn = 10000               # High concurrency support
default_pool_size = 25                # Actual DB connections
reserve_pool_size = 5                 # Emergency connections

# Connection lifetime
server_lifetime = 3600                # Recycle after 1 hour
server_idle_timeout = 600             # Close idle after 10 min
```

**Why:**

- API servers can create 1000s of connections
- PostgreSQL default: 100 max connections
- PgBouncer pools connections efficiently
- 10× more concurrent requests supported

---

## Performance Tuning (32GB RAM)

```ini
# postgresql.conf
shared_buffers = 8GB                 # 25% of RAM
effective_cache_size = 24GB          # 75% of RAM
work_mem = 64MB                      # Per sort/hash operation
maintenance_work_mem = 2GB           # For VACUUM, CREATE INDEX

# Query planner
random_page_cost = 1.1               # SSD optimized (vs 4.0 HDD)
effective_io_concurrency = 200       # For SSDs

# Autovacuum
autovacuum_vacuum_scale_factor = 0.05
autovacuum_analyze_scale_factor = 0.02

# Disable JIT for OLTP
jit = off
```

---

## Monitoring Queries

### Slow Queries

```sql
-- Enable pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 slowest queries
SELECT
    substring(query, 1, 100) AS short_query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Index Usage

```sql
-- Unused indexes (candidates for deletion)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Table Bloat

```sql
-- Check tables needing VACUUM
SELECT
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_tup_del > 1000
ORDER BY n_tup_del DESC;
```

---

## Next Steps

- **ERD Diagram:** See [../../database/database.mmd](../../database/database.mmd)
- **Schema Documentation:** See [../../database/database.md](../../database/database.md)
- **Workflows:** See [../workflows/README.md](../workflows/README.md) to understand data flow
- **Backend Implementation:** See [../backend/repository_layer.md](../backend/repository_layer.md)

---

**Document Owner:** DemeterAI Engineering Team
**Last Reviewed:** 2025-10-08
**Database Version:** PostgreSQL 15+, PostGIS 3.3+
