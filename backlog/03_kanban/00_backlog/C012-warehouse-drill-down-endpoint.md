# [C012] Warehouse Drill-Down - GET /api/map/warehouses/{id}/areas

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
  - Blocked by: [DB001, DB002-storage-areas-model]

## Description

Drill down from warehouse to storage areas (level 2 hierarchy).

## Acceptance Criteria

- [ ] **AC1**: Path parameter: warehouse_id
- [ ] **AC2**: Return all storage_areas for warehouse
- [ ] **AC3**: Include stock summary per area

```python
@router.get("/warehouses/{warehouse_id}/areas", response_model=List[StorageAreaResponse])
async def get_warehouse_areas(
    warehouse_id: int,
    service: StorageAreaService = Depends()
):
    """Get storage areas for warehouse."""
    return await service.get_by_warehouse(warehouse_id)
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
