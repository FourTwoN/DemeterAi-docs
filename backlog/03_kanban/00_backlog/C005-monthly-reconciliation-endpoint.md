# [C005] Monthly Reconciliation Report - GET /api/stock/reconciliation

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-03 (Week 7-8)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: L (3 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocked by: [SVC005-reconciliation-service, DB007, DB008]

## Description

Generate monthly reconciliation report with calculated sales.

**What**: GET endpoint returning:

- Previous month photo count
- Movements (plantado, muerte, trasplante)
- Current month photo count
- **Calculated sales**: previous + movements - current

**Why**: Core business workflow - automated sales calculation from inventory changes.

## Acceptance Criteria

- [ ] **AC1**: Route defined:
  ```python
  @router.get(
      "/reconciliation",
      response_model=ReconciliationReportResponse,
      summary="Monthly reconciliation report"
  )
  async def get_reconciliation_report(
      year: int,
      month: int,
      warehouse_id: Optional[int] = None,
      service: ReconciliationService = Depends()
  ):
      """Generate reconciliation report for month."""
      return await service.generate_report(year, month, warehouse_id)
  ```

- [ ] **AC2**: Response includes:
    - opening_count (from photo/manual)
    - movements_summary (plantado, muerte, trasplante totals)
    - closing_count (from end-month photo)
    - **calculated_sales** = opening + movements - closing

- [ ] **AC3**: Validation: year 2020-2030, month 1-12

**Coverage Target**: ≥85%

## Definition of Done Checklist

- [ ] Route defined
- [ ] Sales calculation correct
- [ ] Unit tests ≥85%

## Time Tracking

- **Estimated**: 3 story points

---

**Card Created**: 2025-10-09
