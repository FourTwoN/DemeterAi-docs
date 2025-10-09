# [C011] List Warehouses - GET /api/map/warehouses

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
  - Blocked by: [SVC006-warehouse-service, DB001-warehouses-model]

## Description

List all warehouses with geospatial data for map visualization.

## Acceptance Criteria

- [ ] **AC1**: Return all active warehouses
- [ ] **AC2**: Include geojson_coordinates, centroid, area_m2
- [ ] **AC3**: Filter by warehouse_type (optional)

```python
@router.get("/warehouses", response_model=List[WarehouseResponse])
async def list_warehouses(
    warehouse_type: Optional[str] = None,
    active_only: bool = True,
    service: WarehouseService = Depends()
):
    """List warehouses for map."""
    return await service.list_warehouses(warehouse_type, active_only)
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
