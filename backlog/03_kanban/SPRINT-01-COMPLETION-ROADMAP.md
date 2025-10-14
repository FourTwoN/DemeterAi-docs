# Sprint 01 Completion Roadmap - FAST TRACK

**Status**: DB017 (Products) IN PROGRESS - 60-90 minutes to completion
**Objective**: Complete remaining 21 models (22 cards, 25 points) to finish Sprint 01
**Strategy**: Parallel execution + dependency-driven prioritization
**Target**: Complete Sprint 01 within 8-10 hours of focused work

---

## Current State Analysis

### Completed (7 models, 13 points)
- ✅ DB001: Warehouses (8 story points combined with geospatial hierarchy)
- ✅ DB002: StorageAreas
- ✅ DB003: StorageLocations
- ✅ DB004: StorageBins
- ✅ DB005: StorageBinTypes
- ✅ DB015: ProductCategories (1pt)
- ✅ DB016: ProductFamilies (1pt)
- ✅ DB018: ProductStates enum (1pt)
- ✅ DB019: ProductSizes enum (1pt)

### In Progress (1 model, 3 points)
- 🔄 DB017: Products (CRITICAL - 3pts, ~60-90 min remaining)

### Remaining (21 models, 22 cards, 25 points)
**TOTAL SPRINT 01**: 28 models + 4 migrations = 32 cards, 41 points

---

## Dependency Analysis (Critical Path)

### Wave 2: PARALLEL BATCH (Immediately after DB017) - 3 tasks, 4 points
**Start Time**: Once DB017 completes (~60-90 min from now)
**Estimated Duration**: 90-120 minutes (parallel execution)
**Strategy**: 3 tasks with ZERO dependencies on each other

#### Batch 2A: Independent Simple Models (1pt each)
1. **DB026: Classifications** (1pt) - CRITICAL for ML pipeline
   - **Dependencies**: DB017 (Products) ✅
   - **Blocks**: DB013 (Detections), DB014 (Estimations)
   - **Why Priority**: Unblocks ML partitioned tables
   - **Complexity**: SIMPLE (product_id + packaging_id + size_id + confidence fields)
   - **Time**: 45-60 minutes

2. **DB011: S3Images** (2pts) - CRITICAL for photo pipeline
   - **Dependencies**: NONE (independent UUID-based model)
   - **Blocks**: DB012 (PhotoProcessingSessions), ML pipeline
   - **Why Priority**: Foundation of entire ML workflow
   - **Complexity**: MEDIUM (UUID PK, GPS validation, enums)
   - **Time**: 60-90 minutes

3. **DB028: Users** (1pt) - CRITICAL for all user-related FKs
   - **Dependencies**: NONE (independent model)
   - **Blocks**: DB007 (StockMovements.user_id), DB012 (PhotoProcessingSessions)
   - **Why Priority**: Many models have user_id FK
   - **Complexity**: SIMPLE (auth fields, role enum)
   - **Time**: 45-60 minutes

**Parallel Execution**: All 3 can start simultaneously (no dependencies)
**Total Time**: 90-120 minutes (longest task = DB011)

---

### Wave 3: ML Pipeline Foundation - 1 task, 2 points
**Start Time**: After Wave 2 completes (DB011 + DB028 done)
**Estimated Duration**: 60-90 minutes

4. **DB012: PhotoProcessingSessions** (2pts) - CRITICAL for ML
   - **Dependencies**: DB011 (S3Images), DB003 (StorageLocations) ✅, DB028 (Users)
   - **Blocks**: DB013, DB014 (Detections, Estimations - partitioned tables)
   - **Why Priority**: Central ML coordination table
   - **Complexity**: MEDIUM (warning states, enums, cascade deletes)
   - **Time**: 60-90 minutes

---

### Wave 4: PARALLEL STOCK + ML BATCH - 6 tasks, 7 points
**Start Time**: After Wave 3 (DB012 done)
**Estimated Duration**: 120-150 minutes (parallel)
**Strategy**: Split into 2 parallel sub-batches

#### Batch 4A: Stock Management Models (4 tasks, 5 points)
Can execute in parallel:

5. **DB009: MovementTypes Enum** (1pt)
   - **Dependencies**: NONE (enum definition)
   - **Blocks**: DB007 (StockMovements)
   - **Time**: 30-45 minutes

6. **DB010: BatchStatus Enum** (1pt)
   - **Dependencies**: NONE (enum definition)
   - **Blocks**: DB008 (StockBatches)
   - **Time**: 30-45 minutes

7. **DB007: StockMovements** (2pts) - CRITICAL event sourcing
   - **Dependencies**: DB017 (Products) ✅, DB004 (StorageBins) ✅, DB028 (Users)
   - **Blocks**: DB013, DB014 (created stock_movement_id FK)
   - **Complexity**: MEDIUM (UUID movement_id, event sourcing pattern)
   - **Time**: 60-90 minutes

8. **DB008: StockBatches** (2pts) - CRITICAL aggregated state
   - **Dependencies**: DB017 (Products) ✅, DB004 (StorageBins) ✅
   - **Blocks**: DB007 (batch_id FK)
   - **Complexity**: MEDIUM (many FKs, business logic fields)
   - **Time**: 60-90 minutes

**Note**: DB007 and DB008 have circular FK relationship (batch_id ↔ movement_id)
**Solution**: Create both models, then add FK constraints in separate migration

#### Batch 4B: ML Partitioned Tables (2 tasks, 2 points)
Can execute in parallel with Stock Batch:

9. **DB013: Detections (Partitioned)** (1pt)
   - **Dependencies**: DB012 (PhotoProcessingSessions), DB026 (Classifications), DB007 (StockMovements)
   - **Blocks**: None (leaf table)
   - **Complexity**: MEDIUM (partitioned by created_at, bbox geometry)
   - **Time**: 60-90 minutes (includes partitioning setup)

10. **DB014: Estimations (Partitioned)** (1pt)
    - **Dependencies**: DB012 (PhotoProcessingSessions), DB026 (Classifications), DB007 (StockMovements)
    - **Blocks**: None (leaf table)
    - **Complexity**: MEDIUM (partitioned by created_at, polygon geometry, band estimation)
    - **Time**: 60-90 minutes (includes partitioning setup)

**Parallel Execution**: All 6 tasks (4A + 4B) can run simultaneously
**Total Time**: 120-150 minutes (longest tasks = DB007, DB008, DB013, DB014)

---

### Wave 5: Packaging + Configuration - 8 tasks, 9 points
**Start Time**: After Wave 4 completes
**Estimated Duration**: 90-120 minutes (parallel)
**Strategy**: Simple models, all can be done in parallel

#### Batch 5A: Packaging Models (6 tasks, 6 points)
11. **DB020: PackagingTypes** (1pt) - Independent
    - Time: 45-60 min

12. **DB021: PackagingMaterials** (1pt) - Independent
    - Time: 45-60 min

13. **DB022: PackagingColors** (1pt) - Independent
    - Time: 45-60 min

14. **DB023: PackagingCatalog** (1pt)
    - Dependencies: DB020, DB021, DB022
    - Time: 60-75 min (waits for above 3)

15. **DB027: PriceList** (1pt)
    - Dependencies: DB023 (PackagingCatalog), DB015 (ProductCategories) ✅
    - Time: 45-60 min

16. **DB006: ProductSampleImages** (1pt)
    - Dependencies: DB017 (Products) ✅, DB011 (S3Images)
    - Time: 45-60 min

#### Batch 5B: Configuration Models (2 tasks, 3 points)
17. **DB024: StorageLocationConfig** (2pts)
    - Dependencies: DB003 (StorageLocations) ✅, DB017 (Products) ✅, DB023 (PackagingCatalog)
    - Time: 60-90 min

18. **DB025: DensityParameters** (1pt)
    - Dependencies: DB005 (StorageBinTypes) ✅, DB017 (Products) ✅, DB023 (PackagingCatalog)
    - Time: 45-60 min

**Parallel Execution**: Start DB020, DB021, DB022 immediately; others follow as dependencies resolve
**Total Time**: 90-120 minutes

---

### Wave 6: Migrations - 4 tasks, 4 points
**Start Time**: After all models complete
**Estimated Duration**: 60-90 minutes (sequential)

19. **DB029: InitialMigration** (1pt)
    - Consolidate all model migrations
    - Time: 30-45 min

20. **DB030: IndexesMigration** (1pt)
    - Add performance indexes
    - Time: 30-45 min

21. **DB031: PartitioningSetup** (1pt)
    - Configure daily partitions for DB013, DB014
    - Time: 30-45 min

22. **DB032: FKConstraints** (1pt)
    - Add all foreign key constraints
    - Time: 30-45 min

**Sequential Execution**: Must run in order
**Total Time**: 60-90 minutes

---

## Execution Timeline (Optimistic)

### Phase 1: Current (DB017 in progress)
- **Now → +90 min**: DB017 completes

### Phase 2: Wave 2 (Parallel Batch)
- **+0 → +120 min**: DB026, DB011, DB028 (parallel)
- **Cumulative**: 210 minutes (3.5 hours)

### Phase 3: Wave 3 (ML Foundation)
- **+0 → +90 min**: DB012 (PhotoProcessingSessions)
- **Cumulative**: 300 minutes (5 hours)

### Phase 4: Wave 4 (Stock + ML Partitioned)
- **+0 → +150 min**: DB009, DB010, DB007, DB008, DB013, DB014 (parallel)
- **Cumulative**: 450 minutes (7.5 hours)

### Phase 5: Wave 5 (Packaging + Config)
- **+0 → +120 min**: DB020-DB027 (parallel batches)
- **Cumulative**: 570 minutes (9.5 hours)

### Phase 6: Wave 6 (Migrations)
- **+0 → +90 min**: DB029-DB032 (sequential)
- **Cumulative**: 660 minutes (11 hours)

**TOTAL ESTIMATED TIME**: 11 hours of focused work
**With breaks + reviews**: 12-14 hours (1.5-2 work days)

---

## Risk Mitigation

### Known Challenges

1. **Circular FK (DB007 ↔ DB008)**
   - **Risk**: Alembic may fail to create circular foreign keys
   - **Solution**: Create models first, add FKs in DB032 migration

2. **Partitioned Tables (DB013, DB014)**
   - **Risk**: First time implementing daily partitions
   - **Solution**: Use PostgreSQL 10+ native partitioning (simpler than pg_partman)

3. **UUID Primary Key (DB011)**
   - **Risk**: API-level UUID generation not database default
   - **Solution**: Document clearly in model docstring, add validation tests

4. **Parallel Execution Coordination**
   - **Risk**: Multiple developers working simultaneously may conflict
   - **Solution**: Use git feature branches per model, merge to main sequentially

### Quality Gates (Non-Negotiable)

- [ ] All models match database.mmd ERD exactly
- [ ] All tests pass with ≥80% coverage
- [ ] Pre-commit hooks pass (ruff, mypy, formatting)
- [ ] Alembic migrations tested (upgrade + downgrade)
- [ ] No circular import issues
- [ ] All relationships tested (bidirectional)

---

## Next Actions (Immediately After DB017)

### Action 1: Delegate Wave 2 Tasks (3 tasks)
```bash
# Move to ready queue
mv backlog/03_kanban/00_backlog/DB026-*.md backlog/03_kanban/01_ready/
mv backlog/03_kanban/00_backlog/DB011-*.md backlog/03_kanban/01_ready/
mv backlog/03_kanban/00_backlog/DB028-*.md backlog/03_kanban/01_ready/
```

### Action 2: Create Mini-Plans
- DB026-mini-plan.md (Classifications strategy)
- DB011-mini-plan.md (UUID + GPS validation strategy)
- DB028-mini-plan.md (User auth + role enum strategy)

### Action 3: Spawn Parallel Agents
- Python Expert + Testing Expert for DB026
- Python Expert + Testing Expert for DB011
- Python Expert + Testing Expert for DB028

**All 3 tasks start SIMULTANEOUSLY** - no waiting!

---

## Success Metrics

### Velocity Target
- **Average**: 2-3 story points per hour (with parallel execution)
- **Sprint 01 Remaining**: 25 points in 11 hours = 2.3 pts/hour ✅ ACHIEVABLE

### Quality Metrics
- Test coverage: ≥80% (current: 85% average)
- Pre-commit pass rate: 100% (current: 17/17 hooks passing)
- Migration success: 100% (upgrade + downgrade)

### Sprint Completion
- **Goal**: 28 models + 4 migrations = 32 cards, 41 points
- **Current**: 9 complete, 1 in progress, 22 remaining
- **Target Date**: End of Day 2 (assuming 8-hour work days)

---

**Document Status**: ACTIVE ROADMAP
**Last Updated**: 2025-10-14 19:00
**Next Update**: After DB017 completion (Wave 2 delegation)
