# Coding Conventions - DemeterAI v2.0
## Naming, Formatting, and Standards

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**⚠️ CRITICAL**: Enforced by Ruff linter + pre-commit hooks. Non-compliance = failed CI/CD.

---

## Python Style Guide

### Base Standard

**PEP 8** + **PEP 257** (Docstrings) + **PEP 484** (Type Hints)

**Enforced by**: Ruff 0.7.0 (linter + formatter)

**Configuration**: `.ruff.toml` (see `04_templates/config-templates/`)

---

## Naming Conventions

### Variables & Functions

**Rule**: `snake_case` (lowercase with underscores)

```python
# ✅ CORRECT
storage_location_id = 123
total_plants_detected = 1500

async def get_stock_movements(session_id: int):
    pass

# ❌ INCORRECT
storageLocationId = 123  # camelCase = WRONG
TotalPlantsDetected = 1500  # PascalCase = WRONG

async def GetStockMovements(session_id: int):  # PascalCase = WRONG
    pass
```

### Classes

**Rule**: `PascalCase` (capitalize first letter of each word)

```python
# ✅ CORRECT
class StockMovementService:
    pass

class PhotoProcessingSession:
    pass

# ❌ INCORRECT
class stock_movement_service:  # snake_case = WRONG
    pass

class photoProcessingSession:  # camelCase = WRONG
    pass
```

### Constants

**Rule**: `UPPER_SNAKE_CASE` (all uppercase with underscores)

```python
# ✅ CORRECT
MAX_RETRIES = 3
DEFAULT_CONFIDENCE_THRESHOLD = 0.25
DATABASE_URL = "postgresql://..."

# ❌ INCORRECT
maxRetries = 3  # camelCase = WRONG
default_confidence_threshold = 0.25  # snake_case = WRONG
```

### Private Members

**Rule**: `_leading_underscore` (prefix with single underscore)

```python
# ✅ CORRECT
class StockService:
    def __init__(self):
        self._repo = None  # Private attribute

    def _internal_method(self):  # Private method
        pass

# ❌ INCORRECT
class StockService:
    def __init__(self):
        self.__repo = None  # Double underscore = name mangling (only for avoiding conflicts)
```

### Database Models

**Rule**: `PascalCase` for class, `snake_case` for table name

```python
# ✅ CORRECT
class StockMovement(Base):
    __tablename__ = "stock_movements"  # snake_case table name

    movement_id = Column(UUID, primary_key=True)

# ❌ INCORRECT
class stock_movement(Base):  # snake_case class = WRONG
    __tablename__ = "StockMovements"  # PascalCase table = WRONG
```

### Pydantic Schemas

**Rule**: `PascalCase` + descriptive suffix

**Suffixes**: `Request`, `Response`, `Create`, `Update`, `Base`

```python
# ✅ CORRECT
class StockMovementRequest(BaseModel):
    quantity: int

class StockMovementResponse(BaseModel):
    movement_id: UUID

class StockMovementCreate(BaseModel):
    pass

# ❌ INCORRECT
class stockMovementRequest(BaseModel):  # camelCase = WRONG
    pass

class StockMovement(BaseModel):  # No suffix = confusing with model
    pass
```

---

## File & Directory Naming

### Python Files

**Rule**: `snake_case.py`

```
# ✅ CORRECT
stock_movement_service.py
photo_processing_session.py
ml_pipeline_coordinator.py

# ❌ INCORRECT
StockMovementService.py  # PascalCase = WRONG
stock-movement-service.py  # kebab-case = WRONG
```

### Directories

**Rule**: `snake_case/` (no plurals unless collection)

```
# ✅ CORRECT
app/services/
app/repositories/
app/models/
app/services/ml_processing/  # Sub-module

# ❌ INCORRECT
app/Services/  # PascalCase = WRONG
app/service/  # No plural = inconsistent
```

### Test Files

**Rule**: `test_<module_name>.py`

```
# ✅ CORRECT
tests/unit/services/test_stock_movement_service.py
tests/integration/test_ml_pipeline.py

# ❌ INCORRECT
tests/stock_movement_service_test.py  # Wrong suffix position
tests/test_stock_movement_service_unit.py  # Unit in filename = redundant (use directory)
```

---

## Card & Epic IDs

### Card ID Format

**Rule**: `<AREA><NUMBER>-<short-name>`

**Pattern**: `[A-Z]{1,4}[0-9]{3}-[a-z-]+`

```
# ✅ CORRECT
F001-project-setup
DB015-stock-movements-model
ML003-sahi-detection
S012-stock-movement-service
C005-stock-controller

# ❌ INCORRECT
F1-project-setup  # Need 3 digits (F001)
db015-stock-movements  # Lowercase area (DB015)
ML-003-sahi  # Dash before number
S12-StockMovementService  # PascalCase in name
```

**Area Codes**:
- `F` = Foundation
- `DB` = Database
- `R` = Repository
- `S` = Service
- `ML` = ML Pipeline
- `C` = Controller
- `CEL` = Celery
- `SCH` = Schema
- `AUTH` = Authentication
- `OBS` = Observability
- `DEP` = Deployment
- `TEST` = Testing

### Epic ID Format

**Rule**: `epic-<number>-<short-name>.md`

```
# ✅ CORRECT
epic-001-foundation.md
epic-007-ml-pipeline.md

# ❌ INCORRECT
Epic-001-foundation.md  # Capitalized
epic-1-foundation.md  # Need 3 digits
epic_001_foundation.md  # Underscores
```

---

## Code Formatting

### Line Length

**Rule**: Max 100 characters (enforced by Ruff)

```python
# ✅ CORRECT (under 100 chars)
async def get_stock_movements_by_location(
    location_id: int,
    start_date: datetime,
    end_date: datetime
) -> List[StockMovement]:
    pass

# ❌ INCORRECT (over 100 chars)
async def get_stock_movements_by_location(location_id: int, start_date: datetime, end_date: datetime) -> List[StockMovement]:
    pass
```

### Indentation

**Rule**: 4 spaces (NO tabs)

```python
# ✅ CORRECT
def function():
    if condition:
        do_something()
    else:
        do_other()

# ❌ INCORRECT
def function():
  if condition:  # 2 spaces = WRONG
    do_something()
```

### Imports

**Rule**: Absolute imports, grouped and sorted

**Order**:
1. Standard library
2. Third-party libraries
3. Local app imports

```python
# ✅ CORRECT
import os
import sys
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_movement import StockMovement
from app.repositories.stock_repository import StockRepository
from app.services.stock_service import StockService

# ❌ INCORRECT
from app.models.stock_movement import StockMovement  # Local first = WRONG
import os  # Stdlib after local = WRONG
from fastapi import *  # Star imports = WRONG
```

**Enforced by**: Ruff's `I` rule (isort)

### Quotes

**Rule**: Double quotes `"` (enforced by Ruff)

```python
# ✅ CORRECT
name = "DemeterAI"
query = "SELECT * FROM stock_movements"

# ❌ INCORRECT
name = 'DemeterAI'  # Single quotes = inconsistent
```

---

## Type Hints

### Required

**Rule**: ALL public functions MUST have type hints

```python
# ✅ CORRECT
async def get_stock(stock_id: int) -> Optional[StockMovement]:
    pass

def calculate_total(movements: List[StockMovement]) -> int:
    pass

# ❌ INCORRECT
async def get_stock(stock_id):  # No type hints = WRONG
    pass

def calculate_total(movements):  # No type hints = WRONG
    pass
```

### Complex Types

**Use typing module**:
```python
from typing import List, Dict, Optional, Union, Tuple, Any

# ✅ CORRECT
def process_data(
    items: List[Dict[str, Any]],
    config: Optional[Dict[str, int]] = None
) -> Tuple[int, str]:
    pass

# ❌ INCORRECT
def process_data(items, config=None):  # No hints
    pass
```

### Return Types

**Rule**: Always specify return type (use `None` for void)

```python
# ✅ CORRECT
async def save_data(data: dict) -> None:
    await repo.create(data)

# ❌ INCORRECT
async def save_data(data: dict):  # No return type
    await repo.create(data)
```

---

## Docstrings

### Required

**Rule**: ALL public classes, functions, and modules MUST have docstrings

**Format**: Google style (readable, concise)

```python
# ✅ CORRECT
async def get_stock_movements(
    location_id: int,
    start_date: datetime,
    end_date: datetime
) -> List[StockMovement]:
    """
    Get all stock movements for a location within a date range.

    Args:
        location_id: Storage location ID
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of stock movements sorted by created_at DESC

    Raises:
        LocationNotFoundException: If location_id doesn't exist
    """
    pass

# ❌ INCORRECT
async def get_stock_movements(location_id, start_date, end_date):
    # No docstring = WRONG
    pass
```

### Module Docstrings

```python
# ✅ CORRECT at top of file
"""
Stock movement service module.

Handles creation, updates, and queries for stock movements.
Supports both photo-based and manual initialization.
"""

from typing import List
# ... rest of code
```

---

## Error Handling

### Custom Exceptions

**Rule**: Use custom exceptions (NOT generic Exception)

```python
# ✅ CORRECT
class ProductMismatchException(AppBaseException):
    def __init__(self, expected: int, actual: int):
        super().__init__(
            technical_message=f"Product {actual} != expected {expected}",
            user_message="Product does not match configuration",
            code=400
        )

# Usage
if config.product_id != request.product_id:
    raise ProductMismatchException(config.product_id, request.product_id)

# ❌ INCORRECT
if config.product_id != request.product_id:
    raise Exception("Product mismatch")  # Generic exception = WRONG
```

### Never Catch-and-Drop

```python
# ✅ CORRECT
try:
    result = await service.process()
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise  # Re-raise to propagate

# ❌ INCORRECT
try:
    result = await service.process()
except Exception:
    pass  # Silent failure = VERY BAD
```

---

## Logging

### No print() Statements

**Rule**: Use `logger` (NOT print)

```python
import logging

logger = logging.getLogger(__name__)

# ✅ CORRECT
logger.info(f"Processing photo {photo_id}")
logger.error(f"Failed to upload to S3: {error}", exc_info=True)

# ❌ INCORRECT
print(f"Processing photo {photo_id}")  # print() = WRONG
print(f"Error: {error}")  # print() = WRONG
```

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Development details | `logger.debug(f"SQL: {query}")` |
| `INFO` | Normal operations | `logger.info(f"Photo {id} processed")` |
| `WARNING` | Recoverable issues | `logger.warning(f"Retrying S3 upload")` |
| `ERROR` | Errors (recoverable) | `logger.error(f"DB query failed")` |
| `CRITICAL` | System failures | `logger.critical(f"DB unreachable")` |

---

## Git Commit Messages

### Format

**Rule**: `<type>: <description>`

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

```bash
# ✅ CORRECT
git commit -m "feat: implement SAHI detection for segments"
git commit -m "fix: validate product_id matches config"
git commit -m "refactor: extract mask generation to separate service"
git commit -m "test: add unit tests for stock movement service"
git commit -m "docs: add architecture decision record for UUID generation"

# ❌ INCORRECT
git commit -m "update stuff"  # Too vague
git commit -m "Fixed bug"  # No type prefix
git commit -m "FEAT: Added feature"  # Capitalized type
git commit -m "feat:implement SAHI"  # No space after colon
```

---

## SQL Naming

### Tables

**Rule**: `snake_case`, plural (usually)

```sql
-- ✅ CORRECT
CREATE TABLE stock_movements (...)
CREATE TABLE photo_processing_sessions (...)

-- ❌ INCORRECT
CREATE TABLE StockMovements (...)  -- PascalCase = WRONG
CREATE TABLE stock_movement (...)  -- Singular = inconsistent
```

### Columns

**Rule**: `snake_case`, descriptive

```sql
-- ✅ CORRECT
movement_id UUID PRIMARY KEY
storage_location_id INT
total_plants_detected INT

-- ❌ INCORRECT
movementId UUID  -- camelCase = WRONG
loc_id INT  -- Abbreviation = unclear
total_plants INT  -- Missing context
```

### Foreign Keys

**Rule**: `<table_name>_id` (singular table name + `_id`)

```sql
-- ✅ CORRECT
storage_location_id INT REFERENCES storage_locations(id)
product_id INT REFERENCES products(id)

-- ❌ INCORRECT
storage_location INT  -- Missing _id suffix
storage_locations_id INT  -- Plural = WRONG
location_id INT  -- Ambiguous (which location table?)
```

---

## Status & Enum Values

### Status Fields

**Rule**: `snake_case`, lowercase

```python
# ✅ CORRECT
status = "pending"
status = "in_progress"
status = "completed"

# ❌ INCORRECT
status = "Pending"  # Capitalized = WRONG
status = "IN_PROGRESS"  # All caps = WRONG
status = "inProgress"  # camelCase = WRONG
```

### Movement Types

```python
# ✅ CORRECT
movement_type = "plantar"
movement_type = "muerte"
movement_type = "transplante"
movement_type = "ventas"
movement_type = "foto"
movement_type = "manual_init"

# ❌ INCORRECT
movement_type = "PLANTING"  # All caps = WRONG
movement_type = "manualInit"  # camelCase = WRONG
```

---

## Verification Commands

**Run before committing**:
```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy app/

# Tests
pytest

# Pre-commit hooks (runs all of above)
pre-commit run --all-files
```

---

## References

- **PEP 8**: https://peps.python.org/pep-0008/
- **Ruff Config**: ../../backlog/04_templates/config-templates/ruff.toml.template
- **Pre-commit Config**: ../../backlog/05_dev-environment/pre-commit-config.yaml

---

**Document Owner**: Backend Team Lead
**Enforcement**: Automated (Ruff + pre-commit hooks + CI/CD)
**Violations**: Code review will reject non-compliant PRs
