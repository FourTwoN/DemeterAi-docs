# Database Model Cards - Expansion Status Report

**Generated**: 2025-10-09
**Project**: DemeterAI Backend Backlog
**Task**: Expand all database model cards (DB001-DB032)

---

## Executive Summary

**Goal**: Expand all 32 database model stub cards to match the comprehensive quality of DB011-DB014 (detailed cards with 300-400 lines each).

**Progress**:
- ✅ **Completed**: 10 cards fully expanded (DB001-DB006, DB011-DB014)
- 🔄 **In Progress**: 22 cards remaining (DB007-DB010, DB015-DB032)
- **Total Lines Created**: ~2,200 lines of comprehensive documentation

---

## Completed Cards (✅ 10/32)

### Location Hierarchy (DB001-DB006) - **COMPLETED**
| Card | Title | Lines | Priority | Status |
|------|-------|-------|----------|--------|
| DB001 | Warehouses Model - PostGIS Root | 443 | HIGH | ✅ EXPANDED |
| DB002 | StorageAreas Model - Level 2 | 144 | HIGH | ✅ EXPANDED |
| DB003 | StorageLocations Model - Photo Unit | 188 | CRITICAL | ✅ EXPANDED |
| DB004 | StorageBins Model - Container Level | 181 | CRITICAL | ✅ EXPANDED |
| DB005 | StorageBinTypes Model - Catalog | 159 | HIGH | ✅ EXPANDED |
| DB006 | Location Hierarchy Validation Triggers | 267 | MEDIUM | ✅ EXPANDED |

**Key Features Added**:
- PostGIS geometry with SRID 4326 (WGS84)
- GENERATED columns for area_m2 calculations
- Spatial containment validation triggers
- QR code unique constraints for physical tracking
- JSONB position_metadata for ML segmentation results
- Comprehensive geospatial query examples
- Performance expectations (<20ms for most operations)

### ML Pipeline Foundation (DB011-DB014) - **COMPLETED** (Previously)
| Card | Title | Lines | Priority | Status |
|------|-------|-------|----------|--------|
| DB011 | S3Images Model - UUID Primary Key | 305 | CRITICAL | ✅ EXPANDED |
| DB012 | PhotoProcessingSessions Model | 348 | CRITICAL | ✅ EXPANDED |
| DB013 | Detections Model - Partitioned | 385 | CRITICAL | ✅ EXPANDED |
| DB014 | Estimations Model - Partitioned | 397 | CRITICAL | ✅ EXPANDED |

**Key Features**:
- UUID primary keys for S3 pre-generation
- Daily partitioning with pg_partman
- Warning states (not just success/failure)
- asyncpg COPY for bulk inserts (714k rows/sec)
- 90-day retention policies

---

## Remaining Cards (🔄 22/32)

### Stock Management (DB007-DB010) - **4 cards**
| Card | Title | Current Lines | Target Lines | Priority |
|------|-------|---------------|--------------|----------|
| DB007 | StockMovements Model + UUID | 34 (STUB) | ~200 | CRITICAL |
| DB008 | StockBatches Model | 34 (STUB) | ~180 | CRITICAL |
| DB009 | MovementTypes Enum | 34 (STUB) | ~120 | HIGH |
| DB010 | BatchStatus Enum | 34 (STUB) | ~100 | HIGH |

**Expansion Strategy**:
- DB007: UUID for movements, movement_type enum (plantar/sembrar/transplante/muerte/ventas/foto/ajuste/manual_init), source/destination bin FKs, unit_price for COGS
- DB008: Batch lifecycle (quantity_initial vs quantity_current), quality_score, planting/germination/transplant dates, empty_containers tracking
- DB009: Enum definition + business logic for each type, validation rules
- DB010: Enum definition for batch states (active/depleted/moved/archived)

### Product Catalog (DB015-DB019) - **5 cards**
| Card | Title | Current Lines | Target Lines | Priority |
|------|-------|---------------|--------------|----------|
| DB015 | ProductCategories Model | 34 (STUB) | ~100 | HIGH |
| DB016 | ProductFamilies Model | 34 (STUB) | ~120 | HIGH |
| DB017 | Products Model + JSONB | 34 (STUB) | ~160 | HIGH |
| DB018 | ProductStates Enum | 34 (STUB) | ~110 | HIGH |
| DB019 | ProductSizes Enum | 34 (STUB) | ~120 | HIGH |

**Expansion Strategy**:
- Hierarchy: ProductCategory → ProductFamily → Product
- DB017: SKU unique constraint, custom_attributes JSONB for flexible metadata
- DB018: Lifecycle states (seed→seedling→juvenile→adult→flowering), is_sellable flag
- DB019: Size ranges (XS/S/M/L/XL) with min/max height_cm

### Packaging System (DB020-DB023) - **4 cards**
| Card | Title | Current Lines | Target Lines | Priority |
|------|-------|---------------|--------------|----------|
| DB020 | PackagingTypes Model | 34 (STUB) | ~100 | MEDIUM |
| DB021 | PackagingMaterials Model | 34 (STUB) | ~90 | MEDIUM |
| DB022 | PackagingColors Model | 34 (STUB) | ~90 | MEDIUM |
| DB023 | PackagingCatalog Model | 34 (STUB) | ~140 | HIGH |

**Expansion Strategy**:
- Cross-reference model: Type × Material × Color = Catalog SKU
- DB023: Volume_liters, diameter_cm, height_cm for capacity calculations
- Seed data for common pot types (10cm plastic black, 15cm terracotta, etc.)

### Configuration & Pricing (DB024-DB027) - **4 cards**
| Card | Title | Current Lines | Target Lines | Priority |
|------|-------|---------------|--------------|----------|
| DB024 | StorageLocationConfig Model | 34 (STUB) | ~150 | HIGH |
| DB025 | DensityParameters Model | 34 (STUB) | ~160 | CRITICAL |
| DB026 | Classifications Model | 34 (STUB) | ~180 | CRITICAL |
| DB027 | PriceList Model | 34 (STUB) | ~130 | MEDIUM |

**Expansion Strategy**:
- DB024: Expected product/packaging/state for location (validation for manual stock init)
- DB025: Critical for ML band estimation (avg_area_per_plant_cm2, overlap_adjustment_factor)
- DB026: ML classification results (product + size + packaging with confidence scores)
- DB027: Wholesale vs retail pricing, unit_per_storage_box, availability enum

### Users (DB028) - **1 card**
| Card | Title | Current Lines | Target Lines | Priority |
|------|-------|---------------|--------------|----------|
| DB028 | Users Model + Auth | 34 (STUB) | ~140 | HIGH |

**Expansion Strategy**:
- Role enum (admin/supervisor/worker/viewer)
- password_hash (bcrypt), email UK
- active flag, last_login timestamp
- Relationships to stock_movements, photo_processing_sessions

### Migrations (DB029-DB032) - **4 cards**
| Card | Title | Current Lines | Target Lines | Priority |
|------|-------|---------------|--------------|----------|
| DB029 | Initial Schema Migration | 34 (STUB) | ~160 | CRITICAL |
| DB030 | Indexes Migration | 34 (STUB) | ~180 | CRITICAL |
| DB031 | Partitioning Setup (pg_partman) | 34 (STUB) | ~150 | CRITICAL |
| DB032 | Foreign Key Constraints | 34 (STUB) | ~140 | HIGH |

**Expansion Strategy**:
- DB029: All CREATE TABLE, CREATE TYPE, CREATE EXTENSION (postgis, pg_partman, pg_cron)
- DB030: GIST indexes for PostGIS, B-tree for FKs, GIN for JSONB
- DB031: pg_partman configuration for detections/estimations daily partitions, cron jobs
- DB032: All FK constraints with appropriate ON DELETE actions (CASCADE, RESTRICT, SET NULL)

---

## Card Template Structure

Each expanded card follows this structure (based on DB011-DB014):

1. **Metadata** (Epic, Sprint, Status, Priority, Complexity, Dependencies)
2. **Related Documentation** (Links to engineering plan, ERD, workflows)
3. **Description** (What/Why/Context - 3-5 paragraphs)
4. **Acceptance Criteria** (5-7 specific ACs with code examples)
5. **Technical Implementation Notes**
   - Architecture (layer, dependencies, design patterns)
   - Model Signature / Code Hints (Python SQLAlchemy pseudocode)
   - Key Features (validation, triggers, indexes)
6. **Testing Requirements** (Unit + Integration tests with examples, coverage target)
7. **Performance Expectations** (Insert/query/update timings)
8. **Handover Briefing** (Context, key decisions, next steps, validation questions)
9. **Definition of Done Checklist** (10-13 items)
10. **Time Tracking** (Estimated story points, actual TBD)

**Average Length**: 150-250 lines per card (enums shorter, complex models longer)

---

## Quality Standards Applied

All expanded cards include:

✅ **PostgreSQL 18 terminology** (not PG 15)
✅ **Concrete code examples** (not placeholders)
✅ **Performance metrics** (<Xms expectations)
✅ **Relationship definitions** (back_populates, cascade rules)
✅ **Index specifications** (GIST for geometry, B-tree for FKs, GIN for JSONB)
✅ **Validation logic** (@validates decorators, CHECK constraints, triggers)
✅ **Testing strategies** (unit + integration test examples)
✅ **Handover context** (why decisions were made, what to validate)

---

## Next Steps

### Immediate Actions (Complete Remaining 22 Cards)

**Batch 1: Stock Management (DB007-DB010)**
- Critical for inventory tracking
- DB007 is complex (UUID movements, multiple enums, COGS tracking)
- DB008-DB010 are simpler (lifecycle + enums)

**Batch 2: Product Catalog (DB015-DB019)**
- Foundation for classification
- Hierarchy structure (category → family → product)
- Enums for states and sizes

**Batch 3: Packaging (DB020-DB023)**
- Cross-reference model (type × material × color)
- DB023 is the complex one (catalog with dimensions)

**Batch 4: Configuration (DB024-DB027)**
- DB025 and DB026 are CRITICAL for ML
- DB024 for manual stock validation
- DB027 for pricing

**Batch 5: Users + Migrations (DB028-DB032)**
- DB028: Standard auth model
- DB029-DB032: Migration strategy cards (different from model cards)

### Validation Checklist

After completing all cards:
- [ ] All 32 cards have 100+ lines
- [ ] All cards reference database/database.mmd ERD
- [ ] All critical paths have acceptance criteria with code examples
- [ ] All models specify indexes (GIST/B-tree/GIN)
- [ ] All relationships have cascade rules (CASCADE/RESTRICT/SET NULL)
- [ ] All cards have handover briefing section
- [ ] PostgreSQL 18 terminology used throughout (NOT PG 15)

---

## Summary Statistics

**Current State**:
- Total Cards: 32
- Expanded: 10 (31%)
- Remaining: 22 (69%)
- Total Lines Created: ~2,200
- Average Lines per Expanded Card: 220

**Target State**:
- Total Cards: 32
- Expanded: 32 (100%)
- Estimated Total Lines: ~5,500
- Estimated Time to Complete: 4-6 hours

---

**Document Status**: Work in Progress
**Last Updated**: 2025-10-09
**Next Update**: After completing DB007-DB010
