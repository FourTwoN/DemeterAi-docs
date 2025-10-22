# [C021] Create Location Config - POST /api/config/location

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `high` (critical for manual init validation)
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [SCH004]
    - Blocked by: [SVC009-location-config-service, DB024-storage-location-config]

## Description

Create storage_location_config defining product/packaging for a location.

## Acceptance Criteria

- [ ] **AC1**: Request body: storage_location_id, product_id, packaging_catalog_id, product_size_id
- [ ] **AC2**: Validate location has no existing config (one config per location)
- [ ] **AC3**: Return HTTP 201 Created

```python
@router.post("/location", response_model=LocationConfigResponse, status_code=201)
async def create_location_config(
    request: LocationConfigRequest,
    current_user: User = Depends(get_current_user),
    service: LocationConfigService = Depends()
):
    """Create storage location configuration."""
    return await service.create_config(request)
```

**Coverage Target**: ≥85%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
