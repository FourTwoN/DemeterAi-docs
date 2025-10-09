# Epic 002: Database Models & Migrations

**Status**: Not Started
**Sprint**: Sprint-01 (Week 3-4)
**Priority**: high (blocks services and ML pipeline)
**Total Story Points**: 40
**Total Cards**: 35 (DB001-DB035)

---

## Goal

Create all 28 SQLAlchemy models matching the database ERD exactly, with complete Alembic migrations and partitioning setup for high-volume tables.

---

## Success Criteria

- [ ] All 28 models created and match `database/database.mmd` ERD
- [ ] Alembic migrations run successfully (upgrade + downgrade tested)
- [ ] Daily partitioning configured for detections/estimations
- [ ] All foreign key relationships validated
- [ ] Integration tests pass with real test database

---

## Cards List (35 cards, 40 points)

### Location Hierarchy Models (6 points)
- **DB001**: Warehouses model (1pt)
- **DB002**: StorageAreas model (1pt)
- **DB003**: StorageLocations model (1pt)
- **DB004**: StorageBins model (1pt)
- **DB005**: StorageBinTypes model (1pt)
- **DB006**: Location relationships & geospatial (1pt)

### Stock Management Models (6 points)
- **DB007**: StockMovements model (2pts)
- **DB008**: StockBatches model (2pts)
- **DB009**: Movement types enum (1pt)
- **DB010**: Batch status enum (1pt)

### Photo Processing Models (8 points)
- **DB011**: S3Images model (UUID primary key) (2pts)
- **DB012**: PhotoProcessingSessions model (2pts)
- **DB013**: Detections model (partitioned) (2pts)
- **DB014**: Estimations model (partitioned) (2pts)

### Product Catalog Models (10 points)
- **DB015**: ProductCategories model (1pt)
- **DB016**: ProductFamilies model (1pt)
- **DB017**: Products model (2pts)
- **DB018**: ProductStates enum (1pt)
- **DB019**: ProductSizes enum (1pt)
- **DB020**: PackagingTypes model (1pt)
- **DB021**: Materials model (1pt)
- **DB022**: Colors model (1pt)
- **DB023**: PackagingCatalog model (1pt)

### Configuration Models (4 points)
- **DB024**: StorageLocationConfig model (2pts)
- **DB025**: DensityParameters model (2pts)

### Classification & Pricing (3 points)
- **DB026**: Classifications model (1pt)
- **DB027**: PriceList model (2pts)

### Users (1 point)
- **DB028**: Users model (1pt)

### Alembic Migrations (7 points)
- **DB029**: Initial schema migration (all tables) (2pts)
- **DB030**: Indexes migration (SP-GiST, B-tree) (2pts)
- **DB031**: Partitioning setup (detections, estimations) (2pts)
- **DB032**: Foreign key constraints validation (1pt)

---

## Dependencies

**Blocked By**: Epic-001 (F006: DB connection, F007: Alembic setup)
**Blocks**: Epic-003 (Repositories), Epic-007 (ML Pipeline)

---

## Technical Decisions

**UUID vs SERIAL**: s3_images.image_id uses UUID (generated in API, not DB)
**Partitioning**: Daily partitions for detections/estimations (pg_partman)
**Geospatial**: PostGIS GEOMETRY columns with SP-GiST indexes
**Relationships**: SQLAlchemy relationship() with lazy='selectinload' default

---

**Epic Owner**: Database Architect
**Created**: 2025-10-09
