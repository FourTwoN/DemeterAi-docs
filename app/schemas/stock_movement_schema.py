"""Stock Movement Pydantic schemas (audit trail)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ManualStockInitRequest(BaseModel):
    """Request for manual stock initialization."""

    storage_location_id: int = Field(..., gt=0, description="Storage location ID")
    product_id: int = Field(..., gt=0, description="Product ID")
    packaging_catalog_id: int = Field(..., gt=0, description="Packaging catalog ID")
    product_size_id: int = Field(..., gt=0, description="Product size ID")
    quantity: int = Field(..., gt=0, description="Must be positive")
    planting_date: date = Field(..., description="Planting date")
    notes: str | None = Field(None, max_length=500, description="Optional notes")

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        """Validate quantity is positive."""
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class StockMovementRequest(BaseModel):
    """Request for stock movement operations."""

    storage_batch_id: int = Field(..., gt=0, description="Stock batch ID")
    movement_type: str = Field(..., min_length=1, description="Movement type")
    quantity: int = Field(..., description="Can be positive or negative")
    notes: str | None = Field(None, max_length=500, description="Optional notes")

    @field_validator("movement_type")
    @classmethod
    def validate_movement_type(cls, v: str) -> str:
        """Validate movement type is valid."""
        valid_types = ["plantado", "muerte", "trasplante", "ventas", "ajuste"]
        if v not in valid_types:
            raise ValueError(f"movement_type must be one of {valid_types}")
        return v


class StockMovementCreateRequest(BaseModel):
    batch_id: int = Field(..., gt=0)
    movement_type: str
    quantity: int
    user_id: int = Field(..., gt=0)
    source_type: str = Field(default="manual")
    is_inbound: bool
    reason_description: str | None = None
    source_bin_id: int | None = None
    destination_bin_id: int | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    processing_session_id: int | None = None


class StockMovementResponse(BaseModel):
    id: int
    movement_id: UUID
    batch_id: int
    movement_type: str
    quantity: int
    user_id: int
    source_type: str
    is_inbound: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
