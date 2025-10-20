"""Price List Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.price_list import PriceList


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

    price_list_id: int
    code: str
    name: str
    price_per_unit: float
    currency: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "PriceList") -> "PriceListResponse":
        return cls(
            price_list_id=model.price_list_id,
            code=model.code,
            name=model.name,
            price_per_unit=model.price_per_unit,
            currency=model.currency,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
