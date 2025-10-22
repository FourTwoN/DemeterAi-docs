# R011: Packaging Type Repository

## Metadata

- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: XS (1 story point)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [R014, S010]
    - Blocked by: [F006, F007, DB020]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L114-L119)

## Description

**What**: Implement repository class for `packaging_types` table with CRUD operations.

**Why**: Packaging types define container categories (maceta, bolsa, bandeja). Repository provides
lookup for packaging catalog and ML classification.

**Context**: Master data for packaging categories. Used to organize packaging_catalog entries.

## Acceptance Criteria

- [ ] **AC1**: `PackagingTypeRepository` class inherits from `AsyncRepository[PackagingType]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method
- [ ] **AC3**: Implements `get_all_active()` for dropdown lists
- [ ] **AC4**: Query performance: <10ms

## Technical Implementation Notes

```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_type import PackagingType
from app.repositories.base_repository import AsyncRepository

class PackagingTypeRepository(AsyncRepository[PackagingType]):
    """Repository for packaging type CRUD"""

    def __init__(self, session: AsyncSession):
        super().__init__(PackagingType, session)

    async def get_by_code(self, code: str) -> Optional[PackagingType]:
        stmt = select(PackagingType).where(PackagingType.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[PackagingType]:
        stmt = select(PackagingType).order_by(PackagingType.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)

## Time Tracking

- **Estimated**: 1 story point (~2 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
