# [SCH006] ProductCreateRequest Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Request schema for creating products.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class ProductCreateRequest(BaseModel):
      """Request schema for product creation."""

      code: str = Field(..., min_length=2, max_length=50)
      name: str = Field(..., min_length=2, max_length=200)
      scientific_name: Optional[str] = Field(None, max_length=200)

      product_category_id: int = Field(..., gt=0)
      product_family_id: int = Field(..., gt=0)

      product_state: str = Field(..., example="vivo")

      @field_validator('code')
      @classmethod
      def validate_code_uppercase(cls, v):
          if not v.isupper():
              raise ValueError("Product code must be uppercase")
          return v
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
