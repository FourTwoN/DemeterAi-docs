# [C020] Stock Trends - GET /api/analytics/trends

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Time-series data for stock trends (daily/weekly/monthly granularity).

## Acceptance Criteria

- [ ] **AC1**: Query params: date_from, date_to, granularity (daily/weekly/monthly)
- [ ] **AC2**: Return time-series data points
- [ ] **AC3**: Filter by warehouse, product

```python
@router.get("/trends", response_model=List[TrendDataPoint])
async def get_stock_trends(
    date_from: date,
    date_to: date,
    granularity: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    warehouse_id: Optional[int] = None,
    product_id: Optional[int] = None,
    service: AnalyticsService = Depends()
):
    """Get stock trends over time."""
    return await service.get_trends(
        date_from, date_to, granularity, warehouse_id, product_id
    )
```

**Coverage Target**: ≥80%

## Time Tracking
- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
