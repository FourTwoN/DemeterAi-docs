# [F010] mypy Configuration - Type Checking

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (2 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [Type safety quality gates]
  - Blocked by: [F001, F002, F003]

## Related Documentation
- **Conventions**: ../../backlog/00_foundation/conventions.md#type-hints
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md#testing--quality

## Description

Configure mypy for static type checking with strict mode, SQLAlchemy plugin, and incremental checking to catch type errors before runtime.

**What**: Create `pyproject.toml` mypy configuration with strict type checking enabled, SQLAlchemy plugin for ORM models, and exclusions for auto-generated code. Integrate with pre-commit hooks.

**Why**: Type hints catch bugs at development time (not production). mypy verifies FastAPI route signatures, SQLAlchemy model types, and Pydantic schema compatibility. Strict mode enforces type hints on all functions.

**Context**: Python is dynamically typed. Without mypy, type errors appear at runtime (e.g., passing int where str expected). DemeterAI has 240+ functions - manual type verification is impossible. mypy automates type safety.

## Acceptance Criteria

- [ ] **AC1**: `pyproject.toml` contains mypy configuration:
  ```toml
  [tool.mypy]
  python_version = "3.12"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  disallow_untyped_defs = true

  [[tool.mypy.overrides]]
  module = "alembic.*"
  ignore_errors = true

  [[tool.mypy.overrides]]
  module = "tests.*"
  disallow_untyped_defs = false
  ```

- [ ] **AC2**: SQLAlchemy plugin enabled:
  ```toml
  [tool.mypy]
  plugins = ["sqlalchemy.ext.mypy.plugin"]
  ```

- [ ] **AC3**: Type stubs for third-party libraries:
  ```toml
  [project.optional-dependencies]
  dev = [
      "mypy==1.8.0",
      "types-requests",
      "types-redis",
      "types-python-dateutil"
  ]
  ```

- [ ] **AC4**: Commands work:
  ```bash
  mypy app/                    # Type check app directory
  mypy app/ --strict           # Extra strict checking
  mypy app/services/stock_service.py  # Check single file
  ```

- [ ] **AC5**: Pre-commit integration:
  - mypy runs on every commit
  - Commits blocked if type errors found

- [ ] **AC6**: Type hints enforced:
  ```python
  # ✅ CORRECT (type hints)
  def create_warehouse(code: str, name: str) -> Warehouse:
      return Warehouse(code=code, name=name)

  # ❌ BLOCKED (missing type hints)
  def create_warehouse(code, name):
      return Warehouse(code=code, name=name)
  ```

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Code Quality)
- Dependencies: mypy 1.8.0, sqlalchemy stubs, pre-commit (F003)
- Design pattern: Static type checking

### Code Hints

**pyproject.toml complete configuration:**
```toml
[tool.mypy]
python_version = "3.12"
strict = true

# Error reporting
warn_return_any = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true

# Type checking behavior
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true

# Strict mode options
no_implicit_optional = true
strict_equality = true
strict_concatenate = true

# SQLAlchemy support
plugins = ["sqlalchemy.ext.mypy.plugin"]

# Incremental caching
incremental = true
cache_dir = ".mypy_cache"

# Exclude auto-generated code
[[tool.mypy.overrides]]
module = "alembic.versions.*"
ignore_errors = true

[[tool.mypy.overrides]]
module = "alembic.env"
ignore_errors = true

# Relax strict mode for tests
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

**Example typed code:**
```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.warehouse import Warehouse

class WarehouseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, warehouse_id: int) -> Optional[Warehouse]:
        """Get warehouse by ID."""
        result = await self.session.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[Warehouse]:
        """Get all warehouses."""
        result = await self.session.execute(select(Warehouse))
        return list(result.scalars().all())
```

### Testing Requirements

**Unit Tests**: N/A (static analysis tool)

**Integration Tests**:
- [ ] Test mypy catches type errors:
  ```python
  # Create file with type error
  echo "def foo(x: int) -> str: return x" > test_type_error.py
  mypy test_type_error.py
  # Expected: Error: Incompatible return value type
  ```

- [ ] Test mypy with strict mode:
  ```python
  # Create file without type hints
  echo "def foo(x): return x + 1" > test_no_types.py
  mypy test_no_types.py --strict
  # Expected: Error: Function is missing a type annotation
  ```

- [ ] Test pre-commit integration:
  ```bash
  # Create file with type error
  echo "def foo(x: int) -> str: return x" > app/test.py
  git add app/test.py
  git commit -m "test"
  # Expected: Commit blocked by mypy
  ```

**Test Command**:
```bash
# Test on all existing code
mypy app/
```

### Performance Expectations
- Type checking: <5 seconds for entire codebase
- Incremental checking: <1 second for single file change
- Cache warmup: <10 seconds first run

## Handover Briefing

**For the next developer:**
- **Context**: This is the type safety gate - all code must have type hints and pass mypy
- **Key decisions**:
  - Strict mode enabled (enforces type hints on all functions)
  - SQLAlchemy plugin (understands ORM models)
  - Tests excluded from strict mode (allow untyped test helpers)
  - Alembic excluded (auto-generated migration code)
  - Incremental caching (faster re-checks)
- **Known limitations**:
  - mypy doesn't catch all type errors (some runtime checks still needed)
  - Third-party libraries without type stubs need `type: ignore` comments
  - Generic types can be verbose (e.g., `List[Optional[Dict[str, Any]]]`)
- **Next steps after this card**:
  - All new code must include type hints
  - Pre-commit runs mypy automatically
  - CI/CD runs `mypy app/ --strict` (Sprint 05)
- **Questions to ask**:
  - Should we use pyright instead of mypy? (alternative type checker)
  - Should we enforce 100% type coverage? (strict but time-consuming)
  - Should we add runtime type checking with pydantic? (already used)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] pyproject.toml configured with mypy options
- [ ] SQLAlchemy plugin enabled
- [ ] Type stubs installed for third-party libraries
- [ ] mypy runs successfully on existing code
- [ ] Pre-commit hook integration tested
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with mypy commands)
- [ ] Sample typed code verified with mypy

## Time Tracking
- **Estimated**: 2 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
