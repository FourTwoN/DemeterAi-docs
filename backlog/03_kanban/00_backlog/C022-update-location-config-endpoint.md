# [C022] Update Location Config - PUT /api/config/location/{id}

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Update existing location configuration (change product/packaging).

## Acceptance Criteria

- [ ] **AC1**: Path param: config_id
- [ ] **AC2**: Allow partial updates (PATCH-style)
- [ ] **AC3**: Return updated config

```python
@router.put("/location/{config_id}", response_model=LocationConfigResponse)
async def update_location_config(
    config_id: int,
    request: LocationConfigRequest,
    service: LocationConfigService = Depends()
):
    """Update location configuration."""
    config = await service.update_config(config_id, request)
    if not config:
        raise HTTPException(404, "Config not found")
    return config
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
