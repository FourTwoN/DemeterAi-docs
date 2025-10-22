# [SCH015] AnalyticsReportResponse Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/schemas`

## Description

Response schema for analytics query results.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class AnalyticsReportRow(BaseModel):
      """Single row in analytics report."""

      # Dimensions (based on group_by)
      warehouse_id: Optional[int]
      warehouse_name: Optional[str]
      storage_area_id: Optional[int]
      storage_area_name: Optional[str]
      product_id: Optional[int]
      product_name: Optional[str]
      packaging_id: Optional[int]
      packaging_name: Optional[str]

      # Metrics
      total_plants: int
      total_batches: int

      # Movements (optional)
      movements: Optional[dict] = None  # {"plantado": 100, "muerte": -50}

  class AnalyticsReportResponse(BaseModel):
      """Response schema for analytics report."""

      report_data: List[AnalyticsReportRow]

      totals: dict  # {"total_plants": 5000, "total_batches": 50}

      filters_applied: dict  # Echo back filters

      generated_at: datetime
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
