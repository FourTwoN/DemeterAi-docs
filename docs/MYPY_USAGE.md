# Mypy Type Checking Guide

## Overview

DemeterAI v2.0 uses [mypy](https://mypy.readthedocs.io/) for static type checking to catch type
errors before runtime. Mypy is configured with **strict mode** enabled, enforcing type hints on all
functions in the application code.

## Why Type Checking?

- **Catch bugs early**: Type errors are detected at development time, not in production
- **Better IDE support**: Enhanced autocomplete, refactoring, and navigation
- **Documentation**: Type hints serve as inline documentation
- **Prevent common errors**: None checks, attribute errors, incompatible types

## Configuration

Mypy configuration is in `pyproject.toml` under the `[tool.mypy]` section:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["sqlalchemy.ext.mypy.plugin"]
```

### Key Settings

- **strict = true**: Enables all strict type checking rules
- **disallow_untyped_defs = true**: All functions must have type hints
- **SQLAlchemy plugin**: Understands ORM models and relationships
- **Incremental caching**: Faster re-checks (cache in `.mypy_cache/`)

### Module Exclusions

- **alembic.*** : Auto-generated migration code (ignore_errors=true)
- **tests.*** : Tests have relaxed rules (no requirement for type hints)

## Running Mypy

### Check Entire Application

```bash
# Check all application code
mypy app/

# Check tests (with relaxed rules)
mypy tests/

# Check everything
mypy app/ tests/
```

### Check Single File

```bash
# Check specific file
mypy app/services/stock_movement_service.py

# Check with extra verbosity
mypy app/services/stock_movement_service.py --show-error-codes
```

### Pre-commit Integration

Mypy runs automatically on every commit via pre-commit hooks:

```bash
# Install pre-commit hooks (one-time setup)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run only mypy
pre-commit run mypy --all-files
```

**Commits will be blocked if type errors are found.**

## Type Hint Examples

### Function Signatures

```python
from typing import Optional

# ✅ CORRECT: Full type hints
def create_warehouse(code: str, name: str) -> Warehouse:
    return Warehouse(code=code, name=name)

# ✅ CORRECT: Optional parameters
def get_warehouse(warehouse_id: int) -> Optional[Warehouse]:
    result = session.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    return result.scalar_one_or_none()

# ❌ WRONG: Missing type hints
def create_warehouse(code, name):
    return Warehouse(code=code, name=name)
```

### Async Functions

```python
from sqlalchemy.ext.asyncio import AsyncSession

# ✅ CORRECT: Async function with type hints
async def get_all_warehouses(session: AsyncSession) -> list[Warehouse]:
    result = await session.execute(select(Warehouse))
    return list(result.scalars().all())
```

### Service Classes

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

class WarehouseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, warehouse_id: int) -> Optional[Warehouse]:
        """Get warehouse by ID."""
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Warehouse]:
        """Get all warehouses."""
        result = await self.session.execute(select(Warehouse))
        return list(result.scalars().all())
```

### Exception Handlers

```python
from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse

async def exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    correlation_id = get_correlation_id()

    # Use dict[str, Any] for mixed-type dictionaries
    response_data: dict[str, Any] = {
        "error": exc.user_message,
        "code": exc.__class__.__name__,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    return JSONResponse(
        status_code=exc.code,
        content=response_data,
    )
```

## Common Type Errors and Solutions

### Error: "Returning Any from function declared to return X"

**Problem**: Function returns a value that mypy can't infer the type of.

```python
# ❌ Problem
def get_logger(name: str) -> BoundLogger:
    return structlog.get_logger(name)  # Returns Any

# ✅ Solution
def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
```

### Error: "Incompatible types in assignment"

**Problem**: Trying to assign a value of one type to a variable of another type.

```python
# ❌ Problem
response_data = {"error": "message"}  # Inferred as dict[str, str]
response_data["extra"] = {"key": 123}  # Can't assign dict to str value

# ✅ Solution
response_data: dict[str, Any] = {"error": "message"}
response_data["extra"] = {"key": 123}
```

### Error: "Function is missing a type annotation"

**Problem**: Function missing return type or parameter types.

```python
# ❌ Problem
async def dispatch(self, request: Request, call_next):
    return await call_next(request)

# ✅ Solution
async def dispatch(self, request: Request, call_next: Any) -> Any:
    return await call_next(request)
```

### Error: "Incompatible return value type"

**Problem**: Function returns a type different from what's declared.

```python
# ❌ Problem
def foo(x: int) -> str:
    return x  # Returns int, not str

# ✅ Solution
def foo(x: int) -> str:
    return str(x)
```

## Type Stubs for Third-Party Libraries

Some libraries don't include type hints. Install type stubs:

```bash
pip install types-requests  # For requests library
pip install types-redis     # For redis library
pip install types-python-dateutil  # For dateutil
```

Already installed in `pyproject.toml`:

- types-requests
- types-redis
- types-python-dateutil

## SQLAlchemy Type Checking

The SQLAlchemy plugin understands ORM relationships:

```python
from sqlalchemy.orm import Mapped, mapped_column

class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))

# Mypy understands these types automatically
warehouse = Warehouse(code="W01", name="Main Warehouse")
warehouse.code  # Type: str (mypy knows this!)
```

## Ignoring Type Errors (Use Sparingly)

Sometimes you need to ignore type errors (e.g., third-party libraries without stubs):

```python
# Ignore error on specific line
result = untyped_function()  # type: ignore[no-untyped-call]

# Ignore all errors on line (avoid if possible)
result = untyped_function()  # type: ignore
```

**Note**: Pre-commit hooks check for blanket `# type: ignore` comments and will warn you.

## Performance

- **Full check**: ~5 seconds for entire codebase
- **Incremental check**: ~1 second for single file change
- **Cache warmup**: ~10 seconds first run (creates `.mypy_cache/`)

## CI/CD Integration

Mypy will run in CI/CD pipeline (Sprint 05):

```yaml
# .gitlab-ci.yml (future)
type-check:
  stage: test
  script:
    - mypy app/ --strict
```

## Best Practices

1. **Add type hints to all functions**: Required by strict mode
2. **Use `Optional[T]` for nullable values**: Be explicit about None
3. **Use `Any` sparingly**: Only when truly necessary
4. **Use `dict[str, Any]` for mixed dicts**: When values have different types
5. **Run mypy before committing**: Pre-commit will do this automatically
6. **Fix type errors, don't ignore them**: Ignoring defeats the purpose

## Resources

- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Python Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [SQLAlchemy Mypy Plugin](https://docs.sqlalchemy.org/en/20/orm/extensions/mypy.html)
- [FastAPI Type Hints](https://fastapi.tiangolo.com/python-types/)

## Troubleshooting

### Mypy not finding modules

```bash
# Make sure you're in the project root
cd /path/to/DemeterDocs

# Activate virtual environment
source venv/bin/activate

# Run mypy
mypy app/
```

### Cache issues

```bash
# Clear mypy cache
rm -rf .mypy_cache

# Run mypy again
mypy app/
```

### Pre-commit hook not running

```bash
# Reinstall pre-commit hooks
pre-commit clean
pre-commit install

# Test
pre-commit run --all-files
```

---

**Last Updated**: 2025-10-13
**Mypy Version**: 1.13.0
**Python Version**: 3.12
