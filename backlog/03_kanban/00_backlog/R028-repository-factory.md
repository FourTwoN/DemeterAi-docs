# R028: Repository Factory & Dependency Injection

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [S001-S023] (ALL services need repositories)
  - Blocked by: [F006, R027, R001-R026]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository factory pattern and FastAPI dependency injection for all repositories.

**Why**: Services need repository instances with proper session management. Factory pattern + dependency injection ensures: (1) proper transaction scope, (2) automatic session cleanup, (3) testability via mock repositories.

**Context**: FastAPI dependency injection integrates with SQLAlchemy async sessions. Each request gets dedicated session. Repositories injected into service layer.

## Acceptance Criteria

- [ ] **AC1**: Factory function `get_repository(repo_class: Type[AsyncRepository], session: AsyncSession)` returns repository instance
- [ ] **AC2**: FastAPI dependency `get_db_session()` yields async session with cleanup
- [ ] **AC3**: Individual dependency functions for each repository (e.g., `get_warehouse_repo()`)
- [ ] **AC4**: Repository dependencies properly typed for IDE autocomplete
- [ ] **AC5**: Session cleanup guaranteed (try/finally block)
- [ ] **AC6**: Integration with FastAPI route dependencies (`Depends()`)

## Technical Implementation Notes

```python
# app/dependencies/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: provides async session with cleanup"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# app/dependencies/repositories.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db_session
from app.repositories.warehouse_repository import WarehouseRepository
# ... other repositories

async def get_warehouse_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> WarehouseRepository:
    """FastAPI dependency: provides WarehouseRepository"""
    return WarehouseRepository(session)

# Repeat for all repositories (R001-R027)
async def get_storage_area_repo(
    session: Annotated[AsyncSession, Depends(get_db_session)]
) -> StorageAreaRepository:
    return StorageAreaRepository(session)

# ... etc


# Usage in FastAPI routes:
from fastapi import APIRouter, Depends
from app.dependencies.repositories import get_warehouse_repo
from app.repositories.warehouse_repository import WarehouseRepository

router = APIRouter()

@router.get("/warehouses/{code}")
async def get_warehouse_by_code(
    code: str,
    repo: Annotated[WarehouseRepository, Depends(get_warehouse_repo)]
):
    warehouse = await repo.get_by_code(code)
    return warehouse
```

## Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_get_db_session_cleanup(db_session):
    """Test session cleanup on success"""
    async for session in get_db_session():
        assert session.is_active
        # Simulate successful operation
        pass
    # Session should be committed and closed

@pytest.mark.asyncio
async def test_get_db_session_rollback_on_error(db_session):
    """Test session rollback on exception"""
    with pytest.raises(ValueError):
        async for session in get_db_session():
            raise ValueError("Test error")
    # Session should be rolled back and closed

@pytest.mark.asyncio
async def test_get_warehouse_repo_dependency(db_session):
    """Test warehouse repository dependency injection"""
    async for session in get_db_session():
        repo = await get_warehouse_repo(session)
        assert isinstance(repo, WarehouseRepository)
        assert repo.session == session
```

## Definition of Done Checklist

- [ ] Session dependency with cleanup implemented
- [ ] Factory functions for all 27 repositories created
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests with FastAPI routes
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Documentation: dependency injection guide

## Time Tracking
- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
