# Architecture Principles - DemeterAI v2.0
## Clean Architecture & Core Rules

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**⚠️ CRITICAL**: These rules are MANDATORY. Violations will be caught in code review.

---

## Clean Architecture Overview

DemeterAI follows **Clean Architecture** (aka Hexagonal Architecture, Ports & Adapters):

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FastAPI Controllers (HTTP Concerns Only)               │   │
│  │  - Route definitions                                    │   │
│  │  - Pydantic validation                                  │   │
│  │  - Status codes (200, 404, 500)                         │   │
│  │  - NO business logic                                    │   │
│  └─────────────────────┬───────────────────────────────────┘   │
└────────────────────────┼───────────────────────────────────────┘
                         │ Depends on ↓
┌────────────────────────▼───────────────────────────────────────┐
│                     APPLICATION LAYER                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Services (Business Logic & Orchestration)              │   │
│  │  - Coordinate operations                                │   │
│  │  - Call other services (NOT repositories directly)      │   │
│  │  - Transform schemas ↔ models                           │   │
│  │  - Enforce business rules                               │   │
│  └─────────────────────┬───────────────────────────────────┘   │
└────────────────────────┼───────────────────────────────────────┘
                         │ Depends on ↓
┌────────────────────────▼───────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Repositories (Data Access)                             │   │
│  │  - SQLAlchemy queries                                   │   │
│  │  - CRUD operations                                      │   │
│  │  - NO business logic                                    │   │
│  └─────────────────────┬───────────────────────────────────┘   │
└────────────────────────┼───────────────────────────────────────┘
                         │ Depends on ↓
┌────────────────────────▼───────────────────────────────────────┐
│                      DATABASE LAYER                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL 18 + PostGIS                                │   │
│  │  - Single source of truth                               │   │
│  │  - Schema defined by migrations (Alembic)               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Tenets (MANDATORY)

### 1. Dependency Rule

**Rule**: Dependencies point INWARD (Domain ← Application ← Infrastructure)

✅ **Allowed**:
- Controllers depend on Services
- Services depend on Repositories
- Services depend on other Services
- Repositories depend on Database models

❌ **Forbidden**:
- Services depending on Controllers (inverted dependency)
- Models depending on Services
- Business logic in Controllers or Repositories

### 2. Database Independence

**Rule**: Business logic doesn't know about PostgreSQL or SQLAlchemy

✅ **Correct**:
```python
class StockMovementService:
    def __init__(self, repo: StockMovementRepository):
        self.repo = repo  # Interface/abstract dependency

    async def create_movement(self, data: dict):
        # Business logic here
        return await self.repo.create(data)
```

❌ **Incorrect**:
```python
class StockMovementService:
    async def create_movement(self, session: AsyncSession, data: dict):
        # Direct SQLAlchemy usage in service = BAD
        movement = StockMovement(**data)
        session.add(movement)
```

### 3. UI Independence

**Rule**: Business logic doesn't know about FastAPI or HTTP

✅ **Correct**:
- Services return domain objects or DTOs
- Controllers convert to HTTP responses

❌ **Incorrect**:
- Services returning HTTP status codes
- Services raising HTTPException

### 4. Framework Independence

**Rule**: Core logic portable to other frameworks (Flask, Django, CLI)

✅ **Correct**:
- Services have no FastAPI imports
- Business logic in pure Python functions

❌ **Incorrect**:
- Business logic inside FastAPI route handlers
- Services depending on FastAPI's Request/Response objects

### 5. Testability

**Rule**: Business logic testable without DB/API/External services

✅ **Correct**:
```python
# Test with mocked repository
async def test_stock_service_create():
    mock_repo = Mock(spec=StockMovementRepository)
    service = StockMovementService(mock_repo)

    result = await service.create_movement({"quantity": 100})

    mock_repo.create.assert_called_once()
```

❌ **Incorrect**:
```python
# Test requires real database
async def test_stock_service_create(real_db_session):
    service = StockMovementService(real_db_session)
    # Can't test without DB = poor testability
```

---

## CRITICAL Rule: Service-to-Service Communication

### ⚠️ NEVER VIOLATE THIS RULE ⚠️

**Rule**: Service A calls Service B's methods (NOT Service B's repository)

### ✅ CORRECT Pattern

```
Controller → Service A → Service B → Repository B
                      ↓
                  Repository A
```

**Example**:
```python
class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_service: StorageLocationConfigService,  # ← Service
        batch_service: StockBatchService                # ← Service
    ):
        self.repo = repo
        self.config_service = config_service
        self.batch_service = batch_service

    async def create_manual_initialization(self, request):
        # ✅ Call config_service (NOT config_repo)
        config = await self.config_service.get_by_location(request.location_id)

        # ✅ Call batch_service (NOT batch_repo)
        batch = await self.batch_service.create_from_movement(movement)
```

### ❌ FORBIDDEN Pattern

```
Controller → Service A → Repository B  (VIOLATION)
                      ↓
                  Repository A
```

**Bad Example**:
```python
class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_repo: StorageLocationConfigRepository,  # ❌ Direct repo
        batch_repo: StockBatchRepository                # ❌ Direct repo
    ):
        self.repo = repo
        self.config_repo = config_repo  # WRONG
        self.batch_repo = batch_repo    # WRONG

    async def create_manual_initialization(self, request):
        # ❌ Direct repo access violates encapsulation
        config = await self.config_repo.get_by_location(request.location_id)
```

**Why This is Wrong**:
- Violates encapsulation (Service B owns Repository B's logic)
- Bypasses business rules in Service B
- Makes testing harder (need to mock multiple repos)
- Duplicates logic across services

---

## Layer Responsibilities

### Controllers (Presentation Layer)

**Location**: `/app/controllers/`

**DO**:
- ✅ Define FastAPI routes (`@router.get`, `@router.post`)
- ✅ Validate input with Pydantic schemas
- ✅ Call service layer methods
- ✅ Return HTTP responses with proper status codes
- ✅ Handle request/response serialization

**DON'T**:
- ❌ Business logic
- ❌ Database queries
- ❌ Call repositories directly
- ❌ Complex data transformations

**Template**:
```python
from fastapi import APIRouter, Depends, status
from app.services.stock_movement_service import StockMovementService
from app.schemas.stock_schema import ManualStockInitRequest

router = APIRouter()

@router.post("/stock/manual", status_code=status.HTTP_201_CREATED)
async def initialize_stock_manually(
    request: ManualStockInitRequest,
    service: StockMovementService = Depends()
):
    """Controller: HTTP concerns only."""
    result = await service.create_manual_initialization(request)
    return result
```

### Services (Application Layer)

**Location**: `/app/services/`

**DO**:
- ✅ Implement business rules
- ✅ Coordinate multi-step operations
- ✅ Call other services (inter-service communication)
- ✅ Transform Pydantic schemas ↔ SQLAlchemy models
- ✅ Enforce validations (config checks, business constraints)
- ✅ Handle complex calculations

**DON'T**:
- ❌ Know about HTTP (no FastAPI imports)
- ❌ Call repositories from other services directly
- ❌ Handle database connections (use dependency injection)

**Communication Rule**:
```
✅ Service A → Service B → Repository B
❌ Service A → Repository B (FORBIDDEN)
```

### Repositories (Infrastructure Layer)

**Location**: `/app/repositories/`

**DO**:
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ SQLAlchemy queries
- ✅ Database transaction management
- ✅ Eager/lazy loading optimization

**DON'T**:
- ❌ Business logic
- ❌ Call other repositories
- ❌ Know about Pydantic schemas (work with SQLAlchemy models only)

**Base Pattern**:
```python
from typing import Generic, TypeVar, Type, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

ModelType = TypeVar("ModelType")

class AsyncRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: int) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

---

## Design Patterns (MANDATORY)

### 1. Repository Pattern

**Purpose**: Abstract database access

✅ **Benefits**:
- Testability (mock repositories in tests)
- Flexibility (swap ORM/raw SQL without changing services)
- Reusability (repositories shared across services)

### 2. Dependency Injection

**Purpose**: Loose coupling, easy testing

**Implementation**: FastAPI's `Depends()`

```python
from fastapi import Depends
from app.db.session import get_db_session

async def get_stock_service(
    session: AsyncSession = Depends(get_db_session)
) -> StockMovementService:
    repo = StockMovementRepository(StockMovement, session)
    config_service = StorageLocationConfigService(...)
    return StockMovementService(repo, config_service)

@router.post("/stock/manual")
async def manual_init(
    service: StockMovementService = Depends(get_stock_service)
):
    return await service.create_manual_initialization(request)
```

### 3. Unit of Work (Transaction Management)

**Purpose**: Ensure all-or-nothing transactions

```python
@asynccontextmanager
async def transaction_scope():
    session = sessionmaker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### 4. Model Singleton (ML Models)

**Purpose**: Load YOLO models once per worker (NOT per task)

**Critical for GPU**: Prevents 2-3s model load overhead per photo

```python
class ModelCache:
    _instances = {}
    _lock = Lock()

    @classmethod
    def get_model(cls, worker_id: int):
        with cls._lock:
            key = f'yolo_v11_seg_{worker_id}'
            if key not in cls._instances:
                model = YOLO('yolov11m-seg.pt')
                model.to(f'cuda:{worker_id}')
                model.fuse()
                cls._instances[key] = model
            return cls._instances[key]
```

### 5. Circuit Breaker (S3 Uploads)

**Purpose**: Prevent cascading failures

```python
import pybreaker

s3_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60
)

@s3_breaker
def upload_to_s3(file, bucket, key):
    return s3_client.upload_file(file, bucket, key)
```

---

## Database as Source of Truth

### Principle

**PostgreSQL database schema is the authoritative reference**

✅ **All diagrams, flows, and documentation MUST align with the database**

### Rules

1. **Schema First**: Database migrations define structure
2. **No Schema Drift**: ORM models match database exactly
3. **Reference Database**: When in doubt, consult `database/database.mmd`
4. **Foreign Keys**: All relationships enforced at database level

### Verification

```bash
# Generate SQLAlchemy models from database
sqlacodegen postgresql://user:pass@localhost/demeterai > models_generated.py

# Compare with app/models/*.py
diff models_generated.py app/models/
```

---

## ML Pipeline Integration

### CRITICAL: ML Pipeline is NOT a Separate Microservice

**Location**: `/app/services/ml_processing/`

**Why**:
- ✅ Reuses same services and repositories as API
- ✅ No code duplication
- ✅ Same transaction boundaries
- ✅ Easier testing and debugging

**Components**:
- `pipeline_coordinator.py` - Orchestrates full ML flow
- `localization_service.py` - GPS → storage_location lookup
- `segmentation_service.py` - YOLO v11 segmentation
- `detection_service.py` - YOLO v11 detection + SAHI
- `estimation_service.py` - Band-based + density estimation
- `image_processing_service.py` - Visualization generation

---

## Anti-Patterns (NEVER DO THIS)

### ❌ 1. Business Logic in Controllers

```python
# BAD
@router.post("/stock/manual")
async def create_stock(request, session: AsyncSession = Depends()):
    # Business logic in controller = WRONG
    if request.quantity <= 0:
        raise HTTPException(400, "Quantity must be positive")

    movement = StockMovement(**request.dict())
    session.add(movement)
    await session.commit()
```

### ❌ 2. Services Calling Other Repos Directly

```python
# BAD
class ServiceA:
    def __init__(self, repo_a, repo_b):  # repo_b = WRONG
        self.repo_a = repo_a
        self.repo_b = repo_b  # Should be service_b
```

### ❌ 3. Database Queries in Controllers

```python
# BAD
@router.get("/stock/{id}")
async def get_stock(id: int, session: AsyncSession = Depends()):
    # Direct query in controller = WRONG
    result = await session.execute(select(StockMovement).where(...))
```

### ❌ 4. Services Depending on FastAPI

```python
# BAD
from fastapi import HTTPException

class StockService:
    async def create_movement(self):
        if not valid:
            raise HTTPException(400, "Invalid")  # FastAPI in service = WRONG
```

### ❌ 5. Circular Dependencies

```python
# BAD
# service_a.py
from app.services.service_b import ServiceB

class ServiceA:
    def __init__(self, service_b: ServiceB):
        ...

# service_b.py
from app.services.service_a import ServiceA  # CIRCULAR

class ServiceB:
    def __init__(self, service_a: ServiceA):
        ...
```

---

## References

- **Engineering Plan**: ../../engineering_plan/03_architecture_overview.md
- **Backend Details**: ../../engineering_plan/backend/README.md
- **Past Decisions**: ../../context/past_chats_summary.md (lines 700-730)

---

**Document Owner**: Backend Team Lead
**Review Frequency**: Every sprint retrospective (adjust if violations found)
**Enforcement**: Code review checklist includes architecture verification
