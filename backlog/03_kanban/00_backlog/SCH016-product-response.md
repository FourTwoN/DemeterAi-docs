# [SCH016] ProductResponse Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Response schema for products.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class ProductResponse(BaseModel):
      """Response schema for product."""

      product_id: int
      code: str
      name: str
      scientific_name: Optional[str]

      product_category_id: int
      product_family_id: int
      product_state: str

      # Related data
      category_name: Optional[str] = None
      family_name: Optional[str] = None

      created_at: datetime

      class Config:
          from_attributes = True

      @classmethod
      def from_model(cls, product, include_related: bool = False):
          data = {
              "product_id": product.product_id,
              "code": product.code,
              "name": product.name,
              "scientific_name": product.scientific_name,
              "product_category_id": product.product_category_id,
              "product_family_id": product.product_family_id,
              "product_state": product.product_state,
              "created_at": product.created_at
          }

          if include_related:
              if product.category:
                  data["category_name"] = product.category.name
              if product.family:
                  data["family_name"] = product.family.name

          return cls(**data)
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
