# [C016] Analytics Query - POST /api/analytics/query

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: L (3 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [SCH005]
    - Blocked by: [SVC008-analytics-service]

## Description

Flexible analytics query endpoint with multi-dimensional filtering.

## Acceptance Criteria

- [ ] **AC1**: POST request body with filters:
    - warehouse_ids, storage_area_ids, product_ids
    - date_from, date_to
    - group_by (warehouse, product, packaging)
    - include_movements (boolean)

- [ ] **AC2**: Return aggregated data with totals

```python
@router.post("/query", response_model=AnalyticsReportResponse)
async def analytics_query(
    request: AnalyticsQueryRequest,
    service: AnalyticsService = Depends()
):
    """Execute analytics query with filters."""
    return await service.execute_query(request)
```

**Coverage Target**: ≥85%

## Time Tracking

- **Estimated**: 3 story points

---

**Card Created**: 2025-10-09
