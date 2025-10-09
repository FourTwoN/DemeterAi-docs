# S010: BatchLifecycleService

## Metadata
- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (3 story points)
- **Area**: `services/stock`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [C009]
  - Blocked by: [S008]

## Description

**What**: Implement `BatchLifecycleService` for batch status transitions (planting → active → transplanted → sold).

**Why**: Tracks batch lifecycle from planting to final disposition. Provides batch history and aging calculations.

**Context**: Clean Architecture Application Layer. Wraps S008 (StockBatchService) to add lifecycle management.

## Acceptance Criteria

- [ ] **AC1**: Update batch status:
```python
class BatchLifecycleService:
    def __init__(self, batch_service: StockBatchService):
        self.batch_service = batch_service

    async def transition_batch_status(
        self,
        batch_id: int,
        new_status: str
    ) -> StockBatchResponse:
        """Transition batch to new status"""
        valid_transitions = {
            "active": ["transplanted", "sold"],
            "transplanted": ["sold"],
            "sold": []
        }

        batch = await self.batch_service.get_batch_by_id(batch_id)
        if new_status not in valid_transitions.get(batch.batch_status, []):
            raise InvalidStatusTransition(batch.batch_status, new_status)

        updated = await self.batch_service.update_batch_status(batch_id, new_status)
        return updated
```

- [ ] **AC2**: Calculate batch age:
```python
async def calculate_batch_age(self, batch_id: int) -> int:
    """Calculate batch age in days"""
    batch = await self.batch_service.get_batch_by_id(batch_id)
    return (datetime.utcnow() - batch.planting_date).days
```

- [ ] **AC3**: Unit tests achieve ≥85% coverage

## Definition of Done Checklist

- [ ] Service code written
- [ ] Status transitions validated
- [ ] Unit tests pass (≥85% coverage)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
