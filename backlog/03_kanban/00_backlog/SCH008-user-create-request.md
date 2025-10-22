# [SCH008] UserCreateRequest Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Request schema for user creation (admin endpoint).

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  from pydantic import EmailStr

  class UserCreateRequest(BaseModel):
      """Request schema for user creation."""

      email: EmailStr = Field(..., example="user@example.com")
      password: str = Field(..., min_length=8, max_length=100)
      first_name: str = Field(..., min_length=1, max_length=100)
      last_name: str = Field(..., min_length=1, max_length=100)
      role: str = Field(..., example="user")

      @field_validator('role')
      @classmethod
      def validate_role(cls, v):
          allowed = ['admin', 'user', 'viewer']
          if v not in allowed:
              raise ValueError(f"Role must be one of {allowed}")
          return v

      @field_validator('password')
      @classmethod
      def validate_password_strength(cls, v):
          """Basic password validation."""
          if not any(c.isupper() for c in v):
              raise ValueError("Password must contain uppercase")
          if not any(c.islower() for c in v):
              raise ValueError("Password must contain lowercase")
          if not any(c.isdigit() for c in v):
              raise ValueError("Password must contain digit")
          return v
  ```

**Coverage Target**: ≥85%

---

**Card Created**: 2025-10-09
