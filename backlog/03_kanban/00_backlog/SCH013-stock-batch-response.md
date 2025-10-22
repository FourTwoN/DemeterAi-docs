# [SCH013] StockBatchResponse Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/schemas`

## Description

Response schema for stock batches.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class StockBatchResponse(BaseModel):
      """Response schema for stock batch."""

      stock_batch_id: int
      batch_code: str
      storage_location_id: int
      product_id: int
      packaging_catalog_id: int
      product_size_id: int

      initial_quantity: int
      current_quantity: int
      batch_status: str  # activo, agotado, vendido

      planting_date: Optional[date]
      created_at: datetime

      # Related data (optional)
      product_name: Optional[str] = None
      packaging_name: Optional[str] = None
      location_name: Optional[str] = None

      class Config:
          from_attributes = True

      @classmethod
      def from_model(cls, batch, include_related: bool = False):
          data = {
              "stock_batch_id": batch.stock_batch_id,
              "batch_code": batch.batch_code,
              "storage_location_id": batch.storage_location_id,
              "product_id": batch.product_id,
              "packaging_catalog_id": batch.packaging_catalog_id,
              "product_size_id": batch.product_size_id,
              "initial_quantity": batch.initial_quantity,
              "current_quantity": batch.current_quantity,
              "batch_status": batch.batch_status,
              "planting_date": batch.planting_date,
              "created_at": batch.created_at
          }

          if include_related:
              if batch.product:
                  data["product_name"] = batch.product.name
              if batch.packaging_catalog:
                  data["packaging_name"] = batch.packaging_catalog.name
              if batch.storage_location:
                  data["location_name"] = batch.storage_location.name

          return cls(**data)
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
