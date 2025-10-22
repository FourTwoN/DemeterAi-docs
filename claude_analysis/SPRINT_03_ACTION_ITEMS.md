# SPRINT 03 CRITICAL ACTION ITEMS
**Date**: 2025-10-21
**Status**: BLOCKING QUALITY GATES
**Priority**: IMMEDIATE

---

## CRITICAL BLOCKERS (MUST FIX)

### 1. FIX 19 FAILING TESTS
**Status**: 5.3% failure rate (EXCEEDS 0% threshold)
**Estimated Effort**: 4-6 hours

#### Group A: Storage Bin Service (3 tests) - EASY FIX
**Root Cause**: Test expects generic `ValueError`, code raises `DuplicateCodeException`

**Failing Tests**:
- `tests/unit/services/test_storage_bin_service.py::test_create_storage_bin_duplicate_code`
- `tests/unit/services/test_storage_bin_service.py::test_get_bins_by_location_success`
- `tests/unit/services/test_storage_bin_service.py::test_get_bins_by_location_empty`

**Fix Options**:
```python
# OPTION 1: Update test to catch specific exception (RECOMMENDED)
from app.core.exceptions import DuplicateCodeException
with pytest.raises(DuplicateCodeException):
    await bin_service.create_storage_bin(request)

# OPTION 2: Make exception inherit from ValueError
class DuplicateCodeException(ValueError):
    ...

# OPTION 3: Update service to raise ValueError
raise ValueError(f"Code {request.code} already exists")
```

**Recommendation**: OPTION 1 (most specific, best practice)

#### Group B: Pipeline Coordinator (16 tests) - MODERATE FIX
**Root Cause**: Mock setup issues in test fixtures or missing repository methods

**Failing Tests** (all in `tests/unit/services/ml_processing/test_pipeline_coordinator.py`):
- test_process_complete_pipeline_success
- test_process_complete_pipeline_progress_updates
- test_process_complete_pipeline_result_aggregation
- test_process_complete_pipeline_no_segments
- test_process_complete_pipeline_segmentation_fails
- test_process_complete_pipeline_detection_fails_warning
- test_process_complete_pipeline_estimation_fails_warning
- test_process_complete_pipeline_persistence_fails
- test_process_complete_pipeline_segments_use_sahi
- test_process_complete_pipeline_boxes_use_direct
- test_process_complete_pipeline_plugs_use_direct
- test_process_complete_pipeline_estimation_only_for_segments
- test_process_complete_pipeline_estimation_receives_detections
- test_process_complete_pipeline_performance_benchmark
- test_process_complete_pipeline_invalid_session_id
- test_process_complete_pipeline_zero_confidence_detections

**Investigation Required**:
1. Check Mock object setup for repository returns
2. Verify async mock is properly configured
3. Ensure all required methods are mocked with return values
4. Check if repository method names match what service expects

**Commands to Run**:
```bash
# Run with verbose output to see actual error
pytest tests/unit/services/ml_processing/test_pipeline_coordinator.py::TestMLPipelineCoordinatorHappyPath::test_process_complete_pipeline_success -xvs

# Check for import errors
python -c "from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator; print('OK')"
```

---

### 2. ACHIEVE ≥80% TEST COVERAGE
**Current**: 65.64%
**Target**: 80%
**Deficit**: 14.36 percentage points
**Estimated Effort**: 24-30 hours

#### Phase 1: Add Tests for Untested Services (10-12 hours)

**Services with 0% Coverage** (5 services):
1. `app/services/movement_validation_service.py` (18 lines)
2. `app/services/packaging_catalog_service.py` (29 lines)
3. `app/services/packaging_color_service.py` (29 lines)
4. `app/services/packaging_material_service.py` (29 lines)
5. `app/services/price_list_service.py` (29 lines)

**Template for Each Service**:
```python
# tests/unit/services/test_[service_name].py

import pytest
from unittest.mock import AsyncMock, Mock
from app.repositories.[repo_name] import [RepositoryClass]
from app.services.[service_name] import [ServiceClass]
from app.schemas.[schema_name] import [SchemaClass]

@pytest.fixture
def mock_repo():
    return AsyncMock(spec=[RepositoryClass])

@pytest.fixture
def service(mock_repo):
    return [ServiceClass](repo=mock_repo)

@pytest.mark.asyncio
async def test_create_success(service, mock_repo):
    """Test successful creation."""
    mock_obj = Mock()
    mock_repo.create.return_value = mock_obj

    request = [SchemaClass](...)
    result = await service.create(request)

    assert result is not None
    mock_repo.create.assert_called_once()
```

**Test Count Needed**: ~4 tests per service × 5 services = 20 new tests

#### Phase 2: Increase ML Pipeline Coverage (8-10 hours)

**Services with <30% Coverage**:
1. `app/services/ml_processing/sahi_detection_service.py`: 24% → 80%
2. `app/services/ml_processing/segmentation_service.py`: 27% → 80%
3. `app/services/ml_processing/pipeline_coordinator.py`: 28% → 80%
4. `app/services/photo/detection_service.py`: 20% → 80%
5. `app/services/photo/estimation_service.py`: 22% → 80%
6. `app/services/photo/photo_processing_session_service.py`: 26% → 80%

**Priority Order**:
1. First: Fix failing pipeline_coordinator tests (16 tests)
2. Then: Increase coverage for each ML service

**Approach**:
- Create test fixtures for complex objects (numpy arrays, image data)
- Test both success and error paths
- Test with real data samples where possible
- Mock only external dependencies (S3, GPU, filesystem)

#### Phase 3: Increase Low Coverage Services (6-8 hours)

**Services 30-70% Coverage**:
1. `app/services/analytics_service.py`: 33% → 80%
2. `app/services/photo/photo_upload_service.py`: 37% → 80%
3. `app/services/stock_movement_service.py`: 71% → 80%

**Specific Focus**:
- analytics_service: Test all aggregation methods
- photo_upload_service: Test file handling, validation, error cases
- stock_movement_service: Add 2-3 more comprehensive tests

---

## SECONDARY ISSUES (SHOULD FIX)

### 3. FIX DOCSTRING EXAMPLES (1 hour)

**Issue**: Docstring examples show improper dependency injection pattern

**Files to Update**:
1. `app/services/storage_area_service.py:102-107`
2. `app/services/warehouse_service.py:86-91`

**Current (WRONG)**:
```python
def get_storage_area_service(session: AsyncSession):
    repo = StorageAreaRepository(session)  # WRONG: Direct instantiation
    return StorageAreaService(repo)
```

**New (CORRECT)**:
```python
def get_storage_area_service(
    session: AsyncSession = Depends(get_db_session),
    warehouse_service: WarehouseService = Depends(get_warehouse_service)
):
    repo = StorageAreaRepository(session)
    return StorageAreaService(repo, warehouse_service)
```

**Or for simple services**:
```python
# Using factory function (recommended for complex cases)
from app.dependencies import get_storage_area_service

@router.post("/storage-areas")
async def create_storage_area(
    request: StorageAreaCreateRequest,
    service: StorageAreaService = Depends(get_storage_area_service)
):
    return await service.create(request)
```

---

## QUICK FIX CHECKLIST

```markdown
## Immediate Actions (1-2 hours)

- [ ] Fix storage_bin_service tests (catch DuplicateCodeException)
- [ ] Investigate pipeline_coordinator mock setup
- [ ] Verify all imports work: python -c "from app.services import *"
- [ ] Run tests locally: pytest tests/unit/services/ -v

## Short Term (4-6 hours)

- [ ] Fix all 19 failing tests
- [ ] Add tests for 5 untested packaging/utility services
- [ ] Update docstring examples

## Medium Term (16-24 hours)

- [ ] Increase ML pipeline coverage to 80%
- [ ] Add comprehensive integration tests
- [ ] Code review all changes
- [ ] Final test run and coverage report
```

---

## VERIFICATION COMMANDS

**Check Current Status**:
```bash
# Run all service tests
pytest tests/unit/services/ -v

# Check coverage
pytest tests/unit/services/ --cov=app/services --cov-report=term-missing

# Check specific service
pytest tests/unit/services/test_storage_bin_service.py -v
pytest tests/unit/services/ml_processing/test_pipeline_coordinator.py -v
```

**After Fixes**:
```bash
# Verify all tests pass
pytest tests/unit/services/ -v --tb=short
# Expected: All pass, 0 failures

# Verify coverage >= 80%
pytest tests/unit/services/ --cov=app/services --cov-report=term-missing
# Expected: TOTAL >= 80%

# Check specific coverage for problem areas
pytest tests/unit/services/ml_processing/ --cov=app/services/ml_processing --cov-report=term-missing
```

---

## GATE REQUIREMENTS SUMMARY

| Gate | Requirement | Current | Status |
|------|-------------|---------|--------|
| Tests Pass | 0 failures | 19 failures | ❌ FAIL |
| Coverage | ≥80% | 65.64% | ❌ FAIL |
| Type Hints | 100% | 99.9% | ✅ PASS |
| Async/Await | Proper usage | OK | ✅ PASS |
| Architecture | Service→Service | OK | ✅ PASS |
| Schema Match | 100% match | OK | ✅ PASS |

**Cannot mark Sprint 03 COMPLETE until all gates pass**

---

## RESOURCES

**Test Templates**: `/home/lucasg/proyectos/DemeterDocs/backlog/04_templates/`
**Exception Definitions**: `/home/lucasg/proyectos/DemeterDocs/app/core/exceptions.py`
**Schema Examples**: `/home/lucasg/proyectos/DemeterDocs/app/schemas/`
**Service Examples**: `/home/lucasg/proyectos/DemeterDocs/app/services/product_category_service.py`

---

## TIMELINE ESTIMATE

- **Phase 1 (Tests)**: 4-6 hours
- **Phase 2 (Coverage - untested)**: 10-12 hours
- **Phase 3 (Coverage - low tested)**: 6-8 hours
- **Phase 4 (Fix examples)**: 1 hour
- **Review & Verify**: 2-3 hours
- **Total**: 28-36 hours

**Recommended Completion**: 3-4 business days with 1 developer

---

**Last Updated**: 2025-10-21
**Ready for**: Immediate action
