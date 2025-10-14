# SPRINT 02 - COMPLETE EXECUTION PLAN

**Sprint**: 02 - ML Pipeline Complete Implementation
**Status**: READY TO START
**Start Date**: 2025-10-14
**Scrum Master**: Claude Code (AI Project Manager)

---

## Executive Summary

Sprint 02 will deliver the **COMPLETE ML Pipeline** for DemeterAI v2.0, enabling CPU-first photo processing with YOLO v11 segmentation, SAHI detection, and band-based estimation. This sprint is the **PROJECT CRITICAL PATH**.

**Scope**:
- **Phase 1**: Complete remaining database models (18 models, ~30 points)
- **Phase 2**: Implement ML Pipeline services (18 services, ~78 points)
- **Total**: 36 tasks, ~108 story points

---

## Phase 1: Complete Database Foundation (18 models, ~30 points)

### Wave 1: Photo Processing Pipeline (DB012-DB014) - CRITICAL

**Priority**: CRITICAL - Blocks ALL ML services

| Task | Model | Story Points | Complexity | Blockers |
|------|-------|--------------|------------|----------|
| DB012 | PhotoProcessingSession | 3 | HIGH | DB011 ✅ |
| DB013 | Detections (Partitioned) | 3 | HIGH | DB012 |
| DB014 | Estimations (Partitioned) | 3 | HIGH | DB013 |

**Dependencies**: DB011 (S3Images) ✅ COMPLETE
**Estimated Time**: 4-6 hours (sequential)
**Key Features**:
- DB012: Session state machine (uploaded → processing → completed/failed)
- DB013: Daily partitioning with pg_partman, asyncpg COPY bulk inserts
- DB014: Band-based estimation results, 90-day retention

---

### Wave 2: Stock Management (DB007-DB010) - HIGH PRIORITY

| Task | Model | Story Points | Complexity | Blockers |
|------|-------|--------------|------------|----------|
| DB009 | MovementTypes Enum | 1 | LOW | DB004 ✅ |
| DB010 | BatchStatus Enum | 1 | LOW | DB004 ✅ |
| DB007 | StockMovements (Event Sourcing) | 3 | HIGH | DB009, DB028 ✅ |
| DB008 | StockBatches (Lifecycle) | 3 | HIGH | DB010, DB004 ✅ |

**Dependencies**: DB004 (StorageBins) ✅, DB028 (Users) ✅ COMPLETE
**Estimated Time**: 4-5 hours
**Key Features**:
- DB007: UUID movements, 8 movement types, COGS tracking
- DB008: Batch lifecycle (quantity_initial vs quantity_current)

---

### Wave 3: Packaging System (DB020-DB023) - MEDIUM PRIORITY

| Task | Model | Story Points | Complexity | Blockers |
|------|-------|--------------|------------|----------|
| DB020 | PackagingTypes | 1 | LOW | None |
| DB021 | PackagingMaterials | 1 | LOW | None |
| DB022 | PackagingColors | 1 | LOW | None |
| DB023 | PackagingCatalog | 2 | MEDIUM | DB020-DB022 |

**Dependencies**: None (independent)
**Estimated Time**: 3-4 hours
**Key Features**:
- Cross-reference model: Type × Material × Color = SKU
- DB023: Volume_liters, diameter_cm, height_cm

---

### Wave 4: Configuration (DB024-DB025, DB027) - HIGH PRIORITY

| Task | Model | Story Points | Complexity | Blockers |
|------|-------|--------------|------------|----------|
| DB024 | StorageLocationConfig | 2 | MEDIUM | DB003 ✅, DB017 ✅ |
| DB025 | DensityParameters | 3 | HIGH | DB005 ✅, DB017 ✅ |
| DB027 | PriceList | 2 | MEDIUM | DB015 ✅ |

**Dependencies**: Product catalog (DB015-DB017) ✅ COMPLETE
**Estimated Time**: 3-4 hours
**Key Features**:
- DB024: Expected product/packaging for location validation
- DB025: CRITICAL for ML band estimation (avg_area_per_plant_cm2)

---

### Wave 5: Migrations (DB029-DB032) - FINAL

| Task | Migration | Story Points | Complexity | Blockers |
|------|-----------|--------------|------------|----------|
| DB029 | Initial Schema | 1 | LOW | ALL models |
| DB030 | Indexes | 1 | LOW | DB029 |
| DB031 | Partitioning Setup (pg_partman) | 2 | MEDIUM | DB030 |
| DB032 | Foreign Key Constraints | 1 | LOW | DB031 |

**Dependencies**: ALL 28 models must be complete
**Estimated Time**: 2-3 hours (sequential)
**Key Features**:
- DB029: All CREATE TABLE, CREATE TYPE, CREATE EXTENSION
- DB031: pg_partman + pg_cron configuration

---

## Phase 2: ML Pipeline Services (18 services, ~78 points)

### Core ML Services (ML001-ML009) - CRITICAL PATH ⚡

| Task | Service | Story Points | Complexity | Priority |
|------|---------|--------------|------------|----------|
| ML001 | Model Singleton (GPU/CPU) | 8 | HIGH | CRITICAL |
| ML002 | YOLO Segmentation | 8 | HIGH | CRITICAL |
| ML003 | SAHI Detection | 8 | HIGH | CRITICAL |
| ML004 | Direct Detection (Boxes/Plugs) | 5 | MEDIUM | HIGH |
| ML005 | Band-Based Estimation | 8 | HIGH | CRITICAL |
| ML006 | Image Processing Utils | 3 | LOW | HIGH |
| ML007 | Mask Generation & Smoothing | 5 | MEDIUM | HIGH |
| ML008 | GPS Extraction & Localization | 3 | LOW | HIGH |
| ML009 | Pipeline Coordinator (Celery Chord) | 8 | HIGH | CRITICAL |

**Total**: 9 services, 56 story points
**Estimated Time**: 14-16 hours
**Dependencies**: DB012-DB014 MUST be complete before starting

---

### Supporting ML Services (ML010-ML018) - MEDIUM PRIORITY

| Task | Service | Story Points | Complexity | Priority |
|------|---------|--------------|------------|----------|
| ML010 | Feathering & Blending | 2 | LOW | MEDIUM |
| ML011 | Cropping & Tiling | 2 | LOW | MEDIUM |
| ML012 | Coordinate Mapping | 3 | MEDIUM | MEDIUM |
| ML013 | Visualization Generation | 2 | LOW | MEDIUM |
| ML014 | Metrics Calculation | 3 | MEDIUM | MEDIUM |
| ML015 | Density Parameter Updates | 3 | MEDIUM | MEDIUM |
| ML016 | Floor Suppression | 2 | LOW | MEDIUM |
| ML017 | Grouping & Clustering | 3 | MEDIUM | MEDIUM |
| ML018 | Error Recovery | 2 | LOW | MEDIUM |

**Total**: 9 services, 22 story points
**Estimated Time**: 6-8 hours

---

## Execution Strategy

### Sequential Waves (Dependencies Matter)

**Week 1 Focus**:
1. **Day 1-2**: Wave 1 (DB012-DB014) - CRITICAL - 9 points
2. **Day 2-3**: Wave 2 (DB007-DB010) - Stock Management - 8 points
3. **Day 3-4**: Wave 3 + Wave 4 (Packaging + Config) - 12 points
4. **Day 4-5**: Wave 5 (Migrations) - 5 points

**CHECKPOINT**: All database models complete (34 points)

**Week 2 Focus**:
5. **Day 6-8**: Core ML Services (ML001-ML009) - CRITICAL - 56 points
6. **Day 9-10**: Supporting ML Services (ML010-ML018) - 22 points

**CHECKPOINT**: Sprint 02 complete (108 points total)

---

## Delegation Workflow

### For Each Task:

1. **Move to ready queue**:
   ```bash
   mv backlog/03_kanban/00_backlog/<TASK>.md backlog/03_kanban/01_ready/
   ```

2. **Delegate with slash command**:
   ```
   /start-task <TASK-ID>
   ```

3. **Team Leader spawns agents in parallel**:
   - Python Expert: Implement code
   - Testing Expert: Write tests (≥80% coverage)

4. **Quality gates**:
   ```
   /review-task <TASK-ID>
   ```

5. **If review passes**:
   ```
   /complete-task <TASK-ID>
   ```

6. **Move to next task**

---

## Success Criteria

### Phase 1 (Database Models) - Definition of Done

For EACH model:
- ✅ SQLAlchemy model with complete type hints
- ✅ Alembic migration (upgrade + downgrade)
- ✅ Unit tests (≥25 tests, ≥80% coverage)
- ✅ Integration tests (≥10 tests)
- ✅ Pre-commit hooks passing (17/17)
- ✅ mypy strict mode: 0 errors
- ✅ ruff linting: 0 violations
- ✅ Git commit with descriptive message

### Phase 2 (ML Services) - Definition of Done

For EACH service:
- ✅ Service class with dependency injection
- ✅ Complete type hints and docstrings
- ✅ Unit tests (≥30 tests, ≥85% coverage)
- ✅ Integration tests (≥15 tests)
- ✅ Performance benchmarks (<10 min CPU, <3 min GPU)
- ✅ Error handling (try/except with custom exceptions)
- ✅ Logging (structured logs with context)
- ✅ Git commit

---

## Risk Mitigation

### High-Risk Tasks

| Task | Risk | Mitigation |
|------|------|------------|
| ML001 | GPU/CPU detection complexity | Test on both CPU and GPU hardware, fallback logic |
| ML003 | SAHI tiling performance | Profile early, optimize tile size (512x512 vs 640x640) |
| ML005 | Band estimation accuracy | Validate against manual counts, auto-calibration |
| ML009 | Celery chord complexity | Unit test each callback, integration test full workflow |
| DB013/DB014 | Partitioning setup | Test pg_partman on staging, verify retention policies |

---

## Velocity Tracking

### Sprint 01 Baseline

- **Velocity**: 11 story points/day (22 points in 2 days)
- **Team**: 1 Scrum Master + 1 Team Leader + 2 Experts (parallel)

### Sprint 02 Projection

- **Estimated Capacity**: 108 story points
- **Timeline**: 10 work days (2 weeks)
- **Target Velocity**: 10-11 story points/day
- **Buffer**: 10% for unexpected complexity

---

## Progress Tracking

### Daily Scrum Updates

**Update `DATABASE_CARDS_STATUS.md` after EVERY task**:

```markdown
## Sprint 02 Progress (YYYY-MM-DD)

### Completed Today
- ✅ DB012: PhotoProcessingSession (3pts) - Moved to 05_done/
- ✅ DB013: Detections (3pts) - Moved to 05_done/

### In Progress
- 🔄 DB014: Estimations (3pts) - In 04_testing/

### Next Up
- DB009: MovementTypes (1pt) - Ready in 01_ready/
- DB010: BatchStatus (1pt) - Ready in 01_ready/

### Velocity
- Today: 6 points completed
- Sprint Total: 9 points (8% of 108 points)
- Days Remaining: 9 days
```

---

## Resource Requirements

### Infrastructure

- **PostgreSQL 18+** with PostGIS 3.4+
- **Redis 7+** for Celery broker
- **Python 3.12** with YOLO v11 dependencies
- **GPU optional** (NVIDIA with CUDA 12+, 8GB+ VRAM)

### Development Tools

- **pytest** for testing
- **mypy** for type checking
- **ruff** for linting
- **pre-commit** hooks
- **Alembic** for migrations

---

## Communication

### Status Updates

- **Daily**: Update `DATABASE_CARDS_STATUS.md`
- **Weekly**: Generate progress report
- **Blockers**: Immediate escalation to Scrum Master
- **Completion**: Sprint 02 summary with metrics

---

## Next Steps (Immediate)

**RIGHT NOW**:

1. Move DB012 (PhotoProcessingSession) to ready queue
2. Execute `/start-task DB012`
3. Track progress through Kanban pipeline
4. Upon completion, immediately start DB013
5. Continue sequential execution through all waves

**GOAL**: Complete Sprint 02 in 10 work days with 100% quality

---

**Plan Created**: 2025-10-14
**Scrum Master**: Claude Code (AI Project Manager)
**Status**: ✅ READY TO EXECUTE
**First Task**: DB012 - PhotoProcessingSession (3pts, HIGH priority)

**🚀 LET'S BUILD THE ML PIPELINE! 🚀**
