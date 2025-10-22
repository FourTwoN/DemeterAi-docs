# Architecture Overview - DemeterAI v2.0

**Document Version:** 1.0
**Last Updated:** 2025-10-08

---

## Table of Contents

1. [Clean Architecture Principles](#clean-architecture-principles)
2. [System Layers](#system-layers)
3. [Data Flow](#data-flow)
4. [Design Patterns](#design-patterns)
5. [Communication Rules](#communication-rules)
6. [Error Handling Strategy](#error-handling-strategy)

---

## Clean Architecture Principles

DemeterAI follows **Clean Architecture** (aka Hexagonal Architecture, Ports & Adapters):

### Core Tenets

1. **Dependency Rule:** Dependencies point inward (Domain ← Application ← Infrastructure)
2. **Database Independence:** Business logic doesn't know about PostgreSQL/SQLAlchemy
3. **UI Independence:** Business logic doesn't know about FastAPI/HTTP
4. **Framework Independence:** Core logic portable to other frameworks
5. **Testability:** Business logic testable without DB/API/External services

### Layer Responsibilities

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
│  │  PostgreSQL + PostGIS                                   │   │
│  │  - Single source of truth                               │   │
│  │  - Schema defined by migrations (Alembic)               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Layers

### 1. Controllers (Presentation Layer)

**Location:** `/app/controllers/`

**Responsibility:** HTTP concerns ONLY

**What Controllers Do:**

- ✅ Define FastAPI routes (`@router.get`, `@router.post`)
- ✅ Validate input with Pydantic schemas
- ✅ Call service layer methods
- ✅ Return HTTP responses with proper status codes
- ✅ Handle request/response serialization

**What Controllers DON'T Do:**

- ❌ Business logic
- ❌ Database queries
- ❌ Call repositories directly
- ❌ Complex data transformations

**Example:**

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
    """
    Controller: HTTP concerns only.
    Business logic in StockMovementService.
    """
    result = await service.create_manual_initialization(request)
    return result
```

### 2. Services (Application Layer)

**Location:** `/app/services/`

**Responsibility:** Business logic and orchestration

**What Services Do:**

- ✅ Implement business rules
- ✅ Coordinate multi-step operations
- ✅ Call other services (inter-service communication)
- ✅ Transform Pydantic schemas ↔ SQLAlchemy models
- ✅ Enforce validations (config checks, business constraints)
- ✅ Handle complex calculations

**What Services DON'T Do:**

- ❌ Know about HTTP (no FastAPI imports)
- ❌ Call repositories from other services directly
- ❌ Handle database connections (use dependency injection)

**Communication Rule:**

```
Controller → Service A → Service B → Repository B
                      ↓
                  Repository A

❌ NOT ALLOWED: Service A → Repository B (must call Service B)
```

**Example:**

```python
class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_service: StorageLocationConfigService,  # ← Call other services
        batch_service: StockBatchService
    ):
        self.repo = repo
        self.config_service = config_service
        self.batch_service = batch_service

    async def create_manual_initialization(
        self,
        request: ManualStockInitRequest
    ) -> StockMovementResponse:
        # 1. Business validation: Check config exists and matches
        config = await self.config_service.get_by_location(request.location_id)
        if not config:
            raise ConfigNotFoundException(request.location_id)

        if config.product_id != request.product_id:
            raise ProductMismatchException(
                expected=config.product_id,
                actual=request.product_id
            )

        # 2. Create stock movement
        movement = await self.repo.create({
            "movement_type": "manual_init",
            "quantity": request.quantity,
            "source_type": "manual"
        })

        # 3. Create stock batch (via batch_service, not direct repo call)
        batch = await self.batch_service.create_from_movement(movement)

        return StockMovementResponse.from_model(movement)
```

### 3. Repositories (Infrastructure Layer)

**Location:** `/app/repositories/`

**Responsibility:** Data access ONLY

**What Repositories Do:**

- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ SQLAlchemy queries
- ✅ Database transaction management
- ✅ Eager/lazy loading optimization

**What Repositories DON'T Do:**

- ❌ Business logic
- ❌ Call other repositories
- ❌ Know about Pydantic schemas (work with SQLAlchemy models only)

**Base Repository Pattern:**

```python
from typing import Generic, TypeVar, Type, List, Optional
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

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, id: int, obj_in: dict) -> Optional[ModelType]:
        db_obj = await self.get(id)
        if not db_obj:
            return None
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: int) -> bool:
        db_obj = await self.get(id)
        if not db_obj:
            return False
        await self.session.delete(db_obj)
        await self.session.flush()
        return True
```

### 4. ML Pipeline (Special Subsystem)

**Location:** `/app/services/ml_processing/`

**Status:** Integrated with API (NOT a separate microservice)

**Components:**

- `pipeline_coordinator.py`: Orchestrates full ML pipeline
- `localization_service.py`: GPS → storage_location lookup
- `segmentation_service.py`: YOLO v11 segmentation
- `detection_service.py`: YOLO v11 detection + SAHI
- `estimation_service.py`: Band-based + density-based estimation
- `image_processing_service.py`: Visualization generation

**Key Principle:** ML pipeline uses the same services and repositories as REST API (code reuse).

---

## Data Flow

### Photo Initialization Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CLIENT: Uploads photo via POST /api/stock/photo             │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. CONTROLLER: Validates multipart form, calls service         │
│    → stock_controller.upload_photo()                            │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. SERVICE: Orchestrates upload + ML dispatch                  │
│    → photo_service.create_session()                             │
│    → s3_service.upload_original()                               │
│    → celery_task.ml_parent_task.delay(photo_id)                │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. CELERY WORKER (GPU): ML processing                          │
│    → localization_service.find_location(gps)                    │
│    → segmentation_service.segment(image)                        │
│    → Spawns child tasks (SAHI detection, estimation)           │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. CALLBACK: Aggregate results                                 │
│    → stock_movement_service.create_from_detections()            │
│    → stock_batch_service.group_by_classification()              │
│    → image_service.create_visualization()                       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. REPOSITORY: Persist to PostgreSQL                           │
│    → stock_movement_repo.create()                               │
│    → stock_batch_repo.create()                                  │
│    → detection_repo.bulk_insert()                               │
│    → estimation_repo.bulk_insert()                              │
└─────────────────────────────────────────────────────────────────┘
```

### Manual Initialization Flow (NEW)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CLIENT: Posts manual count via POST /api/stock/manual       │
│    { location_id, product_id, packaging_id, quantity }         │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. CONTROLLER: Validates request, calls service                │
│    → stock_controller.initialize_manual()                       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. SERVICE: Business validation                                │
│    → config_service.get_by_location(location_id)                │
│    → IF config.product_id != request.product_id:               │
│         RAISE ProductMismatchException ← CRITICAL VALIDATION    │
│    → ELSE: Continue                                             │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. SERVICE: Create stock movement                              │
│    → stock_movement_service.create({                            │
│         movement_type: "manual_init",                           │
│         quantity: request.quantity,                             │
│         source_type: "manual"                                   │
│      })                                                         │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. SERVICE: Create stock batch                                 │
│    → batch_service.create_from_movement(movement)               │
│    → Batch includes: product, size, packaging, quantity        │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. REPOSITORY: Persist to PostgreSQL                           │
│    → stock_movement_repo.create()                               │
│    → stock_batch_repo.create()                                  │
│    → NO detections, estimations, or photo_session              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Patterns

### 1. Repository Pattern

**Purpose:** Abstract database access

**Benefits:**

- ✅ Testability (mock repositories in tests)
- ✅ Flexibility (swap ORM/raw SQL without changing services)
- ✅ Reusability (repositories shared across services)

### 2. Dependency Injection

**Purpose:** Loose coupling, easy testing

**Implementation:** FastAPI's `Depends()`

**Example:**

```python
from fastapi import Depends
from app.db.session import get_db_session

async def get_stock_service(
    session: AsyncSession = Depends(get_db_session)
) -> StockMovementService:
    repo = StockMovementRepository(StockMovement, session)
    return StockMovementService(repo)

@router.post("/stock/manual")
async def manual_init(
    request: ManualStockInitRequest,
    service: StockMovementService = Depends(get_stock_service)
):
    return await service.create_manual_initialization(request)
```

### 3. Unit of Work (Transaction Management)

**Purpose:** Ensure all-or-nothing transactions

**Implementation:** SQLAlchemy session with commit/rollback

**Example:**

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

**Purpose:** Load YOLO models once per worker (not per task)

**Critical for GPU:** Prevents 2-3s model load overhead per photo

**Example:**

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

**Purpose:** Prevent cascading failures

**Implementation:** pybreaker

**Example:**

```python
s3_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)

@s3_breaker
def upload_to_s3(file, bucket, key):
    return s3_client.upload_file(file, bucket, key)
```

---

## Communication Rules

### CRITICAL Rule: Service-to-Service Communication

```
✅ CORRECT:
Controller → Service A → Service B → Repository B
                      ↓
                  Repository A

❌ INCORRECT:
Controller → Service A → Repository B (FORBIDDEN)
```

**Why:** Violates encapsulation. Service B owns Repository B's logic.

### Example: Manual Initialization

```python
# ✅ CORRECT
class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_service: StorageLocationConfigService,  # ← Service
        batch_service: StockBatchService                # ← Service
    ):
        ...

    async def create_manual_init(self, request):
        config = await self.config_service.get_by_location(...)  # ← Service call
        batch = await self.batch_service.create_from_movement(...)  # ← Service call
        ...

# ❌ INCORRECT
class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_repo: StorageLocationConfigRepository,  # ❌ Direct repo access
        batch_repo: StockBatchRepository                # ❌ Direct repo access
    ):
        ...
```

---

## Error Handling Strategy

### Centralized Exceptions

**Location:** `/app/exceptions/`

**Structure:**

```python
class AppBaseException(Exception):
    def __init__(self, technical_message: str, user_message: str, code: int = 500):
        self.technical_message = technical_message
        self.user_message = user_message
        self.code = code

class ProductMismatchException(AppBaseException):
    def __init__(self, expected: int, actual: int):
        super().__init__(
            technical_message=f"Product mismatch: expected {expected}, got {actual}",
            user_message="The product you entered does not match the configured product for this location",
            code=400
        )
```

### Global Exception Handler

```python
@app.exception_handler(AppBaseException)
async def app_exception_handler(request, exc: AppBaseException):
    return JSONResponse(
        status_code=exc.code,
        content={
            "error": exc.user_message,
            "detail": exc.technical_message if DEBUG else None
        }
    )
```

---

## Next Steps

- **Deep Dive:** [Database Architecture](./database/README.md)
- **Understand Workflows:** [Workflows Overview](./workflows/README.md)
- **Backend Implementation:** [Backend Layer Details](./backend/README.md)

---

**Document Owner:** DemeterAI Engineering Team
**Last Reviewed:** 2025-10-08
