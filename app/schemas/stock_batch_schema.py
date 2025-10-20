"""Stock Batch Pydantic schemas (inventory tracking)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StockBatchCreateRequest(BaseModel):
    batch_code: str = Field(..., min_length=6, max_length=50)
    current_storage_bin_id: int = Field(..., gt=0)
    product_id: int = Field(..., gt=0)
    product_state_id: int | None = None
    product_size_id: int | None = None
    has_packaging: bool = Field(default=False)
    packaging_catalog_id: int | None = None
    quantity_initial: int = Field(..., gt=0)
    quantity_current: int = Field(..., ge=0)
    quantity_empty_containers: int = Field(default=0, ge=0)
    quality_score: Decimal | None = Field(None, ge=0, le=5)
    planting_date: date | None = None
    custom_attributes: dict[str, Any] | None = None


class StockBatchResponse(BaseModel):
    batch_id: int
    batch_code: str
    current_storage_bin_id: int
    product_id: int
    quantity_initial: int
    quantity_current: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
