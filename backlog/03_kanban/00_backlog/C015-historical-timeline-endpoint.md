# [C015] Historical Timeline - GET /api/map/timeline

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Retrieve historical stock movements for a location (timeline view).

## Acceptance Criteria

- [ ] **AC1**: Query params: storage_location_id, date_from, date_to
- [ ] **AC2**: Return movements ordered by created_at DESC
- [ ] **AC3**: Include movement type, quantity, user

```python
@router.get("/timeline", response_model=List[StockMovementResponse])
async def get_location_timeline(
    storage_location_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    service: StockMovementService = Depends()
):
    """Get historical movements for location."""
    return await service.get_timeline(storage_location_id, date_from, date_to)
```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
