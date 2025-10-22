# [C017] Month-over-Month Comparison - POST /api/analytics/compare

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: M (2 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD

## Description

Compare stock metrics between two time periods (month-over-month, year-over-year).

## Acceptance Criteria

- [ ] **AC1**: Request body: period_1 (start/end), period_2 (start/end)
- [ ] **AC2**: Return comparison metrics: growth %, absolute change
- [ ] **AC3**: Support multiple groupings (warehouse, product)

```python
@router.post("/compare", response_model=ComparisonReportResponse)
async def compare_periods(
    period_1_start: date,
    period_1_end: date,
    period_2_start: date,
    period_2_end: date,
    group_by: Optional[List[str]] = None,
    service: AnalyticsService = Depends()
):
    """Compare stock metrics between periods."""
    return await service.compare_periods(
        period_1_start, period_1_end,
        period_2_start, period_2_end,
        group_by
    )
```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
