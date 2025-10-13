# DemeterAI Testing Guide

## Overview

This directory contains all automated tests for DemeterAI v2.0 backend. Tests use pytest with async support, coverage reporting, and markers for selective execution.

## Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run specific test file
pytest tests/unit/test_sample.py

# Run tests matching pattern
pytest -k "test_health"
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (db_session, client, sample data)
├── core/                    # Core functionality tests
│   ├── test_logging.py      # Structured logging tests
│   └── test_exceptions.py   # Exception handling tests
├── db/                      # Database layer tests
│   └── test_session.py      # Session management tests
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_sample.py       # Sample unit tests
│   └── ...
└── integration/             # Integration tests (slower, real dependencies)
    ├── test_api_health.py   # Health endpoint tests
    └── ...
```

## Test Markers

Tests are automatically marked based on their location:

- `@pytest.mark.unit` - Unit tests (tests/unit/)
- `@pytest.mark.integration` - Integration tests (tests/integration/)
- `@pytest.mark.slow` - Slow tests (manually marked)

### Using Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all except slow tests (good for CI/CD fast feedback)
pytest -m "not slow"

# Combine markers (unit OR integration, but not slow)
pytest -m "(unit or integration) and not slow"
```

## Fixtures

### Database Fixtures

#### `db_session` (async)
Function-scoped database session with automatic rollback.

```python
@pytest.mark.unit
async def test_warehouse_creation(db_session):
    warehouse = Warehouse(code="WH-001", name="Test Warehouse")
    db_session.add(warehouse)
    await db_session.commit()
    assert warehouse.id is not None
```

#### `client` (async)
FastAPI test client with test database.

```python
@pytest.mark.integration
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
```

### Sample Data Fixtures

Factory fixtures for common test data:

- `sample_warehouse` - Warehouse test data
- `sample_storage_area` - Storage area test data
- `sample_product` - Product test data

```python
def test_with_sample_data(sample_warehouse):
    assert sample_warehouse["code"] == "WH-TEST"
    assert sample_warehouse["active"] is True
```

## Coverage

### Running Coverage

```bash
# Coverage with term output
pytest --cov=app

# Coverage with HTML report
pytest --cov=app --cov-report=html

# Open HTML report (Linux)
xdg-open htmlcov/index.html

# Coverage with missing lines highlighted
pytest --cov=app --cov-report=term-missing
```

### Coverage Requirements

- **Minimum**: 80% (enforced by --cov-fail-under=80)
- **Current**: 98.28%
- **Goal**: Keep above 90% for production code

### Coverage Tips

1. Focus on business logic coverage (services, repositories)
2. Don't over-test framework code (FastAPI routes, SQLAlchemy models)
3. Test error paths (exceptions, validation failures)
4. Use mocks for external services (S3, Redis, Celery)

## Test Database

### Current Setup (Before Docker)

- **Engine**: SQLite in-memory (aiosqlite)
- **Scope**: Function-scoped (fresh DB per test)
- **Isolation**: Automatic rollback after each test

### Future Setup (After F012 Docker)

- **Engine**: PostgreSQL test database
- **Scope**: Session-scoped (faster, shared DB)
- **Isolation**: Transaction rollback per test

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_stock_service.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.unit
async def test_stock_service_create(db_session):
    # Arrange
    service = StockService(db_session)
    stock_data = {"product_id": 1, "quantity": 100}

    # Act
    result = await service.create(stock_data)

    # Assert
    assert result.quantity == 100
    assert result.id is not None
```

### Integration Test Example

```python
# tests/integration/test_stock_api.py
import pytest

@pytest.mark.integration
async def test_create_stock_endpoint(client):
    # Arrange
    payload = {"product_id": 1, "quantity": 100}

    # Act
    response = await client.post("/api/v1/stock", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["quantity"] == 100
```

### Async Test Guidelines

1. **Always mark async tests**: `@pytest.mark.asyncio` (auto-applied by conftest)
2. **Use async fixtures**: `db_session`, `client`
3. **Await async calls**: `await client.get(...)`, `await service.create(...)`
4. **Mock async methods**: Use `AsyncMock()` from unittest.mock

## Continuous Integration

### CI/CD Test Command

```bash
# Fast feedback (skip slow tests)
pytest -m "not slow" --cov=app --cov-fail-under=80

# Full test suite
pytest --cov=app --cov-fail-under=80
```

### Pre-commit Checks

```bash
# Run before committing
pytest --cov=app --cov-fail-under=80
ruff check app/ tests/
mypy app/
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure package is installed in editable mode
pip install -e .
```

#### Async Warnings
```bash
# Already configured in pyproject.toml
# asyncio_mode = "auto"
```

#### Coverage Below 80%
```bash
# Check which files need tests
pytest --cov=app --cov-report=term-missing

# Focus on missing lines shown in output
```

#### Test Database Connection Errors
```bash
# Currently using SQLite in-memory (no setup needed)
# After F012: Docker will provide PostgreSQL test database
```

## Resources

- **pytest docs**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **httpx**: https://www.python-httpx.org/

## Questions?

For test setup questions, see:
- `tests/conftest.py` - Fixture implementations
- `pyproject.toml` - Pytest configuration
- Card F009 - Testing framework setup
