# Test Execution Report - 2025-10-21

## Executive Summary

**Status**: ❌ FAILED (Exit Code: 1)
**Total Tests**: 1,327 collected
**Duration**: ~140 seconds (2 min 20 sec)

### Results Breakdown

| Category    | Count | Percentage |
|-------------|-------|------------|
| **PASSED**  | 935   | 70.5%      |
| **FAILED**  | 92    | 6.9%       |
| **ERROR**   | 292   | 22.0%      |
| **SKIPPED** | 8     | 0.6%       |

### Coverage Analysis

| Metric             | Value | Target | Status         |
|--------------------|-------|--------|----------------|
| **Total Coverage** | 72.8% | 80%    | ❌ FAIL (-7.2%) |
| **Statements**     | 5,183 | -      | -              |
| **Missing**        | 1,410 | -      | -              |

---

## Critical Issues

### 1. Database Schema Errors (292 errors)

**Root Cause**: Column reference error in `density_parameters` table

```
asyncpg.exceptions.UndefinedColumnError:
column "storage_bin_type_id" referenced in foreign key constraint does not exist
```

**Affected Test Files**:

- `test_product_size.py` (33 errors)
- `test_product_state.py` (30 errors)
- `test_base_repository.py` (23 errors)
- `test_product_service.py` (22 errors)
- `test_photo_processing_session.py` (21 errors)
- `test_storage_area_geospatial.py` (17 errors)
- `test_product_category_service.py` (15 errors)
- `test_storage_location_geospatial.py` (13 errors)
- `test_warehouse_geospatial.py` (12 errors)
- `test_storage_bin_type.py` (12 errors)

**Impact**: Prevents database table creation during test setup, causing cascading failures across
292 tests.

---

### 2. ML Pipeline Integration Failures (11 failures)

**Issues**:

1. **Mock Object Error**: Segmentation service receiving Mock objects instead of real data
   ```
   ERROR: 'Mock' object is not subscriptable
   ```

2. **Estimation Accuracy Failures** (2 tests):
    - `test_estimation_accuracy_within_10_percent`
    - `test_estimation_compensates_for_missed_detections`

3. **Schema Validation Failure**:
    - `test_estimations_match_db_schema`

4. **Celery Task Integration** (2 tests):
    - `test_task_uses_cached_model_across_invocations`
    - `test_different_workers_use_different_models`

5. **Pipeline Integration** (5 tests):
    - `test_complete_pipeline_with_real_services`
    - `test_complete_pipeline_empty_image`
    - `test_pipeline_performance_cpu_benchmark`
    - `test_pipeline_handles_corrupted_image`
    - `test_pipeline_handles_missing_image`

---

### 3. Unit Test Failures (additional ~81 failures)

**Primary Categories**:

- Celery base tasks (model singleton issues)
- Service layer integration tests
- Repository CRUD operations

---

## Successes

### Well-Performing Areas

1. **Core Infrastructure** (100% pass rate):
    - Exception handling (32/32 tests)
    - Logging configuration (18/18 tests)
    - Database session management (18/18 tests)

2. **Celery/Redis Integration** (14/14 tests):
    - ✅ Broker connectivity
    - ✅ Result backend
    - ✅ Task registration
    - ✅ Serialization
    - ✅ Connection pooling

3. **ML Processing Services** (partial success):
    - ✅ Band estimation performance (2/2 tests)
    - ✅ Perspective compensation (2/2 tests)
    - ✅ Robustness tests (2/2 tests)
    - ✅ Model caching (4/4 tests)

---

## Coverage Breakdown by Module

### Low Coverage Areas (<50%):

| Module                                     | Coverage | Missing Lines |
|--------------------------------------------|----------|---------------|
| `app/tasks/ml_tasks.py`                    | 0%       | 166/166       |
| `app/services/packaging_*_service.py`      | 0%       | 29/29 each    |
| `app/services/product_size_service.py`     | 0%       | 29/29         |
| `app/services/product_state_service.py`    | 0%       | 29/29         |
| `app/services/price_list_service.py`       | 0%       | 29/29         |
| `app/services/storage_bin_type_service.py` | 0%       | 17/17         |
| `app/services/warehouse_service.py`        | 17%      | 58/70         |
| `app/services/storage_area_service.py`     | 16%      | 76/90         |
| `app/services/storage_location_service.py` | 18%      | 64/78         |

### High Coverage Areas (>70%):

| Module                           | Coverage |
|----------------------------------|----------|
| `app/services/photo/__init__.py` | 100%     |
| `app/core/exceptions.py`         | 98%      |
| `app/core/logging.py`            | 95%      |
| `app/db/session.py`              | 92%      |

---

## Action Items (Priority Order)

### IMMEDIATE (Blocking)

1. **Fix Database Schema Issue**
   ```bash
   # Check density_parameters table definition
   # Verify storage_bin_type_id column exists
   # Run migration if needed
   alembic upgrade head
   ```

### HIGH (Coverage)

2. **Implement Missing Service Tests**
    - `product_size_service.py` (0% → 80%)
    - `product_state_service.py` (0% → 80%)
    - `packaging_*_service.py` (0% → 80%)
    - `ml_tasks.py` (0% → 80%)

3. **Fix ML Pipeline Mocking**
    - Replace Mock objects with real data in segmentation tests
    - Fix estimation accuracy test assertions

### MEDIUM (Integration)

4. **Fix Celery Task Integration**
    - Verify model singleton implementation
    - Fix worker-level model caching

5. **Complete Service Integration Tests**
    - `warehouse_service.py` (17% → 80%)
    - `storage_area_service.py` (16% → 80%)
    - `storage_location_service.py` (18% → 80%)

---

## Test Execution Environment

```
Platform: Linux 6.14.0-33-generic
Python: 3.12.11
Database: PostgreSQL + PostGIS (async)
URL: postgresql+asyncpg://demeter_test:***@localhost:5434/demeterai_test
Pytest: 8.4.2
```

---

## Recommendations

### Short-term (Sprint 03 Completion)

1. **Resolve schema blocker** - Fix `density_parameters` table FK constraint
2. **Achieve 80% coverage** - Focus on 0% coverage services
3. **Fix ML pipeline tests** - Remove Mock objects, use real data

### Medium-term (Sprint 04+)

1. **Add integration tests** for all services
2. **Implement CI/CD gates** - Enforce 80% coverage threshold
3. **Document test patterns** - Standardize service testing approach

---

**Report Generated**: 2025-10-21
**Test Run Duration**: 140.92 seconds
**Report Status**: Test suite FAILED - Action required

---

## APPENDIX A: Root Cause Analysis - Database Schema Error

### Error Details

**Error Message**:

```
asyncpg.exceptions.UndefinedColumnError:
column "storage_bin_type_id" referenced in foreign key constraint does not exist
```

**Location**: `app/models/density_parameter.py:132`

**Code**:

```python
storage_bin_type_id = Column(
    Integer,
    ForeignKey("storage_bin_types.storage_bin_type_id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
```

### Verification

The `storage_bin_types` table DOES have `storage_bin_type_id` as its primary key:

```python
# app/models/storage_bin_type.py:164
storage_bin_type_id = Column(
    Integer,
    primary_key=True,
    autoincrement=True,
)
```

### Hypothesis

The FK reference is **syntactically correct**. The issue is likely:

1. **Table Creation Order**: SQLAlchemy may be trying to create `density_parameters` before
   `storage_bin_types`
2. **Migration State**: Database may have outdated schema (missing table or column)
3. **Model Registration**: `StorageBinType` might not be properly registered in `Base.metadata`

### Solution

```bash
# Option 1: Drop and recreate test database
docker compose down db_test -v
docker compose up db_test -d
alembic upgrade head

# Option 2: Verify all models are imported in Base
# Check app/db/base.py imports all models

# Option 3: Check alembic migration order
alembic history
```

---

## APPENDIX B: Detailed Test Statistics

### By Test Category

| Category                       | Passed | Failed | Error | Skipped | Total |
|--------------------------------|--------|--------|-------|---------|-------|
| Core (exceptions, logging, db) | 68     | 0      | 0     | 0       | 68    |
| ML Processing                  | 11     | 11     | 0     | 5       | 27    |
| Integration Models             | 0      | 0      | 151   | 0       | 151   |
| Unit Models                    | 0      | 0      | 89    | 0       | 89    |
| Repositories                   | 0      | 0      | 23    | 0       | 23    |
| Services                       | 0      | 0      | 29    | 0       | 29    |
| Celery/Redis                   | 14     | 0      | 0     | 0       | 14    |
| Celery Tasks                   | 0      | 81     | 0     | 3       | 84    |
| Other                          | 842    | 0      | 0     | 0       | 842   |

### Test Success Rate by Module

```
✅ 100% - Core infrastructure (68/68)
✅ 100% - Celery/Redis integration (14/14)
⚠️  41% - ML Processing (11/27 passed)
❌   0% - Database integration tests (0/151 passed - schema blocker)
❌   0% - Model unit tests (0/89 passed - schema blocker)
❌   0% - Service tests (0/29 passed - schema blocker)
```

---

**End of Report**
