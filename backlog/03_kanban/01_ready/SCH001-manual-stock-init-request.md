# [SCH001] ManualStockInitRequest Schema

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`
- **Assignee**: TBD
- **Dependencies**:
    - Blocked by: [DB007, DB024]

## Description

Pydantic request schema for manual stock initialization (POST /api/stock/manual).

## Acceptance Criteria

- [ ] **AC1**: Schema defined in `app/schemas/stock_schema.py`:
  ```python
  from pydantic import BaseModel, Field, field_validator
  from datetime import date
  from typing import Optional

  class ManualStockInitRequest(BaseModel):
      """Request schema for manual stock initialization."""

      storage_location_id: int = Field(
          ...,
          gt=0,
          description="Storage location ID where stock is initialized",
          example=123
      )

      product_id: int = Field(
          ...,
          gt=0,
          description="Product ID (must match location config)",
          example=45
      )

      packaging_catalog_id: int = Field(
          ...,
          gt=0,
          description="Packaging catalog ID (must match location config)",
          example=12
      )

      product_size_id: int = Field(
          ...,
          gt=0,
          description="Product size ID",
          example=3
      )

      quantity: int = Field(
          ...,
          gt=0,
          description="Quantity of plants to initialize",
          example=1500
      )

      planting_date: Optional[date] = Field(
          None,
          description="Planting date (optional, defaults to today)",
          example="2025-09-15"
      )

      notes: Optional[str] = Field(
          None,
          max_length=500,
          description="Optional notes",
          example="Initial count from Excel import"
      )

      class Config:
          json_schema_extra = {
              "example": {
                  "storage_location_id": 123,
                  "product_id": 45,
                  "packaging_catalog_id": 12,
                  "product_size_id": 3,
                  "quantity": 1500,
                  "planting_date": "2025-09-15",
                  "notes": "Initial count from Excel"
              }
          }

      @field_validator('quantity')
      @classmethod
      def validate_quantity(cls, v):
          """Ensure quantity is positive."""
          if v <= 0:
              raise ValueError("Quantity must be greater than 0")
          return v
  ```

- [ ] **AC2**: Field validation:
    - All IDs must be > 0
    - quantity must be > 0
    - notes max 500 chars
    - planting_date must be valid date

- [ ] **AC3**: OpenAPI example included

**Coverage Target**: ≥85%

## Time Tracking

- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
