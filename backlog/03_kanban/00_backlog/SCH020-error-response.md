# [SCH020] ErrorResponse Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Standard error response schema for all API errors.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class ErrorResponse(BaseModel):
      """Standard error response schema."""

      error: str = Field(
          ...,
          description="User-friendly error message",
          example="Product mismatch"
      )

      detail: str = Field(
          ...,
          description="Technical error details",
          example="The product you entered (Sedum Blue) does not match the configured product (Echeveria Golden)"
      )

      code: Optional[str] = Field(
          None,
          description="Error code for programmatic handling",
          example="PRODUCT_MISMATCH"
      )

      timestamp: datetime = Field(
          default_factory=datetime.utcnow,
          description="Error timestamp (UTC)"
      )

      class Config:
          json_schema_extra = {
              "example": {
                  "error": "Product mismatch",
                  "detail": "The product you entered does not match the configured product",
                  "code": "PRODUCT_MISMATCH",
                  "timestamp": "2025-10-08T14:30:00Z"
              }
          }

      @classmethod
      def from_exception(cls, exc: Exception, code: Optional[str] = None):
          """Factory method from exception."""
          return cls(
              error=exc.__class__.__name__,
              detail=str(exc),
              code=code
          )
  ```

- [ ] **AC2**: Used in global exception handler

**Coverage Target**: ≥85%

---

**Card Created**: 2025-10-09
