# ✅ IMMEDIATE FIXES CHECKLIST

**Start Time**: Now
**Target Completion**: 4 hours
**Priority**: 🔴 CRITICAL - SPRINT 5 GATE BLOCKER

---

## Fix #1: Migration Enum Conflict (⏱️ 10 minutes)

### Status: ☐ NOT STARTED

### The File:
```
/home/lucasg/proyectos/DemeterDocs/alembic/versions/2f68e3f132f5_create_warehouses_table.py
```

### What to Do:

**Step 1:** Open the file in editor
```bash
nano /home/lucasg/proyectos/DemeterDocs/alembic/versions/2f68e3f132f5_create_warehouses_table.py
```

**Step 2:** Find line 70 (look for `sa.Enum('GREENHOUSE'...`)

**Step 3:** Change from:
```python
sa.Column('warehouse_type',
    sa.Enum('GREENHOUSE', 'SHADEHOUSE', 'OPEN_FIELD', 'TUNNEL',
            name='warehouse_type_enum'),
    nullable=False
)
```

To:
```python
sa.Column('warehouse_type',
    sa.Enum('GREENHOUSE', 'SHADEHOUSE', 'OPEN_FIELD', 'TUNNEL',
            name='warehouse_type_enum',
            create_type=False),  # ← ADD THIS LINE
    nullable=False
)
```

**Step 4:** Save and exit

### Verification:
```bash
cd /home/lucasg/proyectos/DemeterDocs

# Apply migrations
alembic upgrade head

# Expected output: Should complete without "type already exists" error
# Should show: "Alembic current: 8807863f7d8c"
alembic current

# Verify 28 tables created:
psql -d demeterai -U demeter -c "\dt public.*" | wc -l
# Should show approximately 29 lines (28 tables + header)
```

### ☐ Completed? Move to Fix #2

---

## Fix #2: Initialize Test Database (⏱️ 10 minutes)

### Status: ☐ NOT STARTED

### What to Do:

```bash
cd /home/lucasg/proyectos/DemeterDocs

# Apply migrations to test database (after Fix #1 is done)
export DATABASE_URL="postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test"
alembic upgrade head
```

### Verification:
```bash
# Verify 28 tables in test DB
psql -U demeter_test -d demeterai_test -h localhost -p 5434 -c "\dt public.*" | wc -l
# Should show approximately 29 lines
```

### ☐ Completed? Move to Fix #3

---

## Fix #3: Load Seed Data (⏱️ 30 minutes)

### Status: ☐ NOT STARTED

### Affected Tables:
- [ ] product_sizes (needs ~5 seed records)
- [ ] product_states (needs ~6 seed records)
- [ ] storage_bin_types (needs ~10 seed records)

### What to Do:

**Option A: Manual SQL (Quickest for now)**

```sql
-- Connect to test database:
psql -U demeter_test -d demeterai_test -h localhost -p 5434

-- Insert product_sizes:
INSERT INTO product_sizes (name, height_cm, width_cm, depth_cm, weight_kg) VALUES
('Small', 30, 20, 20, 2.5),
('Medium', 50, 30, 30, 5.0),
('Large', 70, 40, 40, 8.0),
('Extra Large', 100, 50, 50, 12.0),
('Miniature', 15, 10, 10, 1.0);

-- Insert product_states:
INSERT INTO product_states (name, description) VALUES
('Seedling', 'Very young plant'),
('Juvenile', 'Young plant'),
('Mature', 'Adult plant'),
('Flowering', 'In bloom'),
('Fruiting', 'Bearing fruit'),
('Dormant', 'Resting period');

-- Insert storage_bin_types:
INSERT INTO storage_bin_types (name, capacity_units, description) VALUES
('Standard Bin', 100, 'Standard storage bin'),
('Large Bin', 200, 'Large capacity bin'),
('Small Bin', 50, 'Small storage bin'),
('Tall Bin', 150, 'Tall narrow bin'),
('Wide Bin', 120, 'Wide shallow bin'),
('Modular Unit', 80, 'Modular storage unit'),
('Climate Bin', 100, 'Climate-controlled bin'),
('Mobile Bin', 100, 'Mobile storage unit'),
('Shelving Unit', 120, 'Shelving with bins'),
('Wall-Mounted Bin', 50, 'Wall-mounted storage');

-- Exit
\q
```

**Option B: Create Alembic seed migration (Better for long-term)**

```bash
# Create seed migration file:
alembic revision --message "load_reference_data"

# This creates: alembic/versions/[hash]_load_reference_data.py
# Edit that file and add the INSERT statements above
# Then run: alembic upgrade head
```

### Verification:
```bash
psql -U demeter_test -d demeterai_test -h localhost -p 5434 << EOF
SELECT COUNT(*) as product_sizes FROM product_sizes;
SELECT COUNT(*) as product_states FROM product_states;
SELECT COUNT(*) as storage_bin_types FROM storage_bin_types;
EOF

# Expected output:
#  product_sizes | 5
#  product_states | 6
#  storage_bin_types | 10
```

### ☐ Completed? Move to Fix #4

---

## Fix #4: PhotoUploadService Hallucination (⏱️ 30 minutes)

### Status: ☐ NOT STARTED

### Files to Modify:
```
/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py
```

### Changes Required:

**Change 1: Line 42 - Import**
```python
# FROM:
from app.services.location_hierarchy_service import LocationHierarchyService

# TO:
from app.services.storage_location_service import StorageLocationService
```

**Change 2: Line 78 - Class attribute**
```python
# FROM:
location_service: LocationHierarchyService for GPS lookup

# TO:
location_service: StorageLocationService for GPS lookup
```

**Change 3: Line 81 - Constructor**
```python
# FROM:
def __init__(
    self,
    session_service: PhotoProcessingSessionService,
    s3_service: S3ImageService,
    location_service: LocationHierarchyService,
) -> None:

# TO:
def __init__(
    self,
    session_service: PhotoProcessingSessionService,
    s3_service: S3ImageService,
    location_service: StorageLocationService,
) -> None:
```

**Change 4: Lines 148-167 - Method call and logic**
```python
# FROM:
logger.info("Looking up location by GPS coordinates")
hierarchy = await self.location_service.get_full_hierarchy_by_gps(
    gps_longitude, gps_latitude
)

if not hierarchy or not hierarchy.storage_location:
    raise ResourceNotFoundException(
        resource_type="StorageLocation",
        resource_id=f"GPS({gps_longitude}, {gps_latitude})",
    )

storage_location_id = hierarchy.storage_location.location_id

logger.info(
    "Location found via GPS",
    extra={
        "storage_location_id": storage_location_id,
        "warehouse_id": hierarchy.warehouse.warehouse_id if hierarchy.warehouse else None,
    },
)

# TO:
logger.info("Looking up location by GPS coordinates")
location = await self.location_service.get_location_by_gps(
    gps_longitude, gps_latitude
)

if not location:
    raise ResourceNotFoundException(
        resource_type="StorageLocation",
        resource_id=f"GPS({gps_longitude}, {gps_latitude})",
    )

storage_location_id = location.storage_location_id

logger.info(
    "Location found via GPS",
    extra={
        "storage_location_id": storage_location_id,
        "storage_area_id": location.storage_area_id,
    },
)
```

### Verification:
```bash
cd /home/lucasg/proyectos/DemeterDocs

# Test import
python -c "from app.services.photo.photo_upload_service import PhotoUploadService; print('✓ PhotoUploadService OK')"

# Expected: ✓ PhotoUploadService OK
```

### ☐ Completed? Move to Fix #5

---

## Fix #5: Create AnalyticsService (⏱️ 2 hours)

### Status: ☐ NOT STARTED

### Part 5A: Create AnalyticsService (40 lines)

**File**: Create `/home/lucasg/proyectos/DemeterDocs/app/services/analytics_service.py`

```python
"""Analytics Service.

Handles inventory reporting and analytics aggregations.
"""

from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.stock_batch import StockBatch
from app.repositories.stock_batch_repository import StockBatchRepository
from app.schemas.analytics_schema import InventoryReportResponse

logger = get_logger(__name__)


class AnalyticsService:
    """Service for analytics and reporting operations."""

    def __init__(self, stock_batch_repo: StockBatchRepository):
        """Initialize analytics service.

        Args:
            stock_batch_repo: StockBatch repository for inventory queries
        """
        self.stock_batch_repo = stock_batch_repo

    async def get_inventory_report(
        self,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
    ) -> InventoryReportResponse:
        """Generate comprehensive inventory report.

        Args:
            warehouse_id: Optional warehouse filter
            product_id: Optional product filter

        Returns:
            Inventory report with totals and aggregations
        """
        logger.info(
            "Generating inventory report",
            extra={"warehouse_id": warehouse_id, "product_id": product_id},
        )

        stmt = select(
            func.count(StockBatch.batch_id).label("total_batches"),
            func.sum(StockBatch.current_quantity).label("total_plants"),
        )

        if product_id:
            stmt = stmt.where(StockBatch.product_id == product_id)

        result = await self.stock_batch_repo.session.execute(stmt)
        row = result.one()

        logger.info(
            "Inventory report generated",
            extra={
                "total_batches": row.total_batches or 0,
                "total_plants": int(row.total_plants or 0),
            },
        )

        return InventoryReportResponse(
            total_batches=row.total_batches or 0,
            total_plants=int(row.total_plants or 0),
            warehouse_id=warehouse_id,
            product_id=product_id,
        )
```

### Part 5B: Create AnalyticsSchema (20 lines)

**File**: Create `/home/lucasg/proyectos/DemeterDocs/app/schemas/analytics_schema.py`

```python
"""Analytics and Reporting Schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InventoryReportResponse(BaseModel):
    """Inventory report response."""

    total_batches: int = Field(..., description="Total number of stock batches")
    total_plants: int = Field(..., description="Total number of plants")
    warehouse_id: Optional[int] = Field(None, description="Warehouse filter (if applied)")
    product_id: Optional[int] = Field(None, description="Product filter (if applied)")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Report generation timestamp"
    )

    model_config = {"from_attributes": True}
```

### Part 5C: Update analytics_controller

**File**: `/home/lucasg/proyectos/DemeterDocs/app/controllers/analytics_controller.py`

**Remove these imports** (lines 24-30):
```python
# DELETE THESE LINES:
# from sqlalchemy import func, select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.models.stock_batch import StockBatch
# from app.models.stock_movement import StockMovement
```

**Add these imports** (after line 23):
```python
from app.repositories.stock_batch_repository import StockBatchRepository
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics_schema import InventoryReportResponse
```

**Add this dependency injection function** (after get_stock_service):
```python
def get_analytics_service(
    session: AsyncSession = Depends(get_db_session),
) -> AnalyticsService:
    """Dependency injection for AnalyticsService."""
    stock_batch_repo = StockBatchRepository(session)
    return AnalyticsService(stock_batch_repo)
```

**Replace the endpoint** (search for `get_full_inventory_report`):
```python
@router.get(
    "/inventory-report",
    response_model=InventoryReportResponse,
    summary="Get full inventory report",
)
async def get_full_inventory_report(
    warehouse_id: int | None = Query(None, description="Filter by warehouse ID"),
    product_id: int | None = Query(None, description="Filter by product ID"),
    service: AnalyticsService = Depends(get_analytics_service),
) -> InventoryReportResponse:
    """Get comprehensive inventory report (C025).

    Provides current stock levels across all locations.

    Args:
        warehouse_id: Optional warehouse filter
        product_id: Optional product filter

    Returns:
        Comprehensive inventory report

    Raises:
        HTTPException 500: Report generation error
    """
    try:
        logger.info(
            "Generating inventory report",
            extra={"warehouse_id": warehouse_id, "product_id": product_id},
        )

        report = await service.get_inventory_report(
            warehouse_id=warehouse_id,
            product_id=product_id,
        )

        logger.info(
            "Inventory report generated",
            extra={
                "total_batches": report.total_batches,
                "total_plants": report.total_plants,
            },
        )

        return report

    except Exception as e:
        logger.error(
            "Failed to generate inventory report",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate inventory report.",
        )
```

### Verification:
```bash
cd /home/lucasg/proyectos/DemeterDocs

# Test imports
python -c "from app.services.analytics_service import AnalyticsService; print('✓ AnalyticsService OK')"
python -c "from app.schemas.analytics_schema import InventoryReportResponse; print('✓ InventoryReportResponse OK')"

# Expected: Both should print ✓
```

### ☐ Completed? Move to Fix #6

---

## Fix #6: Create LocationRelationshipRepository (⏱️ 30 minutes)

### Status: ☐ NOT STARTED

### File to Create:
```
/home/lucasg/proyectos/DemeterDocs/app/repositories/location_relationship_repository.py
```

### Content:
```python
"""Location Relationship Repository.

Repository for managing location hierarchy relationships.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location_relationships import LocationRelationship
from app.repositories.base import AsyncRepository


class LocationRelationshipRepository(AsyncRepository[LocationRelationship]):
    """Repository for LocationRelationship CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(LocationRelationship, session)
```

### Verification:
```bash
cd /home/lucasg/proyectos/DemeterDocs

# Test import
python -c "from app.repositories.location_relationship_repository import LocationRelationshipRepository; print('✓ LocationRelationshipRepository OK')"

# Expected: ✓ LocationRelationshipRepository OK
```

### ☐ Completed? Move to Fix #7

---

## Fix #7: Fix ML Test Mocks (⏱️ 1 hour)

### Status: ☐ NOT STARTED

### Files to Fix:
- [ ] `/home/lucasg/proyectos/DemeterDocs/tests/unit/services/ml_processing/test_pipeline_coordinator.py`
- [ ] `/home/lucasg/proyectos/DemeterDocs/tests/integration/ml_processing/test_pipeline_integration.py`

### The Problem:
```python
# ❌ WRONG - Mock() cannot be subscripted
detection_results = Mock()

# ✅ CORRECT - Proper YOLO result structure
detection_results = [Mock(boxes=Mock(data=torch.tensor([[0, 0, 100, 100, 0.9, 0]])))]
```

### How to Find and Fix:
```bash
# Find occurrences:
grep -n "Mock()" tests/unit/services/ml_processing/test_pipeline_coordinator.py
grep -n "Mock()" tests/integration/ml_processing/test_pipeline_integration.py

# For each Mock() that represents YOLO results:
# CHANGE: Mock()
# TO: [Mock(boxes=Mock(data=torch.tensor([[0, 0, 100, 100, 0.9, 0]])))]
```

### Verification:
```bash
cd /home/lucasg/proyectos/DemeterDocs

# Run ML tests
pytest tests/unit/services/ml_processing/test_pipeline_coordinator.py -v

# Expected: Tests should pass (not fail with 'Mock' object is not subscriptable)
```

### ☐ Completed? Move to Final Verification

---

## 🎯 FINAL VERIFICATION (⏱️ 15 minutes)

### After Completing ALL Fixes:

```bash
cd /home/lucasg/proyectos/DemeterDocs

echo "=== 1. Alembic Current ==="
alembic current
# Expected: 8807863f7d8c

echo "=== 2. Database Tables ==="
psql -d demeterai -U demeter -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | head -3
# Expected: 28

echo "=== 3. All Imports ==="
python -c "
from app.models import *
from app.repositories import *
from app.services import *
from app.controllers import *
from app.schemas import *
print('✓ ALL IMPORTS OK')
"

echo "=== 4. Run Full Test Suite ==="
pytest tests/ -v --tb=short

echo "=== 5. Coverage Report ==="
pytest tests/ --cov=app --cov-report=term-missing | grep TOTAL
# Expected: should be >= 80%
```

### Success Criteria:
- [ ] Alembic current shows: `8807863f7d8c`
- [ ] Database has 28 tables
- [ ] All imports work without errors
- [ ] Tests: >= 80% passing (target: >1000/1327)
- [ ] No architecture violations
- [ ] No hallucinated methods

---

## 📝 STATUS TRACKING

| Fix | Task | Status | Time | Completed |
|-----|------|--------|------|-----------|
| #1 | Migration enum conflict | ☐ | 10 min | ☐ |
| #2 | Init test database | ☐ | 10 min | ☐ |
| #3 | Load seed data | ☐ | 30 min | ☐ |
| #4 | PhotoUploadService fix | ☐ | 30 min | ☐ |
| #5 | Create AnalyticsService | ☐ | 2 hr | ☐ |
| #6 | LocationRelationshipRepo | ☐ | 30 min | ☐ |
| #7 | Fix ML test mocks | ☐ | 1 hr | ☐ |
| **Final** | **Verification** | ☐ | **15 min** | ☐ |

**Total Time**: ~4 hours 15 minutes

---

## 🚀 YOU'RE READY!

Once all fixes are completed and verification passes, Sprint 5 is ready to begin.

**Good luck! 💪**
