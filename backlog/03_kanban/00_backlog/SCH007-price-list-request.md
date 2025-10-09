# [SCH007] PriceListRequest Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Request schema for price list entries.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  from decimal import Decimal

  class PriceListRequest(BaseModel):
      """Request schema for price list."""

      product_id: int = Field(..., gt=0)
      packaging_catalog_id: int = Field(..., gt=0)
      product_size_id: int = Field(..., gt=0)

      price: Decimal = Field(..., gt=0, decimal_places=2)
      currency: str = Field(..., min_length=3, max_length=3, example="USD")

      @field_validator('currency')
      @classmethod
      def validate_currency(cls, v):
          if not v.isupper():
              raise ValueError("Currency must be uppercase")
          return v
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
