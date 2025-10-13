# Development Guide

**Version:** 1.0
**Last Updated:** 2025-10-08

---

## Overview

This guide covers development workflow, conventions, testing, and the 15-phase implementation plan for DemeterAI v2.0.

---

## Development Phases

**Current Status:** Phase 0 (Engineering Documentation) → Ready for Phase 1

### Phase 0: ✅ Engineering Documentation (COMPLETED)

- ✅ Git repository setup
- ✅ Directory structure designed
- ✅ Database ERD documented
- ✅ 6 workflow diagrams created
- ✅ Engineering plan partitioned and updated
- ✅ Manual initialization workflow added

### Phase 1-5: Backend Core (8-10 weeks)

**Phase 1:** SQLAlchemy Models + Repositories
- Create all 28 database models
- Implement base AsyncRepository pattern
- Write specialized repository methods
- Unit tests for all repositories

**Phase 2:** Base Services
- ProductService, PackagingService
- StorageLocationService, WarehouseService
- Configuration services
- Unit tests with mocked repositories

**Phase 3:** Complex Services
- StockMovementService (with manual init support)
- StockBatchService
- PhotoSessionService
- Integration tests

**Phase 4:** ML Pipeline
- SegmentationService (YOLO v11, CPU-first)
- DetectionService (SAHI integration)
- EstimationService (band-based algorithm)
- PipelineCoordinator (Celery chord pattern)
- Model singleton pattern

**Phase 5:** Pydantic Schemas
- Request/response schemas for all endpoints
- Validation rules
- Schema documentation

### Phase 6-10: API Layer (6-8 weeks)

**Phase 6:** Location Controllers
- GET /warehouses, /areas, /locations
- Pagination, filtering

**Phase 7:** Configuration Controllers
- POST/GET /config/storage-location
- Product/packaging CRUD

**Phase 8:** Stock Controllers + Celery
- POST /stock/photo (async with Celery)
- POST /stock/manual (sync)
- GET /stock/tasks/status (polling)
- Celery worker setup

**Phase 9:** Analytics Controllers
- POST /report
- GET /comparison
- Data export (Excel/CSV)

**Phase 10:** Authentication
- JWT token generation
- User management
- Role-based access control

### Phase 11-15: Infrastructure (4-6 weeks)

**Phase 11:** Exceptions + Logging
- Centralized exception handling
- Structured logging (JSON format)
- Error tracking integration

**Phase 12:** Configuration Management
- YAML config loaders
- Environment variable management
- Feature flags

**Phase 13:** Docker + Deployment
- Dockerfile (multi-stage build)
- docker-compose.yml
- CI/CD pipeline (GitHub Actions)

**Phase 14:** Documentation
- README.md
- API documentation (Swagger)
- Deployment guide

**Phase 15:** Optimization + Refactoring
- Performance profiling
- Query optimization
- Code cleanup
- Tech debt resolution

**Total Estimated Time:** 18-24 weeks (4.5-6 months)

---

## Coding Conventions

### Python Style

**Linter/Formatter:** Ruff 0.7.0

Ruff is a fast, all-in-one linter and formatter (10-100x faster than Black+Flake8+isort).

**Quick Commands:**
```bash
# Format code
ruff format .

# Check and auto-fix issues
ruff check . --fix

# Run before commit
ruff format . && ruff check . --fix
```

**Configuration:** See `pyproject.toml` under `[tool.ruff]`
- Line length: 100 characters
- Target version: Python 3.12
- Enabled rules: E, F, I, N, W, UP, B, C4, SIM

**Detailed Guide:** See [../../RUFF_USAGE.md](../../RUFF_USAGE.md) for complete documentation

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| **Variables** | snake_case | `storage_location_id` |
| **Functions** | snake_case | `async def get_stock_movements()` |
| **Classes** | PascalCase | `StockMovementService` |
| **Constants** | UPPER_SNAKE_CASE | `MAX_RETRIES = 3` |
| **Private** | _leading_underscore | `_internal_method()` |
| **Database Models** | PascalCase | `StockMovement` |
| **Pydantic Schemas** | PascalCase + suffix | `StockMovementRequest` |

### File Organization

```
app/
├── models/
│   ├── __init__.py
│   ├── stock_movement.py
│   └── stock_batch.py
│
├── repositories/
│   ├── __init__.py
│   ├── base.py
│   ├── stock_movement_repository.py
│   └── stock_batch_repository.py
│
├── services/
│   ├── __init__.py
│   ├── stock_movement_service.py
│   ├── stock_batch_service.py
│   └── ml_processing/
│       ├── pipeline_coordinator.py
│       ├── segmentation_service.py
│       └── detection_service.py
│
├── controllers/
│   ├── __init__.py
│   ├── stock_controller.py
│   └── location_controller.py
│
├── schemas/
│   ├── __init__.py
│   ├── stock_schema.py
│   └── location_schema.py
│
└── main.py
```

---

## Testing Strategy

### Test Coverage Target

**Minimum:** 80% coverage
**Ideal:** 90%+ coverage

### Test Types

**Unit Tests:** 70% of tests
- Test individual functions/methods
- Mock dependencies
- Fast execution (<1s per test)

**Integration Tests:** 25% of tests
- Test service layer with real database
- Use test database (Docker container)
- Medium execution (1-5s per test)

**End-to-End Tests:** 5% of tests
- Test full workflows (API → DB)
- Simulate real user scenarios
- Slow execution (5-30s per test)

### Test Structure

```python
# tests/unit/services/test_stock_movement_service.py
import pytest
from unittest.mock import MagicMock
from app.services.stock_movement_service import StockMovementService

@pytest.mark.asyncio
async def test_create_manual_init_success(mocker):
    # Arrange
    mock_repo = mocker.MagicMock()
    mock_config_service = mocker.MagicMock()
    mock_config_service.get_by_location.return_value = {
        "product_id": 45,
        "packaging_catalog_id": 12
    }

    service = StockMovementService(mock_repo, mock_config_service, ...)

    request = ManualStockInitRequest(
        storage_location_id=123,
        product_id=45,
        packaging_catalog_id=12,
        quantity=1500
    )

    # Act
    result = await service.create_manual_initialization(request)

    # Assert
    assert result.quantity == 1500
    mock_repo.create.assert_called_once()
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/unit/services/test_stock_movement_service.py

# Specific test
pytest tests/unit/services/test_stock_movement_service.py::test_create_manual_init_success

# Watch mode (re-run on file changes)
pytest-watch
```

---

## Git Workflow

### Branch Strategy

**Main branches:**
- `main` - Production-ready code
- `develop` - Integration branch

**Feature branches:**
- `feature/manual-stock-init`
- `feature/celery-gpu-workers`
- `bugfix/product-mismatch-error`

### Commit Message Format

```
docs: <description>
feat: <description>
fix: <description>
refactor: <description>
test: <description>
chore: <description>
```

**Examples:**
- ✅ `docs: add manual stock initialization workflow`
- ✅ `feat: implement StockMovementService.create_manual_init`
- ✅ `fix: validate product_id matches config`
- ✅ `test: add unit tests for manual init validation`

---

## Code Review Checklist

Before submitting PR:

- [ ] All tests pass (`pytest`)
- [ ] Code coverage ≥ 80%
- [ ] Linter passes (`ruff check .`)
- [ ] Formatter applied (`ruff format .`)
- [ ] No print() statements (use logger)
- [ ] Docstrings added for public functions
- [ ] Type hints added for function signatures
- [ ] No TODOs or FIXMEs (create issues instead)
- [ ] Database migrations tested (if applicable)
- [ ] Mermaid diagrams validated (if applicable)

---

## Performance Guidelines

### Database Queries

**DO:**
- ✅ Use `selectinload()` for one-to-many
- ✅ Use `joinedload()` for many-to-one
- ✅ Add indexes for frequent WHERE clauses
- ✅ Use `asyncpg COPY` for bulk inserts (1000+ rows)

**DON'T:**
- ❌ Lazy loading in async code (N+1 queries)
- ❌ SELECT * (fetch only needed columns)
- ❌ Missing indexes on foreign keys

### Async/Await

**DO:**
- ✅ Use `async def` for I/O-bound operations
- ✅ Use `await` for database queries, S3 uploads
- ✅ Use `asyncio.gather()` for parallel operations

**DON'T:**
- ❌ Use `async def` without any `await` (blocking event loop)
- ❌ Call sync DB methods in async routes
- ❌ Use `time.sleep()` (use `await asyncio.sleep()`)

---

## Environment Setup

### Prerequisites

- Python 3.12
- Docker + Docker Compose
- PostgreSQL 15+ with PostGIS 3.3+
- Redis 7+

### Initial Setup

```bash
# Clone repository
git clone https://github.com/your-org/demeterai-backend.git
cd demeterai-backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start database + Redis
docker-compose up -d db redis

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app worker --pool=prefork --concurrency=4 --queues=cpu_queue
```

---

## Next Steps

- **Backend Implementation:** See [../backend/README.md](../backend/README.md)
- **API Specification:** See [../api/README.md](../api/README.md)
- **Database Schema:** See [../database/README.md](../database/README.md)

---

**Document Owner:** DemeterAI Engineering Team
**Last Reviewed:** 2025-10-08
