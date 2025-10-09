# R012: Packaging Material Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: XS (1 story point)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R014]
  - Blocked by**: [F006, F007, DB021]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L145-L150)

## Description

**What**: Implement repository class for `packaging_materials` table with CRUD operations.

**Why**: Packaging materials define container material types (plastico, ceramica, biodegradable). Repository provides lookup for packaging catalog.

**Context**: Master data for packaging material classification.

## Acceptance Criteria

- [ ] **AC1**: `PackagingMaterialRepository` class inherits from `AsyncRepository[PackagingMaterial]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method
- [ ] **AC3**: Implements `get_all_active()` for dropdown lists
- [ ] **AC4**: Query performance: <10ms

## Technical Implementation Notes

```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_material import PackagingMaterial
from app.repositories.base_repository import AsyncRepository

class PackagingMaterialRepository(AsyncRepository[PackagingMaterial]):
    """Repository for packaging material CRUD"""

    def __init__(self, session: AsyncSession):
        super().__init__(PackagingMaterial, session)

    async def get_by_code(self, code: str) -> Optional[PackagingMaterial]:
        stmt = select(PackagingMaterial).where(PackagingMaterial.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[PackagingMaterial]:
        stmt = select(PackagingMaterial).order_by(PackagingMaterial.name)
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
