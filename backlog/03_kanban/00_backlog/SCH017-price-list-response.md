# [SCH017] PriceListResponse Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `low`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`

## Description

Response schema for price list entries.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  from decimal import Decimal

  class PriceListResponse(BaseModel):
      """Response schema for price list."""

      price_id: int
      product_id: int
      packaging_catalog_id: int
      product_size_id: int

      price: Decimal
      currency: str

      # Related data
      product_name: Optional[str] = None
      packaging_name: Optional[str] = None
      size_name: Optional[str] = None

      created_at: datetime
      updated_at: Optional[datetime]

      class Config:
          from_attributes = True

      @classmethod
      def from_model(cls, price_list, include_related: bool = False):
          data = {
              "price_id": price_list.price_id,
              "product_id": price_list.product_id,
              "packaging_catalog_id": price_list.packaging_catalog_id,
              "product_size_id": price_list.product_size_id,
              "price": price_list.price,
              "currency": price_list.currency,
              "created_at": price_list.created_at,
              "updated_at": price_list.updated_at
          }

          if include_related:
              if price_list.product:
                  data["product_name"] = price_list.product.name
              if price_list.packaging_catalog:
                  data["packaging_name"] = price_list.packaging_catalog.name
              if price_list.product_size:
                  data["size_name"] = price_list.product_size.name

          return cls(**data)
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
