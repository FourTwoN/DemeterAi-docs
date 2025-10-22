# [SCH004] LocationConfigRequest Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`
- **Assignee**: TBD

## Description

Request schema for creating/updating storage location configuration.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class LocationConfigRequest(BaseModel):
      """Request schema for location configuration."""

      storage_location_id: int = Field(..., gt=0)
      product_id: int = Field(..., gt=0)
      packaging_catalog_id: int = Field(..., gt=0)
      product_size_id: int = Field(..., gt=0)
  ```

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
