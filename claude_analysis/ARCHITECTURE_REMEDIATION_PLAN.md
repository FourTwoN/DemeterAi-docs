# Architecture Remediation Plan - Sprint 04 Controllers

## Team Leader Mini-Plan

**Created**: 2025-10-21
**Priority**: CRITICAL
**Complexity**: 13 points (High)
**Type**: Refactoring / Architecture Fix
**Impact**: 6 controllers, 26+ endpoints, entire API layer

---

## Executive Summary

**Problem**: Controllers directly import and instantiate Repositories, violating Clean Architecture.

**Root Cause**: No centralized dependency injection system. Each controller manually creates
repository instances in dependency functions, creating tight coupling and making testing impossible.

**Solution**: Implement Service Factory pattern with centralized dependency injection.

**Affected Components**:

- stock_controller.py (7 endpoints)
- product_controller.py (6 endpoints)
- location_controller.py (6 endpoints)
- config_controller.py (3 endpoints)
- analytics_controller.py (3 endpoints)
- **TOTAL**: 5 controllers, 25+ endpoints

---

## Architecture Violations Identified

### CRITICAL Violations

#### 1. **stock_controller.py** (Lines 33-34, 86, 98, 114-115)

```python
# VIOLATION: Direct repository imports
from app.repositories.stock_batch_repository import StockBatchRepository
from app.repositories.stock_movement_repository import StockMovementRepository


# VIOLATION: Controller manually instantiates repositories
def get_stock_movement_service(session):
  movement_repo = StockMovementRepository(session)  # ❌ Should use factory
  return StockMovementService(movement_repo)
```

**Impact**: 7 endpoints affected (POST /photo, POST /manual, etc.)

#### 2. **product_controller.py** (Lines 30-32, 60, 69-70, 78-80)

```python
# VIOLATION: Direct repository imports
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository
from app.repositories.product_repository import ProductRepository


# VIOLATION: Manual instantiation in EVERY endpoint dependency
def get_product_service(session):
  product_repo = ProductRepository(session)  # ❌
  category_repo = ProductCategoryRepository(session)  # ❌
  family_repo = ProductFamilyRepository(session)  # ❌
```

**Impact**: 6 endpoints affected (GET /categories, POST /products, etc.)

#### 3. **location_controller.py** (Lines 28-31, 56, 65-66, 74-76, etc.)

```python
# VIOLATION: Direct repository imports
from app.repositories.storage_area_repository import StorageAreaRepository
from app.repositories.storage_bin_repository import StorageBinRepository
from app.repositories.storage_location_repository import StorageLocationRepository
from app.repositories.warehouse_repository import WarehouseRepository


# VIOLATION: Repeated manual instantiation
def get_location_hierarchy_service(session):
  warehouse_repo = WarehouseRepository(session)  # ❌
  area_repo = StorageAreaRepository(session)  # ❌
  location_repo = StorageLocationRepository(session)  # ❌
  bin_repo = StorageBinRepository(session)  # ❌
```

**Impact**: 6 endpoints affected (GET /warehouses, GET /search, etc.)

#### 4. **config_controller.py** (Lines 25-28, 51, 59)

```python
# VIOLATION: Direct repository imports
from app.repositories.density_parameter_repository import DensityParameterRepository
from app.repositories.storage_location_config_repository import StorageLocationConfigRepository
```

**Impact**: 3 endpoints affected

#### 5. **analytics_controller.py** (Lines 28, 46)

```python
# VIOLATION: Direct repository import
from app.repositories.stock_batch_repository import StockBatchRepository


def get_analytics_service(session):
  stock_batch_repo = StockBatchRepository(session)  # ❌
```

**Impact**: 3 endpoints affected

---

## Solution Architecture

### Service Factory Pattern

**File**: `/home/lucasg/proyectos/DemeterDocs/app/factories/service_factory.py`

**Responsibility**: Centralized dependency injection for ALL services.

**Benefits**:

1. **Single Source of Truth**: All service dependencies in one place
2. **Testability**: Easy to mock factory for testing
3. **Maintainability**: Change service dependencies in one location
4. **Type Safety**: Proper type hints throughout
5. **Lazy Loading**: Services created only when needed

### Design Pattern

```python
# app/factories/service_factory.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession


class ServiceFactory:
  """Centralized service factory for dependency injection.

  Pattern: Factory + Singleton (per session)
  Lifecycle: One factory per database session
  Thread-safety: Each async request gets own session
  """

  def __init__(self, session: AsyncSession):
    self.session = session

    # Cache service instances (lazy loading)
    self._services: dict = {}

  # Level 1: Repository-only services (no dependencies)
  def get_warehouse_service(self) -> WarehouseService:
    if 'warehouse' not in self._services:
      repo = WarehouseRepository(self.session)
      self._services['warehouse'] = WarehouseService(repo)
    return self._services['warehouse']

  # Level 2: Services with service dependencies
  def get_storage_area_service(self) -> StorageAreaService:
    if 'storage_area' not in self._services:
      repo = StorageAreaRepository(self.session)
      warehouse_service = self.get_warehouse_service()  # ✅ Service dependency
      self._services['storage_area'] = StorageAreaService(repo, warehouse_service)
    return self._services['storage_area']

  # Level 3: Complex services (multiple dependencies)
  def get_location_hierarchy_service(self) -> LocationHierarchyService:
    if 'location_hierarchy' not in self._services:
      self._services['location_hierarchy'] = LocationHierarchyService(
          warehouse_service=self.get_warehouse_service(),
          area_service=self.get_storage_area_service(),
          location_service=self.get_storage_location_service(),
          bin_service=self.get_storage_bin_service(),
      )
    return self._services['location_hierarchy']
```

### Controller Pattern (After Refactoring)

```python
# app/controllers/product_controller.py (AFTER)
from app.factories.service_factory import ServiceFactory


# ✅ CORRECT: Get factory, not individual repos
def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
  return ServiceFactory(session)


# ✅ CORRECT: Controller uses factory to get services
@router.get("/products")
async def list_products(
    factory: ServiceFactory = Depends(get_factory)
) -> list[ProductResponse]:
  service = factory.get_product_service()  # ✅ No repo knowledge
  return await service.get_all()
```

---

## Implementation Plan

### Phase 1: Create Service Factory (1 file, ~500 lines)

**File**: `app/factories/service_factory.py`

**Tasks**:

1. Create factory class with session injection
2. Implement service getters for all 30+ services
3. Implement lazy loading with caching
4. Add comprehensive type hints
5. Add docstrings for every method

**Dependencies**: NONE (can start immediately)

**Estimated Time**: 3 hours

**Service Count**: 35 services

- Warehouse hierarchy: 4 services (WarehouseService, StorageAreaService, etc.)
- Product taxonomy: 5 services (ProductCategoryService, ProductFamilyService, etc.)
- Stock management: 4 services (StockBatchService, StockMovementService, etc.)
- Photo/ML pipeline: 6 services (PhotoUploadService, DetectionService, etc.)
- Analytics: 1 service
- Configuration: 2 services
- Others: 13 services

**Acceptance Criteria**:

- [ ] ServiceFactory class created with __init__(session)
- [ ] All 35 services have getter methods
- [ ] Lazy loading implemented (services cached in self._services)
- [ ] Type hints on all methods
- [ ] No repository imports in controllers (after refactor)
- [ ] Factory can be instantiated: `factory = ServiceFactory(session)`

---

### Phase 2: Refactor Controllers (5 files, ~200 lines modified)

**Order**: Simplest to most complex (dependency order)

#### 2.1. **config_controller.py** (EASIEST - 2 services, 3 endpoints)

**Changes**:

```python
# BEFORE (lines 25-28)
from app.repositories.density_parameter_repository import DensityParameterRepository
from app.repositories.storage_location_config_repository import StorageLocationConfigRepository

# AFTER
from app.factories.service_factory import ServiceFactory


# BEFORE (lines 47-52, 55-60)
def get_storage_location_config_service(session):
  config_repo = StorageLocationConfigRepository(session)  # ❌
  return StorageLocationConfigService(config_repo)


# AFTER
def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
  return ServiceFactory(session)


@router.get("/location-defaults")
async def get_location_defaults(
    location_id: int,
    factory: ServiceFactory = Depends(get_factory)  # ✅
):
  service = factory.get_storage_location_config_service()
  # ... rest unchanged
```

**Lines Modified**: ~30 lines
**Endpoints Affected**: 3
**Estimated Time**: 30 minutes
**Risk**: LOW

**Acceptance Criteria**:

- [ ] No repository imports in config_controller.py
- [ ] All dependency functions use get_factory()
- [ ] All endpoints work (run tests)
- [ ] No changes to endpoint signatures

#### 2.2. **analytics_controller.py** (EASY - 1 service, 3 endpoints)

**Changes**:

```python
# BEFORE (line 28)
from app.repositories.stock_batch_repository import StockBatchRepository

# AFTER
from app.factories.service_factory import ServiceFactory


# BEFORE (lines 42-47)
def get_analytics_service(session):
  stock_batch_repo = StockBatchRepository(session)  # ❌
  return AnalyticsService(stock_batch_repo)


# AFTER
def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
  return ServiceFactory(session)


@router.get("/daily-counts")
async def get_daily_plant_counts(
    factory: ServiceFactory = Depends(get_factory)  # ✅
):
  service = factory.get_analytics_service()
  # ... rest unchanged
```

**Lines Modified**: ~25 lines
**Endpoints Affected**: 3
**Estimated Time**: 30 minutes
**Risk**: LOW

**Acceptance Criteria**:

- [ ] No repository imports
- [ ] All endpoints use factory
- [ ] Tests pass

#### 2.3. **product_controller.py** (MEDIUM - 3 services, 6 endpoints)

**Changes**:

```python
# BEFORE (lines 30-32)
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository
from app.repositories.product_repository import ProductRepository

# AFTER
from app.factories.service_factory import ServiceFactory


# BEFORE (lines 56-85) - 3 separate dependency functions
def get_product_category_service(session):
  category_repo = ProductCategoryRepository(session)  # ❌
  return ProductCategoryService(category_repo)


def get_product_family_service(session):
  family_repo = ProductFamilyRepository(session)  # ❌
  category_repo = ProductCategoryRepository(session)  # ❌
  category_service = ProductCategoryService(category_repo)  # ❌
  return ProductFamilyService(family_repo, category_service)


def get_product_service(session):
  product_repo = ProductRepository(session)  # ❌
  category_repo = ProductCategoryRepository(session)  # ❌
  family_repo = ProductFamilyRepository(session)  # ❌
  # ...


# AFTER (ONE dependency function)
def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
  return ServiceFactory(session)


# Update ALL endpoints
@router.get("/categories")
async def list_product_categories(
    factory: ServiceFactory = Depends(get_factory)  # ✅
):
  service = factory.get_product_category_service()
  # ... rest unchanged
```

**Lines Modified**: ~60 lines (3 dependency functions → 1)
**Endpoints Affected**: 6
**Estimated Time**: 1 hour
**Risk**: MEDIUM (service dependency chain)

**Acceptance Criteria**:

- [ ] No repository imports
- [ ] All 6 endpoints use factory
- [ ] Service dependencies correct (ProductFamilyService needs ProductCategoryService)
- [ ] Tests pass (especially product creation with SKU)

#### 2.4. **stock_controller.py** (HARD - 6 services, 7 endpoints)

**Changes**:

```python
# BEFORE (lines 33-34)
from app.repositories.stock_batch_repository import StockBatchRepository
from app.repositories.stock_movement_repository import StockMovementRepository

# AFTER
from app.factories.service_factory import ServiceFactory


# BEFORE (lines 61-122) - 4 dependency functions with nested repo creation
def get_photo_upload_service(session):
  # Nested imports ❌
  from app.repositories.photo_processing_session_repository import PhotoProcessingSessionRepository
  from app.repositories.s3_image_repository import S3ImageRepository
  from app.repositories.warehouse_repository import WarehouseRepository

  session_repo = PhotoProcessingSessionRepository(session)  # ❌
  s3_repo = S3ImageRepository(session)  # ❌
  warehouse_repo = WarehouseRepository(session)  # ❌

  session_service = PhotoProcessingSessionService(session_repo)  # ❌
  s3_service = S3ImageService(s3_repo)  # ❌
  location_service = LocationHierarchyService(warehouse_repo)  # ❌

  return PhotoUploadService(session_service, s3_service, location_service)


# ... 3 more complex functions

# AFTER (ONE dependency function)
def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
  return ServiceFactory(session)


# Update ALL endpoints
@router.post("/photo")
async def upload_photo_for_stock_count(
    file: UploadFile,
    factory: ServiceFactory = Depends(get_factory)  # ✅
):
  service = factory.get_photo_upload_service()
  # ... rest unchanged
```

**Lines Modified**: ~90 lines (4 dependency functions → 1)
**Endpoints Affected**: 7
**Estimated Time**: 1.5 hours
**Risk**: HIGH (complex service dependencies, nested imports)

**Acceptance Criteria**:

- [ ] No repository imports (including nested)
- [ ] All 7 endpoints use factory
- [ ] PhotoUploadService dependencies correct
- [ ] BatchLifecycleService dependencies correct
- [ ] Tests pass (especially photo upload workflow)

#### 2.5. **location_controller.py** (VERY HARD - 5 services, 6 endpoints)

**Changes**:

```python
# BEFORE (lines 28-31)
from app.repositories.storage_area_repository import StorageAreaRepository
from app.repositories.storage_bin_repository import StorageBinRepository
from app.repositories.storage_location_repository import StorageLocationRepository
from app.repositories.warehouse_repository import WarehouseRepository

# AFTER
from app.factories.service_factory import ServiceFactory


# BEFORE (lines 52-118) - 5 dependency functions, LOTS of duplication
def get_warehouse_service(session):
  warehouse_repo = WarehouseRepository(session)  # ❌
  return WarehouseService(warehouse_repo)


def get_storage_area_service(session):
  area_repo = StorageAreaRepository(session)  # ❌
  warehouse_repo = WarehouseRepository(session)  # ❌ DUPLICATE
  warehouse_service = WarehouseService(warehouse_repo)  # ❌ DUPLICATE
  return StorageAreaService(area_repo, warehouse_service)


def get_storage_location_service(session):
  location_repo = StorageLocationRepository(session)  # ❌
  area_repo = StorageAreaRepository(session)  # ❌ DUPLICATE
  warehouse_repo = WarehouseRepository(session)  # ❌ DUPLICATE
  warehouse_service = WarehouseService(warehouse_repo)  # ❌ DUPLICATE
  area_service = StorageAreaService(area_repo, warehouse_service)  # ❌ DUPLICATE
  return StorageLocationService(location_repo, area_service)


# ... even MORE duplication for bin_service and hierarchy_service

# AFTER (ONE dependency function, NO duplication)
def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
  return ServiceFactory(session)


@router.get("/warehouses")
async def list_warehouses(
    factory: ServiceFactory = Depends(get_factory)  # ✅
):
  service = factory.get_warehouse_service()
  # ... rest unchanged
```

**Lines Modified**: ~100 lines (5 dependency functions → 1, eliminate 50+ lines of duplication)
**Endpoints Affected**: 6
**Estimated Time**: 2 hours
**Risk**: VERY HIGH (most complex service dependency chain in entire project)

**Acceptance Criteria**:

- [ ] No repository imports
- [ ] All 6 endpoints use factory
- [ ] LocationHierarchyService dependencies correct (needs all 4 hierarchy services)
- [ ] No code duplication (factory handles service creation)
- [ ] Tests pass (especially GPS lookup)

---

### Phase 3: Integration Testing (ALL controllers)

**Tasks**:

1. Run all controller tests
2. Verify no endpoint behavior changed
3. Verify service dependencies correct
4. Check for import errors
5. Validate type hints

**Test Commands**:

```bash
# Test each controller individually
pytest tests/integration/test_config_controller.py -v
pytest tests/integration/test_analytics_controller.py -v
pytest tests/integration/test_product_controller.py -v
pytest tests/integration/test_stock_controller.py -v
pytest tests/integration/test_location_controller.py -v

# Run all controller tests
pytest tests/integration/ -v -k "controller"

# Verify imports work
python -c "from app.factories.service_factory import ServiceFactory; print('✅ Factory OK')"
python -c "from app.controllers import *; print('✅ Controllers OK')"
```

**Acceptance Criteria**:

- [ ] All controller tests pass
- [ ] No import errors
- [ ] No endpoint behavior changes
- [ ] ServiceFactory can be instantiated
- [ ] Type hints correct (mypy passes)

**Estimated Time**: 1 hour

---

## Risk Assessment

### High-Risk Areas

#### 1. **Service Dependency Chains**

**Problem**: Services depend on other services (e.g., ProductFamilyService needs
ProductCategoryService)

**Mitigation**:

- Factory handles dependency order
- Lazy loading prevents circular dependencies
- Test each service getter individually

#### 2. **Nested Imports in stock_controller.py**

**Problem**: Lines 65-69 have nested repository imports inside dependency function

**Mitigation**:

- Factory replaces ALL nested imports
- Test photo upload workflow specifically

#### 3. **LocationHierarchyService Complexity**

**Problem**: Needs 4 service dependencies (warehouse, area, location, bin)

**Mitigation**:

- Factory ensures correct instantiation order
- Test GPS lookup endpoint (most complex usage)

#### 4. **Testing Difficulty**

**Problem**: No existing controller tests

**Mitigation**:

- Create smoke tests for each endpoint first
- Verify endpoints return expected status codes
- Add comprehensive tests after refactor

---

## Quality Gates

### Before Starting Implementation

- [ ] All existing tests pass (baseline)
- [ ] Database schema matches models
- [ ] All services exist and are importable

### After Phase 1 (Factory Creation)

- [ ] ServiceFactory can be instantiated
- [ ] All service getters work
- [ ] No import errors
- [ ] Type hints correct (mypy passes)
- [ ] Factory tests written (unit tests for each getter)

### After Each Controller (Phase 2)

- [ ] No repository imports in controller
- [ ] All endpoints use factory
- [ ] Endpoint tests pass
- [ ] No behavior changes (same responses)
- [ ] Type hints correct

### Final (Phase 3)

- [ ] All 5 controllers refactored
- [ ] All controller tests pass
- [ ] No import errors in entire app
- [ ] Type hints correct (mypy app/controllers/)
- [ ] No code duplication in dependency functions
- [ ] ServiceFactory used consistently across all controllers

---

## Files Modified

### New Files (1)

- `app/factories/__init__.py` (exports ServiceFactory)
- `app/factories/service_factory.py` (~500 lines)

### Modified Files (5 controllers)

1. `app/controllers/config_controller.py` (~30 lines changed)
2. `app/controllers/analytics_controller.py` (~25 lines changed)
3. `app/controllers/product_controller.py` (~60 lines changed)
4. `app/controllers/stock_controller.py` (~90 lines changed)
5. `app/controllers/location_controller.py` (~100 lines changed)

**Total Lines Modified**: ~305 lines
**Total Lines Deleted**: ~150 lines (duplication removed)
**Net Change**: ~+155 lines + new factory file (~500 lines)

---

## Timeline Estimate

| Phase     | Task                             | Time     | Risk      |
|-----------|----------------------------------|----------|-----------|
| 1         | Create ServiceFactory            | 3h       | LOW       |
| 2.1       | Refactor config_controller.py    | 0.5h     | LOW       |
| 2.2       | Refactor analytics_controller.py | 0.5h     | LOW       |
| 2.3       | Refactor product_controller.py   | 1h       | MEDIUM    |
| 2.4       | Refactor stock_controller.py     | 1.5h     | HIGH      |
| 2.5       | Refactor location_controller.py  | 2h       | VERY HIGH |
| 3         | Integration testing              | 1h       | MEDIUM    |
| **TOTAL** |                                  | **9.5h** |           |

**Estimated Story Points**: 13 (High complexity)

**Parallel Work Opportunities**:

- Phase 1 (Factory) must be done first (blocking)
- Phase 2.1 and 2.2 can be done in parallel (independent)
- Phase 2.3, 2.4, 2.5 should be sequential (increasing complexity)

---

## Success Metrics

### Code Quality

- **Before**: 5 controllers with 200+ lines of repository instantiation code
- **After**: 5 controllers with 1 line dependency injection each
- **Code Reduction**: ~150 lines eliminated (duplication)

### Architecture Compliance

- **Before**: 5 controllers violating Clean Architecture (Controller→Repo)
- **After**: 0 violations (Controller→Factory→Service→Repo)

### Testability

- **Before**: Controllers cannot be unit tested (hard-coded repo instantiation)
- **After**: Controllers fully testable (factory can be mocked)

### Maintainability

- **Before**: Service dependencies scattered across 20+ dependency functions
- **After**: Service dependencies centralized in 1 factory file

---

## Rollback Plan

**If integration tests fail after refactoring a controller**:

1. Revert controller file: `git checkout HEAD app/controllers/{controller_name}.py`
2. Keep factory file (it's reusable)
3. Fix issue in factory
4. Re-attempt controller refactor

**If factory has fundamental issue**:

1. Revert all changes: `git checkout HEAD app/`
2. Create new branch with different approach
3. Consider alternative: FastAPI dependency overrides pattern

---

## Next Steps for Python Expert

**After Team Leader approval**:

1. **Start Phase 1**: Create `app/factories/service_factory.py`
    - Use template: Singleton pattern with lazy loading
    - Implement all 35 service getters
    - Add comprehensive type hints
    - Write unit tests for factory

2. **Start Phase 2**: Refactor controllers in order
    - Start with config_controller.py (easiest)
    - Test after each controller
    - Move to next controller only after tests pass

3. **Complete Phase 3**: Integration testing
    - Run all controller tests
    - Verify no behavior changes
    - Document any issues

---

## Coordination with Other Agents

### Python Expert

- **Task**: Implement ServiceFactory + refactor controllers
- **Deliverables**: 1 new file (factory), 5 modified files (controllers)
- **Timeline**: 9.5 hours over 2-3 days

### Testing Expert

- **Task**: Create controller tests (if missing)
- **Deliverables**: Integration tests for all 25+ endpoints
- **Timeline**: Start in parallel with Phase 1

### Database Expert

- **Task**: On-call for schema questions
- **Availability**: As needed

---

## Documentation Updates

**After completion**:

1. Update `engineering_plan/03_architecture_overview.md`
    - Add ServiceFactory pattern
    - Document dependency injection

2. Update `app/controllers/README.md` (create if missing)
    - Explain how to add new endpoints
    - Show factory usage pattern

3. Update `CLAUDE.md`
    - Add ServiceFactory to architecture section
    - Update controller best practices

---

## Conclusion

This refactoring eliminates ALL Clean Architecture violations in the controller layer by:

1. Creating centralized ServiceFactory for dependency injection
2. Removing direct repository imports from controllers
3. Eliminating 150+ lines of duplicated service instantiation code
4. Making controllers fully testable
5. Establishing maintainable pattern for future development

**After completion**: Controllers will be thin, testable, and compliant with Clean Architecture
principles.

---

**Team Leader**: Ready to delegate to Python Expert upon approval.
**Status**: PLAN COMPLETE - Awaiting execution approval.
