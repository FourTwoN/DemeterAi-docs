# [SCH003] StockMovementRequest Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`
- **Assignee**: TBD

## Description

Request schema for stock movements (plantado, muerte, trasplante).

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  from pydantic import BaseModel, Field, field_validator
  from typing import Optional

  class StockMovementRequest(BaseModel):
      """Request schema for stock movement."""

      storage_batch_id: int = Field(..., gt=0)

      movement_type: str = Field(
          ...,
          description="Movement type",
          example="plantado"
      )

      quantity: int = Field(
          ...,
          description="Quantity (positive for plantado, negative for muerte)",
          example=100
      )

      notes: Optional[str] = Field(None, max_length=500)

      @field_validator('movement_type')
      @classmethod
      def validate_movement_type(cls, v):
          allowed = ['plantado', 'muerte', 'trasplante']
          if v not in allowed:
              raise ValueError(f"movement_type must be one of {allowed}")
          return v

      @field_validator('quantity')
      @classmethod
      def validate_quantity_sign(cls, v, values):
          """Plantado must be positive, muerte must be negative."""
          movement_type = values.data.get('movement_type')
          if movement_type == 'plantado' and v <= 0:
              raise ValueError("plantado quantity must be positive")
          if movement_type == 'muerte' and v >= 0:
              raise ValueError("muerte quantity must be negative")
          return v
  ```

**Coverage Target**: ≥85%

## Time Tracking
- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
