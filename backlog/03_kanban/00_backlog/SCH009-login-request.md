# [SCH009] LoginRequest Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Request schema for login endpoint.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class LoginRequest(BaseModel):
      """Request schema for login."""

      email: EmailStr = Field(..., example="user@example.com")
      password: str = Field(..., min_length=1, max_length=100)

      class Config:
          json_schema_extra = {
              "example": {
                  "email": "admin@demeterai.com",
                  "password": "SecurePassword123"
              }
          }
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
