# [SCH019] AuthTokenResponse Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Response schema for JWT authentication tokens.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class AuthTokenResponse(BaseModel):
      """Response schema for authentication tokens."""

      access_token: str = Field(
          ...,
          description="JWT access token (15 min expiry)",
          example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      )

      refresh_token: str = Field(
          ...,
          description="JWT refresh token (7 day expiry)",
          example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      )

      token_type: str = Field(
          default="bearer",
          description="Token type",
          example="bearer"
      )

      expires_in: int = Field(
          ...,
          description="Access token expiry in seconds",
          example=900
      )

      class Config:
          json_schema_extra = {
              "example": {
                  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                  "token_type": "bearer",
                  "expires_in": 900
              }
          }
  ```

**Coverage Target**: ≥85%

---

**Card Created**: 2025-10-09
