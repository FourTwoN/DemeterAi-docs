# Sprint 04 - Fixes Checklist

**Status**: ACTION REQUIRED
**Priority**: CRITICAL
**Effort**: 28-40 hours
**Target**: End of Sprint 04

---

## FIX #1: Architecture Violation - Repository Imports in Controllers

### Problem
Controllers directly import and instantiate repositories, violating clean architecture pattern.

### Current Code (❌ WRONG)
```python
# app/controllers/analytics_controller.py
from app.repositories.stock_batch_repository import StockBatchRepository

def get_analytics_service(session: AsyncSession = Depends(get_db_session)):
    stock_batch_repo = StockBatchRepository(session)
    return AnalyticsService(stock_batch_repo)
```

### Solution: Create DI Factory Module

**Step 1**: Create `app/di/__init__.py`
```python
"""Dependency Injection module."""
```

**Step 2**: Create `app/di/factory.py`
```python
"""Service factory - centralized DI."""

from sqlalchemy.ext.asyncio import AsyncSession

# Stock Services
def create_stock_batch_service(session: AsyncSession):
    from app.repositories.stock_batch_repository import StockBatchRepository
    from app.repositories.storage_location_config_repository import (
        StorageLocationConfigRepository,
    )
    from app.services.storage_location_config_service import (
        StorageLocationConfigService,
    )
    from app.services.stock_batch_service import StockBatchService

    batch_repo = StockBatchRepository(session)
    config_repo = StorageLocationConfigRepository(session)
    config_service = StorageLocationConfigService(config_repo)

    return StockBatchService(batch_repo, config_service)

def create_stock_movement_service(session: AsyncSession):
    from app.repositories.stock_movement_repository import StockMovementRepository
    from app.services.stock_movement_service import StockMovementService

    movement_repo = StockMovementRepository(session)
    return StockMovementService(movement_repo)

# Similar factory functions for all services...
```

**Step 3**: Update Controllers to Use Factory
```python
# app/controllers/analytics_controller.py
from app.di.factory import create_analytics_service  # ✅ Import factory

def get_analytics_service(session: AsyncSession = Depends(get_db_session)):
    return create_analytics_service(session)  # ✅ Use factory
```

### Tasks
- [ ] Create `app/di/__init__.py`
- [ ] Create `app/di/factory.py` with all service factories
- [ ] Update `stock_controller.py` to use factory
- [ ] Update `location_controller.py` to use factory
- [ ] Update `product_controller.py` to use factory
- [ ] Update `config_controller.py` to use factory
- [ ] Update `analytics_controller.py` to use factory
- [ ] Remove all repository imports from controllers
- [ ] Run linter to verify no repository imports remain

---

## FIX #2: Complete Placeholder Endpoints

### C003: Get Celery Task Status

**Issue**: Returns placeholder response

**Current Code** (stock_controller.py:302-350):
```python
# TODO: Replace with actual Celery task lookup when CEL005 is implemented
return {"task_id": str(task_id), "status": "PENDING", ...}
```

**Solution**: Depends on CEL005 (Celery integration) - Mark as deferred

**Action**:
- [ ] Document dependency on CEL005
- [ ] Add @router.get() deprecation note: "Requires CEL005 for full implementation"
- [ ] Keep placeholder until CEL005 ready

---

### C005: List Stock Batches

**Issue**: Returns empty list because `StockBatchService.get_multi()` not implemented

**Solution**:

**Step 1**: Add method to `StockBatchService`
```python
# app/services/stock_batch_service.py
async def get_multi(
    self,
    skip: int = 0,
    limit: int = 100
) -> list[StockBatchResponse]:
    """Get multiple stock batches with pagination."""
    batches = await self.repo.get_multi(skip=skip, limit=limit)
    return [StockBatchResponse.from_model(batch) for batch in batches]
```

**Step 2**: Update controller to call service
```python
# app/controllers/stock_controller.py
@router.get("/batches", response_model=list[StockBatchResponse])
async def list_stock_batches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: StockBatchService = Depends(get_stock_batch_service),
):
    batches = await service.get_multi(skip=skip, limit=limit)
    return batches
```

**Tasks**:
- [ ] Implement `StockBatchService.get_multi()`
- [ ] Update `list_stock_batches()` endpoint
- [ ] Add test case for list endpoint
- [ ] Verify response format

---

### C006: Get Batch Details

**Issue**: Returns 404 because `StockBatchService.get_by_id()` not implemented

**Solution**:

**Step 1**: Add method to `StockBatchService`
```python
# app/services/stock_batch_service.py
async def get_by_id(self, batch_id: int) -> StockBatchResponse:
    """Get stock batch by ID."""
    batch = await self.repo.get(batch_id)
    if not batch:
        raise ResourceNotFoundException(f"Batch {batch_id} not found")
    return StockBatchResponse.from_model(batch)
```

**Step 2**: Update controller
```python
# app/controllers/stock_controller.py
@router.get("/batches/{batch_id}", response_model=StockBatchResponse)
async def get_batch_details(
    batch_id: int,
    service: StockBatchService = Depends(get_stock_batch_service),
):
    return await service.get_by_id(batch_id)
```

**Tasks**:
- [ ] Implement `StockBatchService.get_by_id()`
- [ ] Update `get_batch_details()` endpoint
- [ ] Add test for success case (batch found)
- [ ] Add test for error case (batch not found)

---

### C007: Stock Movement History

**Issue**: Returns empty list because `StockMovementService.get_multi()` not implemented

**Solution**: Similar to C005

**Tasks**:
- [ ] Implement `StockMovementService.get_multi()`
- [ ] Update `get_stock_movement_history()` endpoint
- [ ] Add test case

---

### C013: Validate Location Hierarchy

**Issue**: Returns placeholder because validation not implemented

**Solution**:

**Step 1**: Add method to `LocationHierarchyService`
```python
# app/services/location_hierarchy_service.py
async def validate_hierarchy(
    self,
    warehouse_id: int | None = None,
    area_id: int | None = None,
    location_id: int | None = None,
    bin_id: int | None = None,
) -> dict:
    """Validate location hierarchy integrity."""
    errors = []

    # If area_id provided, verify it belongs to warehouse
    if area_id and warehouse_id:
        area = await self.area_service.get_by_id(area_id)
        if area.warehouse_id != warehouse_id:
            errors.append(f"Area {area_id} does not belong to warehouse {warehouse_id}")

    # Similar checks for location and bin...

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "hierarchy": {
            "warehouse_id": warehouse_id,
            "area_id": area_id,
            "location_id": location_id,
            "bin_id": bin_id,
        }
    }
```

**Step 2**: Update controller
```python
# app/controllers/location_controller.py
@router.post("/validate", response_model=dict)
async def validate_location_hierarchy(...):
    return await service.validate_hierarchy(warehouse_id, area_id, ...)
```

**Tasks**:
- [ ] Implement `LocationHierarchyService.validate_hierarchy()`
- [ ] Update endpoint
- [ ] Add tests

---

### C024: Daily Plant Counts

**Issue**: Returns placeholder because aggregation not implemented

**Solution**:

**Step 1**: Add method to `AnalyticsService`
```python
# app/services/analytics_service.py
async def get_daily_counts(
    self,
    start_date: date,
    end_date: date,
    location_id: int | None = None,
    product_id: int | None = None,
) -> list[dict]:
    """Get daily plant counts aggregated from stock movements."""
    query = select(
        func.date(StockMovement.created_at).label("date"),
        func.sum(case(
            (StockMovement.is_inbound == True, StockMovement.quantity),
            else_=0
        )).label("movements_in"),
        func.sum(case(
            (StockMovement.is_inbound == False, StockMovement.quantity),
            else_=0
        )).label("movements_out"),
    ).where(
        func.date(StockMovement.created_at).between(start_date, end_date)
    )

    # Add optional filters
    if location_id:
        query = query.join(StockBatch).where(StockBatch.storage_location_id == location_id)
    if product_id:
        query = query.join(StockBatch).where(StockBatch.product_id == product_id)

    query = query.group_by(func.date(StockMovement.created_at))

    result = await self.session.execute(query)
    rows = result.fetchall()

    return [
        {
            "date": row.date,
            "movements_in": row.movements_in or 0,
            "movements_out": row.movements_out or 0,
            "net_change": (row.movements_in or 0) - (row.movements_out or 0),
        }
        for row in rows
    ]
```

**Tasks**:
- [ ] Implement `AnalyticsService.get_daily_counts()`
- [ ] Update endpoint
- [ ] Add tests with sample data

---

### C026: Data Export

**Issue**: Returns placeholder CSV/JSON

**Solution**:

**Step 1**: Add methods to `AnalyticsService`
```python
async def export_inventory_csv(self) -> str:
    """Export inventory as CSV."""
    # Query inventory data
    rows = [["batch_id", "product", "quantity", "location"]]
    # ... build CSV rows
    return "\n".join([",".join(row) for row in rows])

async def export_inventory_json(self) -> list[dict]:
    """Export inventory as JSON."""
    # Query and return as list of dicts
    ...
```

**Step 2**: Update controller
```python
if export_format == "csv":
    content = await service.export_inventory_csv()
    media_type = "text/csv"
else:
    data = await service.export_inventory_json()
    content = json.dumps(data)
    media_type = "application/json"
```

**Tasks**:
- [ ] Implement CSV export in AnalyticsService
- [ ] Implement JSON export in AnalyticsService
- [ ] Update endpoint
- [ ] Add tests

---

## FIX #3: Add Integration Tests

### Test Structure

Create 5 new test files:

```
tests/integration/
  ├── test_stock_controller.py (7 tests)
  ├── test_location_controller.py (6 tests)
  ├── test_product_controller.py (7 tests)
  ├── test_config_controller.py (3 tests)
  └── test_analytics_controller.py (3 tests)
```

### Example Test Template

```python
# tests/integration/test_stock_controller.py

@pytest.mark.integration
async def test_upload_photo_returns_202(client, db_session):
    """Test photo upload returns 202 Accepted."""
    # Create test data
    warehouse = await create_test_warehouse(db_session)
    location = await create_test_storage_location(db_session, warehouse)

    # Call endpoint
    response = await client.post(
        "/api/v1/stock/photo",
        data={
            "longitude": 10.5,
            "latitude": 20.5,
            "user_id": 1,
        },
        files={"file": ("photo.jpg", b"fake image data", "image/jpeg")}
    )

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert "session_id" in data
    assert data["status"] == "PROCESSING"

@pytest.mark.integration
async def test_create_manual_stock_init(client, db_session):
    """Test manual stock initialization."""
    # Setup test data
    location = await create_test_location(db_session)
    product = await create_test_product(db_session)
    packaging = await create_test_packaging(db_session)
    config = await create_test_location_config(
        db_session, location, product, packaging
    )

    # Call endpoint
    response = await client.post(
        "/api/v1/stock/manual",
        json={
            "storage_location_id": location.storage_location_id,
            "product_id": product.product_id,
            "packaging_catalog_id": packaging.packaging_catalog_id,
            "product_size_id": 1,
            "quantity": 100,
            "planting_date": "2025-10-01",
        }
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["batch_id"] > 0
    assert data["quantity"] == 100

# ... more tests
```

### Tasks for Each Controller

#### Stock Controller Tests (7):
- [ ] test_upload_photo_returns_202
- [ ] test_upload_photo_invalid_file_returns_400
- [ ] test_create_manual_stock_init_success
- [ ] test_create_manual_stock_init_config_not_found
- [ ] test_create_stock_movement_success
- [ ] test_list_stock_batches_pagination
- [ ] test_get_batch_details_returns_batch

#### Location Controller Tests (6):
- [ ] test_list_warehouses_returns_list
- [ ] test_get_warehouse_areas_returns_areas
- [ ] test_get_area_locations_returns_locations
- [ ] test_get_location_bins_returns_bins
- [ ] test_search_by_gps_returns_hierarchy
- [ ] test_search_by_gps_not_found_returns_404

#### Product Controller Tests (7):
- [ ] test_list_categories_returns_list
- [ ] test_create_category_success
- [ ] test_list_families_by_category
- [ ] test_create_product_generates_sku
- [ ] test_get_product_by_sku_success
- [ ] test_get_product_by_sku_not_found

#### Config Controller Tests (3):
- [ ] test_get_location_defaults_returns_config
- [ ] test_set_location_defaults_creates_config
- [ ] test_get_density_parameters_by_product

#### Analytics Controller Tests (3):
- [ ] test_get_daily_counts_returns_aggregation
- [ ] test_get_inventory_report_returns_summary
- [ ] test_export_data_csv_format

### General Tasks
- [ ] Create fixtures for test data factories
- [ ] Setup test database migrations
- [ ] Create conftest.py with shared fixtures
- [ ] Run all tests with coverage
- [ ] Achieve ≥80% coverage for controllers

---

## FIX #4: Fix Test Database Setup

### Problem
Tests fail with database schema creation errors

### Solution

**Step 1**: Check Alembic Configuration
```bash
# Verify alembic.ini is correct
cat alembic.ini | grep sqlalchemy.url

# Should point to test database, not production
```

**Step 2**: Run Migrations on Test DB
```bash
# Apply all migrations
alembic -c alembic_test.ini upgrade head

# Verify schema was created
psql -U demeter_test -d demeterai_test -c "\dt"
```

**Step 3**: Update conftest.py
```python
# tests/conftest.py

@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create test database schema before running tests."""
    # Run migrations
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from alembic.operations import Operations

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.test_database_url)

    # Run upgrade
    os.system("alembic -c alembic.ini upgrade head")

    yield

    # Teardown (optional - drop schema)
    # os.system("alembic -c alembic.ini downgrade base")
```

### Tasks
- [ ] Debug Alembic configuration
- [ ] Verify test database URL
- [ ] Run migrations on test DB
- [ ] Create test database setup in conftest.py
- [ ] Run health check test to verify setup
- [ ] Verify no schema errors

---

## FIX #5: Quality Gates Verification

### Pre-Commit Checklist

```bash
# 1. Check repository imports removed
grep -r "from app.repositories" app/controllers/ && echo "FAIL" || echo "PASS"

# 2. Check no TODOs in controllers
grep -r "TODO\|FIXME" app/controllers/ && echo "FOUND" || echo "CLEAN"

# 3. Run linter
flake8 app/controllers/ app/schemas/

# 4. Run type checker
mypy app/controllers/ app/schemas/

# 5. Run tests
pytest tests/integration/test_*_controller.py -v

# 6. Check coverage
pytest tests/integration/test_*_controller.py --cov=app/controllers --cov-report=term-missing
```

### Tasks
- [ ] Remove all repository imports from controllers
- [ ] Clean up all TODO comments (or mark as deferred with reason)
- [ ] Pass flake8 linting
- [ ] Pass mypy type checking
- [ ] All endpoint tests pass
- [ ] Coverage ≥80% for controllers module

---

## Summary of Changes

| File | Change | Priority |
|------|--------|----------|
| app/di/__init__.py | Create module | P1 |
| app/di/factory.py | Create factory | P1 |
| app/controllers/*.py | Remove repo imports | P1 |
| app/services/stock_batch_service.py | Add get_multi, get_by_id | P2 |
| app/services/stock_movement_service.py | Add get_multi | P2 |
| app/services/location_hierarchy_service.py | Add validate_hierarchy | P2 |
| app/services/analytics_service.py | Add aggregation, export | P2 |
| tests/integration/test_*_controller.py | Create tests | P1 |
| tests/conftest.py | Update DB setup | P2 |

---

## Time Estimate per Task

| Task | Hours | Notes |
|------|-------|-------|
| Create DI factory | 3-4 | Straightforward refactoring |
| Update all controllers | 2-3 | Search and replace |
| Add missing service methods | 4-6 | Database queries needed |
| Complete placeholder endpoints | 3-4 | Service calls + response mapping |
| Create integration tests | 12-14 | 126+ test cases |
| Fix test database | 2-3 | Alembic debugging |
| Quality gate verification | 2-3 | Linting, coverage |
| **TOTAL** | **28-37** | **1 week** |

---

## Approval Checklist

- [ ] All repository imports removed from controllers
- [ ] DI factory module created and working
- [ ] 25+ endpoints tested and passing
- [ ] 80%+ test coverage achieved
- [ ] Test database setup working
- [ ] No linting/type errors
- [ ] All 7 placeholder endpoints completed
- [ ] Code review approved
- [ ] Ready to move to Sprint 05

---

**Last Updated**: 2025-10-21
**Status**: PENDING IMPLEMENTATION
**Estimated Completion**: 2025-10-28
