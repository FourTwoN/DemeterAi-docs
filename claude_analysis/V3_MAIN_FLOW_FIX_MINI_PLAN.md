# Team Leader Mini-Plan: V3 Main Photo Upload Flow - Critical Fixes

**Date**: 2025-10-22
**Status**: Ready for Implementation
**Priority**: CRITICAL (BLOCKER issues prevent end-to-end flow)

---

## Executive Summary

**Goal**: Make the V3 main photo upload flow work end-to-end (photo upload → S3 → ML processing → callback → user response)

**Current State**: Flow is broken due to 2 BLOCKER issues + 2 missing components
**Target State**: Complete working flow with production data loaded and workers enabled

**Estimated Effort**: 4-6 hours (2-3 hours for blockers, 2-3 hours for production data + testing)

---

## Task Overview

**Scope**: Fix V3 main photo upload flow
**Epic**: Production Readiness
**Complexity**: 8 points (Medium)
**Blocking Issues**: 2 critical, 2 high-priority

**Flowchart Reference**: `/home/lucasg/proyectos/DemeterDocs/flows/procesamiento_ml_upload_s3_principal/FLUJO PRINCIPAL V3-2025-10-07-201442.mmd`

---

## Critical Issues Analysis

### BLOCKER 1: Signature Mismatch in photo_upload_service.py (Line 236)

**Severity**: CRITICAL - Flow cannot execute
**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py`
**Line**: 236

**Current Code**:
```python
celery_task = ml_parent_task.delay(session.session_id, original_image.s3_key_original)
```

**Expected Signature** (from `ml_tasks.py` line 182-187):
```python
@app.task(bind=True, queue="cpu_queue", max_retries=2)
def ml_parent_task(
    self: Task,
    session_id: int,
    image_data: list[dict[str, Any]],
) -> dict[str, Any]:
```

**Problem**:
1. Current call passes 2 args: `(session_id: UUID, s3_key: str)`
2. Expected signature: `(session_id: int, image_data: list[dict])`
3. Type mismatch: `session.session_id` is UUID, but function expects `int`
4. Missing `image_data` parameter completely

**Root Cause**:
The photo_upload_service.py was implemented before ml_tasks.py signature was finalized. The ML task expects structured metadata for each image, not just an S3 key.

**Impact**:
- Celery task will fail immediately on execution
- TypeError will be raised
- ML pipeline never starts
- User receives "pending" status but processing never completes

---

### BLOCKER 2: Celery Workers Not Enabled in docker-compose.yml

**Severity**: CRITICAL - No workers to process tasks
**File**: `/home/lucasg/proyectos/DemeterDocs/docker-compose.yml`
**Lines**: 184-226

**Current State**: All Celery workers are commented out:
- `celery_cpu` worker (lines 184-203) - COMMENTED
- `celery_io` worker (lines 209-226) - COMMENTED
- `flower` monitoring (lines 232-248) - COMMENTED

**Problem**:
1. Even if photo_upload_service.py calls ml_parent_task.delay(), no worker exists to execute it
2. Tasks will sit in Redis queue indefinitely
3. Users will poll status endpoint forever, never getting results

**Impact**:
- Zero task processing capacity
- Tasks queued but never executed
- Frontend polling timeout (no status updates)
- Production deployment impossible

---

### HIGH-PRIORITY 3: Missing Production Data Loader Script

**Severity**: HIGH - Cannot test with realistic data
**Directory**: `/home/lucasg/proyectos/DemeterDocs/production_data/`

**Current State**:
- CSV files exist in subdirectories:
  - `gps_layers/`
  - `price_list/`
  - `product_category/`
  - `prueba_v1_nave_venta/`
- NO Python script to load these into database

**Problem**:
1. Database likely empty or has only test data
2. GPS location lookup will fail (no storage_locations)
3. ML processing will fail (no storage_location_config)
4. Cannot verify end-to-end flow with production data

**Impact**:
- Cannot test realistic workflow
- GPS lookup returns None
- Flow terminates at STEP 2 (line 148-154 of photo_upload_service.py)
- Production deployment will fail silently

---

### MEDIUM-PRIORITY 4: Architecture Review Needed

**Severity**: MEDIUM - Code quality and maintainability
**Scope**: Verify best practices across the flow

**Areas to Review**:
1. Service→Service pattern enforcement
2. Exception handling centralization
3. Logging consistency
4. Import cleanliness

**Current Observations**:
- photo_upload_service.py correctly uses Service→Service pattern ✅
- ml_tasks.py uses helper functions (_mark_session_*) which call services ✅
- Exception handling looks consistent ✅
- Logging uses structured logging ✅

**Recommendation**: Low risk, but should verify during implementation

---

## Implementation Strategy

### Phase 1: BLOCKER Fixes (Sequential - CRITICAL PATH)

**Priority**: Must be completed first before any testing possible

#### Fix 1.1: Signature Mismatch (2 hours)

**What to Change**:

**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py`
**Lines to Modify**: 233-246

**Current Code (WRONG)**:
```python
# STEP 5: Dispatch ML pipeline (Celery task)
from app.tasks.ml_tasks import ml_parent_task

celery_task = ml_parent_task.delay(session.session_id, original_image.s3_key_original)
task_id = celery_task.id

logger.info(
    "ML pipeline task dispatched",
    extra={
        "task_id": str(task_id),
        "session_id": str(session.session_id),
        "s3_key": original_image.s3_key_original,
    },
)
```

**New Code (CORRECT)**:
```python
# STEP 5: Dispatch ML pipeline (Celery task)
from app.tasks.ml_tasks import ml_parent_task

# Build image_data for ML task
# NOTE: ml_parent_task expects list[dict] with keys:
#   - image_id (int): S3Image database ID
#   - image_path (str): Path to image file
#   - storage_location_id (int): Where photo was taken
image_data = [
    {
        "image_id": original_image.id,  # S3Image.id (database PK, integer)
        "image_path": f"/tmp/uploads/{original_image.image_id}.jpg",  # Temp path
        "storage_location_id": storage_location_id,  # From GPS lookup (line 156)
    }
]

# Call ML task with correct signature
# ml_parent_task(session_id: int, image_data: list[dict])
celery_task = ml_parent_task.delay(
    session_id=session.id,  # PhotoProcessingSession.id (integer PK, NOT session_id UUID)
    image_data=image_data,
)
task_id = celery_task.id

logger.info(
    "ML pipeline task dispatched",
    extra={
        "task_id": str(task_id),
        "session_db_id": session.id,  # Database ID (int)
        "session_uuid": str(session.session_id),  # UUID for external reference
        "image_id": original_image.id,
        "storage_location_id": storage_location_id,
        "num_images": len(image_data),
    },
)
```

**Why This Fix**:
1. **Type Safety**: `session.id` (int) matches `session_id: int` parameter
2. **Structured Data**: `image_data` list provides all metadata ML pipeline needs
3. **Matches Expected Signature**: Exactly matches `ml_parent_task` line 182-187
4. **Temp File Path**: ML task expects local file path (will download from S3 if not found)
5. **Storage Location**: Passes GPS-resolved location for ML processing context

**Testing**:
```python
# Unit test for signature match
def test_photo_upload_calls_ml_task_correctly(mocker):
    # Mock ml_parent_task.delay
    mock_task = mocker.patch("app.services.photo.photo_upload_service.ml_parent_task.delay")

    # Create photo upload service and call upload_photo
    service = PhotoUploadService(...)
    await service.upload_photo(file, gps_lon, gps_lat, user_id)

    # Verify ml_parent_task.delay was called with correct signature
    mock_task.assert_called_once()
    call_args = mock_task.call_args

    # Check positional args
    assert isinstance(call_args.kwargs["session_id"], int)  # NOT UUID
    assert isinstance(call_args.kwargs["image_data"], list)
    assert len(call_args.kwargs["image_data"]) == 1

    # Check image_data structure
    img = call_args.kwargs["image_data"][0]
    assert "image_id" in img
    assert "image_path" in img
    assert "storage_location_id" in img
```

---

#### Fix 1.2: Enable Celery Workers (30 minutes)

**What to Change**:

**File**: `/home/lucasg/proyectos/DemeterDocs/docker-compose.yml`
**Lines to Uncomment**: 184-226 (at minimum)

**Changes Required**:

1. **Uncomment celery_cpu worker** (lines 184-203):
   ```yaml
   celery_cpu:
     build:
       context: .
       dockerfile: Dockerfile
     container_name: demeterai-celery-cpu
     env_file:
       - .env
     environment:
       - DATABASE_URL=postgresql+asyncpg://demeter:demeter_dev_password@db:5432/demeterai
       - DATABASE_URL_SYNC=postgresql+psycopg2://demeter:demeter_dev_password@db:5432/demeterai
       - REDIS_URL=redis://redis:6379/0
       - CELERY_BROKER_URL=redis://redis:6379/0
       - CELERY_RESULT_BACKEND=redis://redis:6379/1
     depends_on:
       db:
         condition: service_healthy
       redis:
         condition: service_healthy
     restart: unless-stopped
     command: celery -A app.celery_app worker --pool=prefork --concurrency=4 --queues=cpu_queue --loglevel=info
   ```

2. **Uncomment celery_io worker** (lines 209-226):
   ```yaml
   celery_io:
     build:
       context: .
       dockerfile: Dockerfile
     container_name: demeterai-celery-io
     env_file:
       - .env
     environment:
       - DATABASE_URL=postgresql+asyncpg://demeter:demeter_dev_password@db:5432/demeterai
       - DATABASE_URL_SYNC=postgresql+psycopg2://demeter:demeter_dev_password@db:5432/demeterai
       - REDIS_URL=redis://redis:6379/0
       - CELERY_BROKER_URL=redis://redis:6379/0
       - CELERY_RESULT_BACKEND=redis://redis:6379/1
     depends_on:
       redis:
         condition: service_healthy
     restart: unless-stopped
     command: celery -A app.celery_app worker --pool=gevent --concurrency=20 --queues=io_queue --loglevel=info
   ```

3. **OPTIONAL: Uncomment Flower monitoring** (lines 232-248) for debugging:
   ```yaml
   flower:
     build:
       context: .
       dockerfile: Dockerfile
     container_name: demeterai-flower
     ports:
       - "5555:5555"
     env_file:
       - .env
     environment:
       - CELERY_BROKER_URL=redis://redis:6379/0
       - CELERY_RESULT_BACKEND=redis://redis:6379/1
     depends_on:
       redis:
         condition: service_healthy
     restart: unless-stopped
     command: celery -A app.celery_app flower --port=5555
   ```

**Why This Fix**:
1. **cpu_queue Worker**: Processes `ml_parent_task` and `ml_aggregation_callback`
2. **io_queue Worker**: Processes S3 uploads (if implemented as Celery tasks)
3. **Flower**: Optional monitoring UI at http://localhost:5555
4. **Worker Topology**: Matches queue routing in `celery_app.py` lines 69-78

**Note on GPU Worker**:
The GPU worker is intentionally NOT included in this fix because:
- It requires NVIDIA GPU + CUDA drivers
- Development environment is CPU-only
- ml_child_task (line 308) is designed to work on CPU (slower, but functional)
- Production deployment will add GPU worker separately

**Testing**:
```bash
# Start workers
docker compose up celery_cpu celery_io -d

# Verify workers are running
docker compose ps | grep celery

# Check worker logs
docker compose logs celery_cpu --tail=50
docker compose logs celery_io --tail=50

# Verify workers registered with Redis
docker compose exec redis redis-cli
> KEYS celery*
> LLEN celery  # Should show queue length

# Check Flower (if enabled)
curl http://localhost:5555/api/workers
```

---

### Phase 2: Production Data Loader (Parallel with Testing)

**Priority**: High - Enables realistic testing

#### Fix 2.1: Create Production Data Loader Script (2-3 hours)

**File to Create**: `/home/lucasg/proyectos/DemeterDocs/scripts/load_production_data.py`

**Purpose**:
Load production CSV files into database to enable:
1. GPS location lookup (storage_locations table)
2. ML processing configuration (storage_location_config table)
3. Product hierarchy (product_category, product_family, products)
4. Pricing data (price_list)

**Implementation**:

```python
"""Production Data Loader - Load CSV files into database.

This script loads production data from CSV files into the database:
- GPS layers (warehouses, storage_areas, storage_locations)
- Product categories and families
- Price lists
- Storage location configurations

Usage:
    python scripts/load_production_data.py --env development

Architecture:
    Uses repository pattern (NOT raw SQL)
    Validates data before insertion
    Handles duplicates gracefully (upsert logic)
    Logs all operations

Data Sources:
    /production_data/gps_layers/*.csv
    /production_data/product_category/*.csv
    /production_data/price_list/*.csv
"""

import asyncio
import csv
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse
from app.repositories.storage_location_repository import StorageLocationRepository
from app.repositories.warehouse_repository import WarehouseRepository

logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent.parent
PRODUCTION_DATA_DIR = BASE_DIR / "production_data"


async def load_gps_layers(session: AsyncSession) -> None:
    """Load GPS layer data (warehouses, storage locations).

    Expected CSV Format:
        warehouse_name,latitude,longitude,storage_area_name,storage_location_code

    Business Rules:
        - Create warehouse if not exists
        - Create storage_area if not exists (linked to warehouse)
        - Create storage_location if not exists (linked to area)
        - Use PostGIS ST_SetSRID(ST_MakePoint(lon, lat), 4326) for GPS
    """
    logger.info("Loading GPS layers data...")

    gps_dir = PRODUCTION_DATA_DIR / "gps_layers"
    if not gps_dir.exists():
        logger.warning(f"GPS layers directory not found: {gps_dir}")
        return

    warehouse_repo = WarehouseRepository(session)
    location_repo = StorageLocationRepository(session)

    loaded_count = 0

    for csv_file in gps_dir.glob("*.csv"):
        logger.info(f"Processing {csv_file.name}...")

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # TODO: Implement warehouse/area/location creation logic
                # This is a template - actual implementation depends on CSV structure
                pass

        logger.info(f"Loaded {loaded_count} GPS records from {csv_file.name}")


async def load_product_categories(session: AsyncSession) -> None:
    """Load product category hierarchy.

    Expected CSV Format:
        category_name,family_name,product_code,product_name,scientific_name
    """
    logger.info("Loading product categories...")
    # TODO: Implement
    pass


async def load_price_lists(session: AsyncSession) -> None:
    """Load price list data.

    Expected CSV Format:
        product_code,packaging_type,price,currency,effective_date
    """
    logger.info("Loading price lists...")
    # TODO: Implement
    pass


async def main() -> None:
    """Main loader entry point."""
    logger.info("Starting production data load...")

    async for session in get_db_session():
        try:
            # Load data in dependency order
            await load_gps_layers(session)
            await load_product_categories(session)
            await load_price_lists(session)

            # Commit transaction
            await session.commit()
            logger.info("Production data load completed successfully")

        except Exception as exc:
            logger.error(f"Production data load failed: {exc}", exc_info=True)
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
```

**Why This Approach**:
1. **Repository Pattern**: Uses existing repositories (maintains consistency)
2. **Async**: Matches application architecture
3. **Transactional**: Single transaction (all-or-nothing)
4. **Idempotent**: Can be run multiple times (upsert logic)
5. **Logging**: Full audit trail

**CSV Analysis Required**:
Before implementation, Python Expert needs to:
1. Examine actual CSV files in `/production_data/*/`
2. Determine exact column names and data types
3. Map CSV columns to database schema
4. Implement validation logic

**Testing**:
```bash
# Run loader script
python scripts/load_production_data.py

# Verify data loaded
docker compose exec db psql -U demeter -d demeterai -c "SELECT COUNT(*) FROM warehouses;"
docker compose exec db psql -U demeter -d demeterai -c "SELECT COUNT(*) FROM storage_locations;"
docker compose exec db psql -U demeter -d demeterai -c "SELECT COUNT(*) FROM products;"
```

---

### Phase 3: Architecture Review (Parallel with Phase 1)

**Priority**: Medium - Quality assurance

#### Review 3.1: Service→Service Pattern Verification (30 minutes)

**Checklist**:

✅ **photo_upload_service.py** (lines 80-95):
```python
def __init__(
    self,
    session_service: PhotoProcessingSessionService,  # ✅ Service
    s3_service: S3ImageService,  # ✅ Service
    location_service: StorageLocationService,  # ✅ Service
) -> None:
```
**PASS**: Only services injected, no direct repository access

✅ **ml_tasks.py** (lines 632-708):
```python
def _mark_session_processing(session_id: int, celery_task_id: str) -> None:
    async def _update() -> None:
        async for session in get_db_session():
            repo = PhotoProcessingSessionRepository(session)
            service = PhotoProcessingSessionService(repo)  # ✅ Uses service
            await service.mark_session_processing(session_id, celery_task_id)
```
**PASS**: Helper functions create service instances (correct pattern for Celery tasks)

**Recommendation**: No changes needed ✅

---

#### Review 3.2: Exception Handling Centralization (30 minutes)

**Check**: All exceptions from `app.core.exceptions`

✅ **photo_upload_service.py**:
```python
from app.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
```
**PASS**: Uses centralized exceptions ✅

✅ **ml_tasks.py**:
```python
from app.core.exceptions import (
    CircuitBreakerException,
    ValidationException,
)
```
**PASS**: Uses centralized exceptions ✅

**Recommendation**: No changes needed ✅

---

#### Review 3.3: Logging Consistency (15 minutes)

**Check**: Structured logging with `extra` dict

✅ **photo_upload_service.py** (line 133-141):
```python
logger.info(
    "Starting photo upload workflow",
    extra={
        "gps_longitude": gps_longitude,
        "gps_latitude": gps_latitude,
        "user_id": user_id,
        "filename": file.filename,
    },
)
```
**PASS**: Consistent structured logging ✅

✅ **ml_tasks.py** (line 228-231):
```python
logger.info(
    f"ML parent task started for session {session_id} with {len(image_data)} images",
    extra={"session_id": session_id, "num_images": len(image_data), "task_id": self.request.id},
)
```
**PASS**: Consistent structured logging ✅

**Recommendation**: No changes needed ✅

---

#### Review 3.4: Import Cleanliness (15 minutes)

**Check**: No circular imports, clean import structure

✅ **photo_upload_service.py**:
- Imports services (no repositories) ✅
- Imports from core, models, schemas ✅
- Lazy import of Celery task (line 234) to avoid circular import ✅

✅ **ml_tasks.py**:
- Imports from app.celery_app ✅
- Imports services and repositories ✅
- No circular imports detected ✅

**Recommendation**: No changes needed ✅

---

## Files to Create/Modify

### Files to Modify (2 files)

1. **`/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py`**
   - Lines: 233-246 (CRITICAL fix)
   - Changes: Fix ml_parent_task.delay() call signature
   - Estimated lines changed: ~15 lines

2. **`/home/lucasg/proyectos/DemeterDocs/docker-compose.yml`**
   - Lines: 184-226 (CRITICAL fix)
   - Changes: Uncomment celery_cpu and celery_io workers
   - Estimated lines changed: ~45 lines (uncomment)

### Files to Create (1-2 files)

3. **`/home/lucasg/proyectos/DemeterDocs/scripts/load_production_data.py`** (NEW)
   - Purpose: Load production CSV data into database
   - Estimated lines: ~300-500 lines
   - Priority: HIGH

4. **`/home/lucasg/proyectos/DemeterDocs/tests/integration/test_v3_main_flow_e2e.py`** (NEW, OPTIONAL)
   - Purpose: End-to-end integration test for V3 flow
   - Estimated lines: ~200-300 lines
   - Priority: MEDIUM

---

## Testing Strategy

### Phase 1 Testing: Signature Fix Verification

**Test 1.1: Unit Test - Signature Match**
```python
# File: tests/unit/services/test_photo_upload_service_signature.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.photo.photo_upload_service import PhotoUploadService


@pytest.mark.asyncio
async def test_upload_photo_calls_ml_task_with_correct_signature(mocker):
    """Verify ml_parent_task.delay() is called with correct arguments."""

    # Mock dependencies
    mock_session_service = AsyncMock()
    mock_s3_service = AsyncMock()
    mock_location_service = AsyncMock()

    # Mock location lookup
    mock_location = MagicMock()
    mock_location.storage_location_id = 42
    mock_location.storage_area_id = 10
    mock_location_service.get_location_by_gps.return_value = mock_location

    # Mock S3 upload
    mock_s3_image = MagicMock()
    mock_s3_image.id = 100  # Database ID (integer)
    mock_s3_image.image_id = "uuid-here"  # UUID
    mock_s3_image.s3_key_original = "original/2025/10/22/uuid-here.jpg"
    mock_s3_service.upload_original.return_value = mock_s3_image

    # Mock session creation
    mock_session = MagicMock()
    mock_session.id = 123  # Database ID (integer)
    mock_session.session_id = "session-uuid"  # UUID
    mock_session_service.create_session.return_value = mock_session

    # Mock ml_parent_task.delay
    mock_ml_task = mocker.patch(
        "app.services.photo.photo_upload_service.ml_parent_task.delay"
    )
    mock_celery_result = MagicMock()
    mock_celery_result.id = "celery-task-id"
    mock_ml_task.return_value = mock_celery_result

    # Create service and upload photo
    service = PhotoUploadService(
        session_service=mock_session_service,
        s3_service=mock_s3_service,
        location_service=mock_location_service,
    )

    # Mock file
    mock_file = AsyncMock()
    mock_file.filename = "test.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.read.return_value = b"fake image data"

    # Execute upload
    result = await service.upload_photo(
        file=mock_file,
        gps_longitude=-70.123,
        gps_latitude=-33.456,
        user_id=1,
    )

    # VERIFY: ml_parent_task.delay() called with correct signature
    mock_ml_task.assert_called_once()
    call_kwargs = mock_ml_task.call_args.kwargs

    # Check session_id is integer (not UUID)
    assert call_kwargs["session_id"] == 123  # Database ID
    assert isinstance(call_kwargs["session_id"], int)

    # Check image_data is list of dicts
    assert isinstance(call_kwargs["image_data"], list)
    assert len(call_kwargs["image_data"]) == 1

    # Check image_data structure
    img_data = call_kwargs["image_data"][0]
    assert img_data["image_id"] == 100  # S3Image database ID
    assert "image_path" in img_data
    assert img_data["storage_location_id"] == 42

    # Verify response
    assert result.task_id == "celery-task-id"
    assert result.session_id == 123
```

**Expected Result**: Test PASSES ✅

---

**Test 1.2: Integration Test - Worker Availability**
```bash
#!/bin/bash
# File: tests/integration/test_celery_workers_available.sh

echo "Testing Celery worker availability..."

# Start workers
docker compose up celery_cpu celery_io -d

# Wait for workers to start
sleep 10

# Check worker processes
CPU_WORKER=$(docker compose ps celery_cpu | grep "Up" | wc -l)
IO_WORKER=$(docker compose ps celery_io | grep "Up" | wc -l)

if [ "$CPU_WORKER" -eq 1 ] && [ "$IO_WORKER" -eq 1 ]; then
    echo "✅ Both workers are running"
else
    echo "❌ Workers not running: CPU=$CPU_WORKER, IO=$IO_WORKER"
    exit 1
fi

# Check Redis queue connectivity
docker compose exec -T redis redis-cli ping | grep PONG
if [ $? -eq 0 ]; then
    echo "✅ Redis connectivity OK"
else
    echo "❌ Redis connectivity FAILED"
    exit 1
fi

# Test task dispatch (simple ping task)
docker compose exec -T api python -c "
from app.celery_app import app

@app.task(queue='cpu_queue')
def ping_task():
    return 'pong'

result = ping_task.delay()
print(f'Task dispatched: {result.id}')
"

echo "✅ All worker tests passed"
```

**Expected Result**: All checks PASS ✅

---

### Phase 2 Testing: Production Data Verification

**Test 2.1: Data Loader Execution**
```bash
# Run data loader
python scripts/load_production_data.py

# Verify counts
docker compose exec db psql -U demeter -d demeterai -c "
SELECT
    (SELECT COUNT(*) FROM warehouses) AS warehouses,
    (SELECT COUNT(*) FROM storage_areas) AS storage_areas,
    (SELECT COUNT(*) FROM storage_locations) AS storage_locations,
    (SELECT COUNT(*) FROM products) AS products;
"
```

**Expected Result**: Non-zero counts for all tables ✅

---

**Test 2.2: GPS Lookup Verification**
```python
# File: tests/integration/test_gps_lookup_with_production_data.py

import pytest

from app.db.session import get_db_session
from app.repositories.storage_location_repository import StorageLocationRepository
from app.services.storage_location_service import StorageLocationService


@pytest.mark.asyncio
async def test_gps_lookup_finds_location():
    """Verify GPS lookup works with production data."""

    async for session in get_db_session():
        repo = StorageLocationRepository(session)
        service = StorageLocationService(repo)

        # Use GPS coordinates from production data
        # TODO: Replace with actual coordinates from CSV
        location = await service.get_location_by_gps(
            longitude=-70.123,
            latitude=-33.456,
        )

        assert location is not None
        assert location.storage_location_id is not None
        assert location.storage_area_id is not None
```

**Expected Result**: Test PASSES (location found) ✅

---

### Phase 3 Testing: End-to-End Flow

**Test 3.1: Complete V3 Flow Integration Test**
```python
# File: tests/integration/test_v3_main_flow_e2e.py

import pytest
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
@pytest.mark.slow
def test_v3_main_flow_end_to_end():
    """End-to-end test: Photo upload → S3 → ML → Callback → Response.

    Flow:
    1. POST /api/stock/photo (upload photo with GPS)
    2. Poll GET /api/photo-sessions/{session_id} (wait for completion)
    3. Verify final status is "completed"
    4. Verify detections and estimations exist
    """
    client = TestClient(app)

    # STEP 1: Upload photo with GPS coordinates
    test_image_path = Path(__file__).parent / "fixtures" / "test_plant_image.jpg"

    with open(test_image_path, "rb") as f:
        response = client.post(
            "/api/stock/photo",
            files={"file": ("test.jpg", f, "image/jpeg")},
            data={
                "gps_longitude": -70.123,  # From production data
                "gps_latitude": -33.456,
                "user_id": 1,
            },
        )

    assert response.status_code == 202  # Accepted
    data = response.json()

    session_id = data["session_id"]
    task_id = data["task_id"]
    poll_url = data["poll_url"]

    assert session_id is not None
    assert task_id is not None

    # STEP 2: Poll for completion (max 5 minutes for CPU processing)
    max_wait = 300  # 5 minutes
    poll_interval = 5  # 5 seconds
    elapsed = 0

    final_status = None

    while elapsed < max_wait:
        response = client.get(poll_url)
        assert response.status_code == 200

        session_data = response.json()
        status = session_data["status"]

        if status in ["completed", "warning", "failed"]:
            final_status = status
            break

        time.sleep(poll_interval)
        elapsed += poll_interval

    # STEP 3: Verify completion
    assert final_status is not None, "Task did not complete within timeout"
    assert final_status in ["completed", "warning"], f"Task failed: {final_status}"

    # STEP 4: Verify results
    assert session_data["total_detected"] > 0 or session_data["total_estimated"] > 0
    assert session_data["avg_confidence"] > 0.0

    print(f"✅ E2E test passed:")
    print(f"   - Status: {final_status}")
    print(f"   - Detected: {session_data['total_detected']}")
    print(f"   - Estimated: {session_data['total_estimated']}")
    print(f"   - Confidence: {session_data['avg_confidence']:.2%}")
```

**Expected Result**: Test PASSES within 5 minutes ✅

---

## Dependencies Between Fixes

### Dependency Graph

```
BLOCKER 1 (Signature Fix) ←──────┐
                                  │
BLOCKER 2 (Enable Workers) ←─────┤── BOTH REQUIRED
                                  │   for any execution
                                  │
                                  ↓
                            Can Execute Tasks
                                  │
                                  ├──→ HIGH-PRIORITY 3 (Production Data)
                                  │     └─→ Enables GPS lookup
                                  │         └─→ Enables ML processing
                                  │
                                  └──→ MEDIUM-PRIORITY 4 (Architecture Review)
                                        └─→ Quality assurance (parallel)
```

### Execution Order

**Sequential (CRITICAL PATH)**:
1. Fix BLOCKER 1 (signature mismatch) - REQUIRED
2. Fix BLOCKER 2 (enable workers) - REQUIRED
3. Test worker availability - VERIFY
4. Fix HIGH-PRIORITY 3 (production data) - REQUIRED for realistic testing

**Parallel (CAN RUN SIMULTANEOUSLY)**:
- Architecture review (MEDIUM-PRIORITY 4) - While waiting for ML processing
- Write integration tests - While fixing blockers

---

## Acceptance Criteria

### Blocker Fixes

- [ ] photo_upload_service.py line 236 fixed (correct signature)
- [ ] ml_parent_task.delay() called with `(session_id: int, image_data: list[dict])`
- [ ] Unit test verifies signature match
- [ ] docker-compose.yml workers uncommented
- [ ] celery_cpu worker starts successfully
- [ ] celery_io worker starts successfully
- [ ] Workers visible in Flower UI (if enabled)

### Production Data

- [ ] load_production_data.py script created
- [ ] Script loads GPS layers (warehouses, storage_locations)
- [ ] Script loads product categories
- [ ] Script loads price lists
- [ ] Database populated with non-zero counts
- [ ] GPS lookup returns valid storage_location

### End-to-End Flow

- [ ] POST /api/stock/photo returns 202 Accepted
- [ ] Celery task dispatched successfully
- [ ] ML processing completes (status → "completed" or "warning")
- [ ] PhotoProcessingSession updated with results
- [ ] Frontend can poll and receive final results
- [ ] No errors in Celery worker logs

### Architecture Quality

- [ ] Service→Service pattern enforced (no violations)
- [ ] Exception handling centralized (uses app.core.exceptions)
- [ ] Logging structured and consistent
- [ ] No circular imports
- [ ] Code review passed

---

## Performance Expectations

### Photo Upload Endpoint
- **Target**: < 500ms response time (return 202 Accepted)
- **Includes**: File validation, GPS lookup, S3 upload, session creation, task dispatch

### ML Processing (CPU Mode)
- **Target**: 5-10 minutes per 4000×3000px photo
- **Bottleneck**: YOLO inference on CPU (no GPU available in dev)
- **Note**: Production with GPU reduces to 1-3 minutes

### End-to-End Flow
- **Target**: < 15 minutes from upload to completion (CPU mode)
- **Includes**: Upload, S3, ML pipeline, callback aggregation

---

## Rollback Plan

### If Fix 1.1 Breaks Something
```bash
# Revert photo_upload_service.py
git checkout HEAD -- app/services/photo/photo_upload_service.py

# Restart API
docker compose restart api
```

### If Fix 1.2 Breaks Something
```bash
# Comment out workers again
# Edit docker-compose.yml lines 184-226
# Restore comments

# Restart stack
docker compose down
docker compose up -d
```

### If Production Data Loader Fails
```bash
# Rollback database
docker compose exec db psql -U demeter -d demeterai -c "
DELETE FROM storage_locations WHERE created_at > NOW() - INTERVAL '1 hour';
DELETE FROM products WHERE created_at > NOW() - INTERVAL '1 hour';
"
```

---

## Next Steps After Completion

1. **Notify Scrum Master**: All blockers resolved
2. **Run full test suite**: `pytest tests/ -v`
3. **Manual E2E test**: Upload real photo via API
4. **Monitor Celery**: Check Flower UI for task success
5. **Review logs**: Verify no errors in worker logs
6. **Update documentation**: Document production data loading process
7. **Create PR**: Commit fixes with detailed description

---

## Handoff Notes

### To Python Expert
**Task**: Implement fixes in photo_upload_service.py and create production data loader

**Priority Order**:
1. Fix signature mismatch (BLOCKER 1) - 2 hours
2. Create load_production_data.py (HIGH-PRIORITY 3) - 2-3 hours

**Key Requirements**:
- Use exact signature from ml_tasks.py line 182-187
- Validate CSV structure before implementing loader
- Test signature fix with unit test
- Test data loader with database queries

**Update task file** with progress every 30 minutes.

---

### To Testing Expert
**Task**: Write integration tests for V3 flow

**Test Coverage**:
1. Signature match unit test (CRITICAL)
2. Worker availability integration test
3. Production data verification
4. End-to-end flow test (OPTIONAL - can be manual for now)

**Start immediately** after Python Expert fixes signature (can work in parallel on test structure).

---

### To Database Expert (On-Call)
**Available for**:
- CSV structure clarification (production_data/)
- Schema questions for data loader
- PostGIS query help for GPS lookup

**Expected questions**:
- "What columns are in gps_layers/*.csv?"
- "How to use ST_MakePoint for GPS coordinates?"
- "What's the FK relationship for storage_location → storage_area?"

---

## Critical Rules (NEVER VIOLATE)

### Rule 1: Signature Must Match Exactly
```python
# CORRECT ✅
ml_parent_task.delay(
    session_id=session.id,  # int (database PK)
    image_data=[{
        "image_id": int,
        "image_path": str,
        "storage_location_id": int,
    }],
)

# WRONG ❌
ml_parent_task.delay(session.session_id, original_image.s3_key_original)
```

### Rule 2: Workers Must Be Running
```bash
# Verify before ANY testing
docker compose ps | grep celery
# Should show: celery_cpu (Up), celery_io (Up)
```

### Rule 3: Production Data Required for GPS Lookup
```python
# Will fail if database empty
location = await self.location_service.get_location_by_gps(lon, lat)
if not location:  # ← This happens if no data loaded
    raise ResourceNotFoundException(...)
```

### Rule 4: Test Signature Fix First
```bash
# BEFORE committing, MUST verify
pytest tests/unit/services/test_photo_upload_service_signature.py -v
# Expected: PASSED ✅
```

---

## Estimated Timeline

### Day 1 (4-6 hours)
- **Hour 1**: Python Expert fixes signature mismatch + unit test
- **Hour 2**: DevOps uncomments workers + verifies startup
- **Hour 3-4**: Python Expert creates production data loader script
- **Hour 5**: Python Expert loads production data + verifies
- **Hour 6**: Testing Expert runs integration tests

### Day 2 (Optional - E2E Testing)
- **Hour 1**: Manual E2E test with real photo
- **Hour 2**: Review Celery logs and Flower monitoring
- **Hour 3**: Write comprehensive E2E integration test
- **Hour 4**: Documentation and handoff to Scrum Master

---

## Success Metrics

### Blocker Resolution
- ✅ Signature mismatch fixed (unit test passes)
- ✅ Workers running (docker ps shows "Up")
- ✅ Tasks dispatched (Celery logs show task execution)

### Production Readiness
- ✅ Production data loaded (non-zero database counts)
- ✅ GPS lookup succeeds (finds storage_location)
- ✅ ML processing completes (session status → "completed")

### Quality Assurance
- ✅ All tests passing (unit + integration)
- ✅ No errors in logs (API + Celery workers)
- ✅ Architecture review passed (Service→Service pattern enforced)

---

**FINAL APPROVAL REQUIRED**: After all fixes complete, run full quality gate check before marking DONE.

**Team Leader Sign-Off**: [Pending completion]

---

**Last Updated**: 2025-10-22
**Plan Version**: 1.0
**Status**: Ready for Implementation
