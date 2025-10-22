# [SCH005] AnalyticsQueryRequest Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-05
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/schemas`
- **Assignee**: TBD

## Description

Request schema for analytics query endpoint with multi-dimensional filters.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  from typing import Optional, List
  from datetime import date

  class AnalyticsQueryRequest(BaseModel):
      """Request schema for analytics query."""

      warehouse_ids: Optional[List[int]] = Field(None, description="Filter by warehouses")
      storage_area_ids: Optional[List[int]] = None
      product_ids: Optional[List[int]] = None

      date_from: Optional[date] = Field(None, description="Start date")
      date_to: Optional[date] = Field(None, description="End date")

      group_by: Optional[List[str]] = Field(
          None,
          description="Group by dimensions",
          example=["warehouse", "product"]
      )

      include_movements: bool = Field(
          False,
          description="Include movement breakdown"
      )

      @field_validator('group_by')
      @classmethod
      def validate_group_by(cls, v):
          if v:
              allowed = ['warehouse', 'storage_area', 'product', 'packaging']
              for dim in v:
                  if dim not in allowed:
                      raise ValueError(f"Invalid group_by: {dim}")
          return v
  ```

**Coverage Target**: ≥85%

## Time Tracking

- **Estimated**: 2 story points

---

**Card Created**: 2025-10-09
