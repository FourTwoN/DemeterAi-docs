# R027: Base Repository (AsyncRepository[T] Generic)

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `CRITICAL` (V0 - blocks all repositories)
- **Complexity**: M (5 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R001-R026] (ALL repositories inherit from this)
  - Blocked by: [F006]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)

## Description

**What**: Implement generic base repository class `AsyncRepository[T]` with common CRUD operations, pagination, and transaction support.

**Why**: All repositories inherit from this base class. Provides consistent interface, reduces code duplication, and ensures best practices (async/await, typing, transactions).

**Context**: Foundation for repository layer. Uses SQLAlchemy 2.0 typed API with generics. Supports pagination, soft deletes, and complex queries.

## Acceptance Criteria

- [ ] **AC1**: Generic class `AsyncRepository[T]` with TypeVar bound to SQLAlchemy Base
- [ ] **AC2**: Implements `get(id: int) -> Optional[T]` for PK lookup
- [ ] **AC3**: Implements `get_multi(skip: int, limit: int) -> List[T]` for pagination
- [ ] **AC4**: Implements `create(obj: dict) -> T` with transaction support
- [ ] **AC5**: Implements `update(id: int, obj: dict) -> Optional[T]` with partial updates
- [ ] **AC6**: Implements `delete(id: int) -> bool` with soft delete support
- [ ] **AC7**: Implements `count() -> int` for pagination metadata
- [ ] **AC8**: All methods use SQLAlchemy 2.0 async API (execute, scalars)

## Technical Implementation Notes

```python
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)

class AsyncRepository(Generic[T]):
    """Generic async repository for CRUD operations"""

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: int) -> Optional[T]:
        """Get entity by primary key"""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[T]:
        """Get multiple entities with pagination"""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: Dict[str, Any]) -> T:
        """Create new entity"""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        id: int,
        obj_in: Dict[str, Any]
    ) -> Optional[T]:
        """Update entity (partial update supported)"""
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        """Delete entity"""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def count(self) -> int:
        """Count total entities"""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar()
```

## Definition of Done Checklist

- [ ] Code written with full type hints
- [ ] Unit tests pass (≥90% coverage)
- [ ] All CRUD methods tested
- [ ] Pagination tested
- [ ] Transaction support tested
- [ ] Linting passes (ruff check)
- [ ] mypy passes (strict mode)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
**CRITICAL PATH**: All repositories depend on this
