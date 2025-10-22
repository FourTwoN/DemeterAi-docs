# DemeterAI v2.0 - Test Fixes Applied (2025-10-22)

**Status**: In Progress - Substantial Fixes Applied
**Expected Test Improvement**: ~120-150 additional tests passing (from 81.5% → ~90%+)

---

## Summary of Fixes

This document catalogs all the test fixes applied to address the audit findings. The focus is on
fixing tests to match the actual model signatures and field names, rather than modifying the
production code.

### Principle: Fix Tests, Not Models

Per user guidance, we are fixing the **tests** to match the **actual model implementations**, rather
than changing the models themselves. This ensures tests accurately reflect production behavior.

---

## 1. Factory Fixtures Added to conftest.py ✅

**File**: `tests/conftest.py`

Added 6 comprehensive async factory fixtures for test data creation:

### 1a. product_category_factory

```python
async def product_category_factory(**kwargs):
    """Create ProductCategory instances with proper attributes."""
```

- Creates ProductCategory with: code, name, description
- Auto-generates defaults if not provided
- Commits to database and returns fresh instance

### 1b. product_family_factory

```python
async def product_family_factory(product_category_factory, **kwargs):
    """Create ProductFamily instances with auto-creation of category if needed."""
```

- Depends on product_category_factory
- Creates ProductFamily with: category_id, name, scientific_name, description
- Auto-creates category if category_id not provided

### 1c. product_factory

```python
async def product_factory(product_family_factory, **kwargs):
    """Create Product instances with proper sku/common_name attributes."""
```

- **KEY FIX**: Replaces old Product(code=, name=) pattern
- Uses correct attributes:
    - `sku`: Stock Keeping Unit (6-20 chars, alphanumeric+hyphen)
    - `common_name`: Human-readable name (NOT 'name')
    - `scientific_name`: Optional botanical name
    - `description`: Optional description
    - `custom_attributes`: JSONB metadata
    - `family_id`: Foreign key to ProductFamily
- Auto-creates family if family_id not provided
- **Fixes ~40+ test failures** in Detection and Estimation tests

### 1d. user_factory

```python
async def user_factory(**kwargs):
    """Create User instances with bcrypt password hashing."""
```

- **KEY FIX**: Replaces old User(username=, hashed_password=) pattern
- Uses correct attributes:
    - `email`: Login identifier (unique, indexed)
    - `password_hash`: Bcrypt hash ($2b$... format)
    - `first_name`: User first name
    - `last_name`: User last name
    - `role`: UserRoleEnum (admin, supervisor, worker, viewer)
    - `active`: Account status
- Auto-generates valid bcrypt hashes for test passwords
- **Fixes ~10+ test failures** in PhotoProcessingSession tests

### 1e. product_size_factory

```python
async def product_size_factory(**kwargs):
    """Create ProductSize instances."""
```

- Note: ProductSizes are usually seeded via migrations (7 standard sizes)
- Available for creating additional test sizes if needed
- Attributes: code, name, description, min_height_cm, max_height_cm, sort_order

### 1f. product_state_factory

```python
async def product_state_factory(**kwargs):
    """Create ProductState instances."""
```

- Note: ProductStates are usually seeded via migrations (11 lifecycle states)
- Available for creating additional test states if needed
- Attributes: code, name, description, is_sellable, sort_order

---

## 2. Test File Corrections ✅

### 2a. test_detection.py

**File**: `tests/unit/models/test_detection.py`

**Fixes Applied**:

- Replaced 9 instances of `Product(code="...", name="...", category="...")` with
  `await product_factory(sku="...", common_name="...")`
- Added `product_factory` parameter to all affected test methods
- Pattern changed from:
  ```python
  product = Product(code="PROD-001", name="Test Product", category="cactus")
  ```
  To:
  ```python
  product = await product_factory(sku="PROD-001", common_name="Test Product")
  ```
- **Affected test methods**: 9 tests in TestDetectionBasicCRUD, TestDetectionBooleanFlags,
  TestDetectionCascadeDelete, etc.

### 2b. test_estimation.py

**File**: `tests/unit/models/test_estimation.py`

**Fixes Applied**:

- Replaced 9 instances of `Product(code=..., name=..., category=...)` with `product_factory` calls
- Added `product_factory` parameter to all affected test methods
- Same pattern change as test_detection.py

### 2c. test_photo_processing_session.py

**File**: `tests/unit/models/test_photo_processing_session.py`

**Fixes Applied**:

- Replaced `User(username="...", email="...", hashed_password="...")` with
  `await user_factory(email="...", first_name="...")`
- Added `user_factory` parameter to all affected test methods
- Pattern changed from:
  ```python
  user = User(username="testuser", email="test@example.com", hashed_password="hashed_pass")
  ```
  To:
  ```python
  user = await user_factory(email="test@example.com", first_name="testuser")
  ```
- **Affected test methods**: Multiple tests in PhotoProcessingSession test classes

---

## 3. Spatial Model Parameter Corrections ✅

**Files**: Multiple test files containing spatial model instantiations

**Fix Applied**: Replace `coordinates=` with `geojson_coordinates=`

**Reasoning**:

- SQLAlchemy models use `geojson_coordinates` as the database column name
- Tests were using wrong parameter name `coordinates`
- This affected Warehouse, StorageArea, and StorageLocation models

**Files Modified**:

1. `tests/conftest.py` - Fixed sample_storage_areas, sample_storage_locations, warehouse_factory,
   storage_area_factory, storage_location_factory
2. `tests/unit/models/test_warehouse.py`
3. `tests/unit/models/test_storage_area.py`
4. `tests/unit/models/test_storage_location.py`
5. `tests/integration/models/test_warehouse_geospatial.py`
6. `tests/integration/models/test_storage_area_geospatial.py`
7. `tests/integration/models/test_storage_location_geospatial.py`
8. `tests/integration/models/test_storage_bin.py`
9. `tests/integration/test_warehouse_service_integration.py`
10. `tests/unit/services/test_warehouse_service.py`
11. `tests/unit/services/test_storage_area_service.py`
12. `tests/unit/services/test_storage_location_service.py`

**Example Change**:

```python
# BEFORE
warehouse = Warehouse(
    code="WH-001",
    name="Test Warehouse",
    coordinates=from_shape(Polygon(coords), srid=4326),
)

# AFTER
warehouse = Warehouse(
    code="WH-001",
    name="Test Warehouse",
    geojson_coordinates=from_shape(Polygon(coords), srid=4326),
)
```

---

## 4. S3ImageService Test Corrections ✅

**File**: `tests/integration/test_s3_image_service.py`

**Fixes Applied**:

1. Added missing import:
   ```python
   from app.schemas.s3_image_schema import S3ImageUploadRequest
   ```

2. Updated upload_original() method calls to use S3ImageUploadRequest object instead of flat
   parameters
    - Old pattern:
      `await s3_service.upload_original(file_bytes, session_id, filename="...", content_type=..., width_px=..., ...)`
    - New pattern: Create S3ImageUploadRequest object with all parameters, then pass to service

**Reasoning**:

- S3ImageService.upload_original() signature expects:
    - file_bytes: bytes
    - session_id: UUID
    - upload_request: S3ImageUploadRequest object
- Tests were passing individual parameters which don't exist in the method signature

---

## 5. Test Method Signature Updates ✅

**Updated test method signatures** to include factory parameters:

### test_detection.py

All test methods that use `product_factory` now have it in their parameters:

```python
async def test_create_detection_minimal_fields(
    self, db_session, warehouse_factory, storage_area_factory,
    storage_location_factory, product_factory  # ← ADDED
):
```

### test_estimation.py

Same pattern as test_detection.py

### test_photo_processing_session.py

All test methods that use `user_factory` now have it in their parameters:

```python
async def test_create_session_all_fields(
    self, db_session, warehouse_factory, storage_area_factory,
    storage_location_factory, user_factory  # ← ADDED
):
```

---

## Expected Impact on Test Pass Rate

### Before Fixes

- **Total Tests**: 1,456
- **Passing**: 1,187 (81.5%)
- **Failing**: 261 (18.0%)
- **Coverage**: 72.38% (below 80% threshold)

### Expected After Fixes

- **Model instantiation failures fixed**: ~90-100 tests
    - Product(code=...) → product_factory: ~40 tests
    - User(username=...) → user_factory: ~10 tests
    - coordinates → geojson_coordinates: ~40-50 tests

- **Expected passing**: ~1,280-1,290 tests (88-90%)
- **Expected failing**: ~170-180 tests (10-12%)
- **Expected coverage**: ~75-80%

### Remaining Issues to Address

1. **Celery task property setter issues** (~20 tests)
    - ModelSingletonTask.request property has no setter
    - Needs modification to allow test injection

2. **ML Pipeline async/await issues** (~15 tests)
    - File path issues in tests
    - Mock setup required

3. **Auth configuration** (~16 tests)
    - Missing AUTH0_DOMAIN environment variable
    - Needs test fixtures for auth service

4. **Type checking** (275 mypy errors)
    - Missing type stubs for some dependencies
    - Lower priority, doesn't affect test execution

---

## How to Verify Fixes

### Step 1: Run a Sample of Fixed Tests

```bash
# Test Product factory fixes
pytest tests/unit/models/test_detection.py::TestDetectionBasicCRUD::test_create_detection_minimal_fields -v

# Test User factory fixes
pytest tests/unit/models/test_photo_processing_session.py::TestPhotoProcessingSessionBasicCRUD::test_create_session_all_fields -v

# Test spatial model fixes
pytest tests/unit/models/test_warehouse.py::TestWarehouseDefaultValues::test_active_defaults_to_true -v
```

### Step 2: Run Full Test Suite

```bash
pytest tests/ -v --tb=short 2>&1 | tee test_results.log

# Count passes/failures
grep "passed\|failed" test_results.log | tail -1
```

### Step 3: Check Coverage

```bash
pytest tests/ --cov=app --cov-report=term-missing | grep "TOTAL"
```

---

## Files Modified Summary

**conftest.py** (Main fixture file)

- Added 6 factory fixtures
- ~150 lines added

**Test Files Modified** (15 files)

- test_detection.py: 9 Product fixes
- test_estimation.py: 9 Product fixes
- test_photo_processing_session.py: 10+ User fixes
- test_warehouse.py: coordinates → geojson_coordinates
- test_storage_area.py: coordinates → geojson_coordinates
- test_storage_location.py: coordinates → geojson_coordinates
- test_warehouse_geospatial.py: coordinates → geojson_coordinates
- test_storage_area_geospatial.py: coordinates → geojson_coordinates
- test_storage_location_geospatial.py: coordinates → geojson_coordinates
- test_storage_bin.py: coordinates → geojson_coordinates
- test_s3_image_service.py: Added import, updated method calls
- test_warehouse_service_integration.py: coordinates → geojson_coordinates
- test_warehouse_service.py: coordinates → geojson_coordinates
- test_storage_area_service.py: coordinates → geojson_coordinates
- test_storage_location_service.py: coordinates → geojson_coordinates

**Total Changes**: ~500+ lines of test fixes

---

## Next Steps

### High Priority (Blocking other fixes)

1. **Verify** these fixes work with pytest run
2. **Commit** the test fixes
3. **Address Celery task issues** if test results show they're blocking further progress

### Medium Priority

4. Fix ML Pipeline coordinate and file path issues
5. Add Auth configuration test fixtures

### Low Priority (Non-blocking)

6. Fix type checking issues (mypy errors)
7. Clean up test code style violations

---

## Notes

- All changes follow the principle of **fixing tests to match models**, not modifying models
- Factories provide consistent, reusable test data creation
- Database transactions are properly handled via async/await
- bcrypt password hashing is correctly implemented in user_factory
- Spatial models now use correct parameter names throughout test suite

**Generated**: 2025-10-22
**Status**: Ready for testing and commit
