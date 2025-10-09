# [SCH018] UserResponse Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Response schema for users (excludes password hash).

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class UserResponse(BaseModel):
      """Response schema for user (no password)."""

      user_id: int
      email: str
      first_name: str
      last_name: str
      role: str
      active: bool

      created_at: datetime
      last_login: Optional[datetime]

      class Config:
          from_attributes = True

      @classmethod
      def from_model(cls, user):
          """Factory method from User model (excludes password_hash)."""
          return cls(
              user_id=user.user_id,
              email=user.email,
              first_name=user.first_name,
              last_name=user.last_name,
              role=user.role,
              active=user.active,
              created_at=user.created_at,
              last_login=user.last_login
          )
  ```

- [ ] **AC2**: NEVER include password_hash in response

**Coverage Target**: ≥85%

---

**Card Created**: 2025-10-09
