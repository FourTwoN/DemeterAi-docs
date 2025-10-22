# [SCH011] StockMovementResponse Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (2 story points)
- **Area**: `backend/schemas`

## Description

Response schema for stock movements with from_model factory method.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  from datetime import datetime
  from uuid import UUID

  class StockMovementResponse(BaseModel):
      """Response schema for stock movement."""

      stock_movement_id: UUID
      storage_batch_id: int
      movement_type: str
      quantity: int
      source_type: str
      notes: Optional[str]
      created_at: datetime
      user_id: int

      # Related data
      batch_code: Optional[str] = None
      product_name: Optional[str] = None
      location_name: Optional[str] = None

      class Config:
          from_attributes = True

      @classmethod
      def from_model(cls, movement, include_related: bool = False):
          """Factory method to create from SQLAlchemy model."""
          data = {
              "stock_movement_id": movement.stock_movement_id,
              "storage_batch_id": movement.storage_batch_id,
              "movement_type": movement.movement_type,
              "quantity": movement.quantity,
              "source_type": movement.source_type,
              "notes": movement.notes,
              "created_at": movement.created_at,
              "user_id": movement.user_id
          }

          if include_related and movement.stock_batch:
              data["batch_code"] = movement.stock_batch.batch_code
              if movement.stock_batch.product:
                  data["product_name"] = movement.stock_batch.product.name
              if movement.stock_batch.storage_location:
                  data["location_name"] = movement.stock_batch.storage_location.name

          return cls(**data)
  ```

**Coverage Target**: ≥85%

---

**Card Created**: 2025-10-09
