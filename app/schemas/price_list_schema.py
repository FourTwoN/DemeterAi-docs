"""Price List Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class PriceListCreateRequest(BaseModel):
    """Request schema for creating price list."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    price_per_unit: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class PriceListUpdateRequest(BaseModel):
    """Request schema for updating price list."""

    name: str | None = Field(None, min_length=1, max_length=200)
    price_per_unit: float | None = Field(None, gt=0)


class PriceListResponse(BaseModel):
    """Response schema for price list."""

    id: int
    packaging_catalog_id: int
    product_categories_id: int
    wholesale_unit_price: int
    retail_unit_price: int
    SKU: str | None
    unit_per_storage_box: int | None
    wholesale_total_price_per_box: int | None
    observations: str | None
    availability: str | None
    discount_factor: int | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
