# Sprint 01: Database Models & Repositories
## Sprint Goal

**Duration**: Week 3-4 (Days 11-20)
**Team Capacity**: 80 story points
**Committed**: 75 story points

---

## Goal Statement

> **"Complete all 28 database models + repositories to establish 100% schema coverage, enabling Service layer development in Sprint 03."**

---

## Success Criteria

- [ ] All 28 SQLAlchemy models created and match `database.mmd` ERD exactly
- [ ] AsyncRepository base class implemented with CRUD operations
- [ ] All 28 specialized repositories created (inherit from AsyncRepository)
- [ ] Alembic migrations for complete schema (28 tables)
- [ ] All migrations tested (upgrade + downgrade)
- [ ] Integration tests pass with real test database

---

## Sprint Scope

### In Scope (63 cards, 75 points)

**Database Models (DB001-DB028)**: 40 points
- 4-level location hierarchy (warehouses, areas, locations, bins)
- Stock management (movements, batches)
- Photo processing (sessions, detections, estimations)
- Product catalog (products, families, categories, packaging)
- Configuration (location config, density parameters)
- Users table

**Alembic Migrations (DB029-DB035)**: 10 points
- Create all tables migrations
- Indexes and constraints
- Partitioning setup (detections, estimations)

**Repositories (R001-R028)**: 25 points
- AsyncRepository base class
- 27 specialized repositories with custom query methods

### Out of Scope
- ❌ Service layer (Sprint 03)
- ❌ ML pipeline (Sprint 02)
- ❌ API controllers (Sprint 04)

---

## Key Deliverables

1. `app/models/*.py` - 28 SQLAlchemy models
2. `app/repositories/base.py` - AsyncRepository pattern
3. `app/repositories/*.py` - 27 specialized repositories
4. `alembic/versions/*.py` - Complete schema migrations
5. Integration tests for repository CRUD operations

---

## Dependencies

**Blocked By**: Sprint 00 (F006: Database connection manager, F007: Alembic setup)
**Blocks**: Sprint 03 (Services), Sprint 02 (ML pipeline needs DB models)

---

**Sprint Owner**: Tech Lead
**Last Updated**: 2025-10-09
