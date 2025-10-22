# [C019] Dashboard Summary - GET /api/analytics/dashboard

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

High-level summary metrics for dashboard view (total plants, active batches, recent movements).

## Acceptance Criteria

- [ ] **AC1**: Return summary metrics:
    - total_plants (all active batches)
    - total_batches (count)
    - total_warehouses, total_locations
    - recent_movements (last 7 days)

- [ ] **AC2**: Optional filter by warehouse_id

```python
@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    warehouse_id: Optional[int] = None,
    service: AnalyticsService = Depends()
):
    """Get dashboard summary metrics."""
    return await service.get_dashboard_summary(warehouse_id)
```

**Coverage Target**: ≥85%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
