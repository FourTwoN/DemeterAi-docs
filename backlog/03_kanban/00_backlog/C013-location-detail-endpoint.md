# [C013] Location Detail - GET /api/map/locations/{id}

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Get storage_location detail with configuration and current stock.

## Acceptance Criteria

- [ ] **AC1**: Return location + config + stock batches
- [ ] **AC2**: Include geospatial data
- [ ] **AC3**: Return 404 if not found

```python
@router.get("/locations/{location_id}", response_model=LocationResponse)
async def get_location_detail(
    location_id: int,
    service: StorageLocationService = Depends()
):
    """Get location detail with config and stock."""
    location = await service.get_with_details(location_id)
    if not location:
        raise HTTPException(404, "Location not found")
    return location
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
