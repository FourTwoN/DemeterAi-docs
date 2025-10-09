# [SCH010] GPSLookupRequest Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Request schema for GPS lookup (query parameters, not body).

## Acceptance Criteria

- [ ] **AC1**: Query parameter validation in controller (no separate schema needed):
  ```python
  # In controller:
  latitude: float = Query(..., ge=-90, le=90, description="Latitude")
  longitude: float = Query(..., ge=-180, le=180, description="Longitude")
  ```

- [ ] **AC2**: Alternative: Define schema for documentation:
  ```python
  class GPSLookupRequest(BaseModel):
      """GPS coordinates for location lookup."""

      latitude: float = Field(..., ge=-90, le=90)
      longitude: float = Field(..., ge=-180, le=180)
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
