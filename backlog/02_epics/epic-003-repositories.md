# Epic 003: Repository Layer

**Status**: Not Started
**Sprint**: Sprint-01 (Week 3-4)
**Priority**: high (blocks service layer)
**Total Story Points**: 25
**Total Cards**: 28 (R001-R028)

---

## Goal

Implement complete data access layer using AsyncRepository pattern with specialized query methods for all 28 database models.

---

## Success Criteria

- [ ] AsyncRepository base class with CRUD operations
- [ ] All 28 specialized repositories inherit from base
- [ ] N+1 query prevention (eager loading patterns)
- [ ] Unit tests ≥85% coverage
- [ ] Integration tests with real test database

---

## Cards List (28 cards, 25 points)

### Base Repository (3 points)
- **R001**: AsyncRepository base class (get, get_multi, create, update, delete) (3pts)

### Location Repositories (4 points)
- **R002**: WarehouseRepository (1pt)
- **R003**: StorageAreaRepository (1pt)
- **R004**: StorageLocationRepository (geospatial queries) (1pt)
- **R005**: StorageBinRepository (1pt)

### Stock Repositories (3 points)
- **R006**: StockMovementRepository (date range, location filters) (2pts)
- **R007**: StockBatchRepository (aggregation queries) (1pt)

### Photo Processing Repositories (4 points)
- **R008**: S3ImageRepository (1pt)
- **R009**: PhotoSessionRepository (2pts)
- **R010**: DetectionRepository (partitioned table queries) (1pt)
- **R011**: EstimationRepository (partitioned table queries) (1pt)

### Product Repositories (5 points)
- **R012**: ProductCategoryRepository (1pt)
- **R013**: ProductFamilyRepository (1pt)
- **R014**: ProductRepository (1pt)
- **R015**: PackagingCatalogRepository (1pt)
- **R016**: ClassificationRepository (1pt)

### Configuration Repositories (2 points)
- **R017**: StorageLocationConfigRepository (1pt)
- **R018**: DensityParameterRepository (auto-calibration queries) (1pt)

### Additional Repositories (4 points)
- **R019-R028**: Remaining model repositories (0.5pt each = 4pts total)

---

## Dependencies

**Blocked By**: Epic-002 (DB models)
**Blocks**: Epic-004, Epic-005, Epic-006 (Services need repositories)

---

## Key Patterns

**N+1 Prevention**:
```python
stmt = (
    select(StockMovement)
    .options(
        joinedload(StockMovement.location),  # Many-to-one
        selectinload(StockMovement.batch)    # One-to-many
    )
)
```

**Bulk Operations**: Use asyncpg COPY for 1000+ rows (714k rows/sec)

---

**Epic Owner**: Backend Lead
**Created**: 2025-10-09
