# [C014] GPS Lookup - GET /api/map/gps-lookup

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `high` (critical for photo localization)
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocked by: [SVC007-localization-service, DB001-warehouses-model]

## Description

Convert GPS coordinates to storage_location using PostGIS ST_Contains.

## Acceptance Criteria

- [ ] **AC1**: Query params: latitude, longitude
- [ ] **AC2**: Use PostGIS point-in-polygon query
- [ ] **AC3**: Return storage_location or 404

```python
@router.get("/gps-lookup", response_model=LocationResponse)
async def gps_lookup(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    service: LocalizationService = Depends()
):
    """Find location from GPS coordinates."""
    location = await service.find_location_by_gps(latitude, longitude)
    if not location:
        raise HTTPException(404, "No location found for GPS coordinates")
    return location
```

**Coverage Target**: ≥85%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
