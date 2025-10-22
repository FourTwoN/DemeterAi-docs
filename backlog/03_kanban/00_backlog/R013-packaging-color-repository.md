# R013: Packaging Color Repository

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
    - Blocked by: [F006, F007, DB022]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L151-L155)

## Description

**What**: Implement repository class for `packaging_colors` table with CRUD operations and hex code
lookup.

**Why**: Packaging colors define container color options (negro, terracota, blanco). Repository
provides lookup by name or hex code for UI color pickers.

**Context**: Master data for packaging color classification. Hex codes enable consistent color
display in UI.

## Acceptance Criteria

- [ ] **AC1**: `PackagingColorRepository` class inherits from `AsyncRepository[PackagingColor]`
- [ ] **AC2**: Implements `get_by_name(name: str)` method (unique constraint)
- [ ] **AC3**: Implements `get_by_hex_code(hex_code: str)` for UI color picker
- [ ] **AC4**: Implements `get_all_active()` for dropdown lists
- [ ] **AC5**: Query performance: <10ms

## Technical Implementation Notes

```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_color import PackagingColor
from app.repositories.base_repository import AsyncRepository

class PackagingColorRepository(AsyncRepository[PackagingColor]):
    """Repository for packaging color CRUD"""

    def __init__(self, session: AsyncSession):
        super().__init__(PackagingColor, session)

    async def get_by_name(self, name: str) -> Optional[PackagingColor]:
        stmt = select(PackagingColor).where(PackagingColor.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hex_code(self, hex_code: str) -> Optional[PackagingColor]:
        stmt = select(PackagingColor).where(PackagingColor.hex_code == hex_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[PackagingColor]:
        stmt = select(PackagingColor).order_by(PackagingColor.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Hex code validation tested
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
