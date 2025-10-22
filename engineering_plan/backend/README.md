# Backend Architecture

**Version:** 1.0
**Last Updated:** 2025-10-08

---

## Overview

The DemeterAI backend follows **Clean Architecture** principles with three distinct layers:

1. **Controllers** (Presentation Layer) - FastAPI routes, HTTP concerns
2. **Services** (Application Layer) - Business logic, orchestration
3. **Repositories** (Infrastructure Layer) - Database access

### Key Principle

**Dependency Rule:** Dependencies point inward (Controllers → Services → Repositories → Database)

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  CONTROLLERS (FastAPI Routes)                                   │
│  - HTTP status codes                                            │
│  - Pydantic validation                                          │
│  - Call services ONLY                                           │
│  - NO business logic                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ Depends on
┌────────────────────────▼────────────────────────────────────────┐
│  SERVICES (Business Logic)                                      │
│  - Orchestrate operations                                       │
│  - Call other services (NOT repos directly)                     │
│  - Transform schemas ↔ models                                   │
│  - Enforce business rules                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ Depends on
┌────────────────────────▼────────────────────────────────────────┐
│  REPOSITORIES (Data Access)                                     │
│  - CRUD operations                                              │
│  - SQLAlchemy queries                                           │
│  - NO business logic                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ Depends on
┌────────────────────────▼────────────────────────────────────────┐
│  DATABASE (PostgreSQL + PostGIS)                                │
│  - Single source of truth                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Components

| Component            | Purpose                | Details                                      |
|----------------------|------------------------|----------------------------------------------|
| **Repository Layer** | Database access        | [repository_layer.md](./repository_layer.md) |
| **Service Layer**    | Business logic         | [service_layer.md](./service_layer.md)       |
| **Controller Layer** | HTTP routes            | [controller_layer.md](./controller_layer.md) |
| **ML Pipeline**      | YOLO + SAHI processing | [ml_pipeline.md](./ml_pipeline.md)           |

---

## ML Pipeline Integration (CRITICAL)

**The ML pipeline is NOT a separate microservice.** It's integrated directly into the backend:

**Location:** `/app/services/ml_processing/`

**Why:**

- ✅ Reuses same services and repositories as API
- ✅ No code duplication
- ✅ Same transaction boundaries
- ✅ Easier testing and debugging

**Components:**

- `pipeline_coordinator.py` - Orchestrates full ML flow
- `localization_service.py` - GPS → storage_location lookup
- `segmentation_service.py` - YOLO v11 segmentation
- `detection_service.py` - YOLO v11 detection + SAHI
- `estimation_service.py` - Band-based + density estimation
- `image_processing_service.py` - Visualization generation

**See:** [ml_pipeline.md](./ml_pipeline.md) for CPU-first implementation details

---

## Communication Rules

### CRITICAL: Inter-Service Communication

```
✅ CORRECT:
Controller → Service A → Service B → Repository B
                      ↓
                  Repository A

❌ FORBIDDEN:
Service A → Repository B (must call Service B instead)
```

**Why:** Service B encapsulates Repository B's logic. Direct repo access violates encapsulation.

### Example: Manual Stock Initialization

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
        # Call other services, not their repositories
        config = await self.config_service.get_by_location(...)
        batch = await self.batch_service.create_from_movement(...)
```

---

## Dependency Injection

### FastAPI `Depends()`

**Purpose:** Loose coupling, easy testing

**Example:**

```python
from fastapi import Depends
from app.db.session import get_db_session

async def get_stock_service(
    session: AsyncSession = Depends(get_db_session)
) -> StockMovementService:
    repo = StockMovementRepository(StockMovement, session)
    config_service = StorageLocationConfigService(...)
    batch_service = StockBatchService(...)
    return StockMovementService(repo, config_service, batch_service)

@router.post("/stock/manual")
async def manual_init(
    request: ManualStockInitRequest,
    service: StockMovementService = Depends(get_stock_service)
):
    return await service.create_manual_initialization(request)
```

**Benefits:**

- ✅ Services auto-injected
- ✅ Easy to mock in tests
- ✅ No global state

---

## Error Handling

### Centralized Exceptions

**Location:** `/app/exceptions/`

**Structure:**

```python
class AppBaseException(Exception):
    def __init__(self, technical_message: str, user_message: str, code: int):
        self.technical_message = technical_message
        self.user_message = user_message
        self.code = code

class ProductMismatchException(AppBaseException):
    def __init__(self, expected: int, actual: int):
        super().__init__(
            technical_message=f"Product {actual} != expected {expected}",
            user_message="Product does not match configuration",
            code=400
        )
```

**Global Handler:**

```python
@app.exception_handler(AppBaseException)
async def handler(request, exc: AppBaseException):
    return JSONResponse(
        status_code=exc.code,
        content={"error": exc.user_message}
    )
```

---

## Testing Strategy

### Unit Tests

**Repositories:**

```python
@pytest.mark.asyncio
async def test_stock_movement_repo_create(db_session):
    repo = StockMovementRepository(StockMovement, db_session)
    movement = await repo.create({
        "movement_type": "manual_init",
        "quantity": 100
    })
    assert movement.id is not None
```

**Services (with mocks):**

```python
@pytest.mark.asyncio
async def test_stock_service_manual_init(mocker):
    mock_repo = mocker.MagicMock()
    mock_config_service = mocker.MagicMock()

    service = StockMovementService(mock_repo, mock_config_service, ...)

    result = await service.create_manual_initialization(request)

    mock_config_service.get_by_location.assert_called_once()
```

---

## Next Steps

- **Repository Layer:** See [repository_layer.md](./repository_layer.md)
- **Service Layer:** See [service_layer.md](./service_layer.md)
- **Controller Layer:** See [controller_layer.md](./controller_layer.md)
- **ML Pipeline:** See [ml_pipeline.md](./ml_pipeline.md)

---

**Document Owner:** DemeterAI Engineering Team
**Last Reviewed:** 2025-10-08
