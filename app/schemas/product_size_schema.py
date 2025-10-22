"""Product Size Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.product_size import ProductSize


class ProductSizeCreateRequest(BaseModel):
    """Request schema for creating a product size."""

    code: str = Field(
        ..., min_length=1, max_length=50, description="Size code (XS, S, M, L, XL, etc.)"
    )
    name: str = Field(..., min_length=1, max_length=200, description="Size name")
    min_height_cm: float = Field(..., gt=0, description="Minimum height in cm")
    max_height_cm: float = Field(..., gt=0, description="Maximum height in cm")


class ProductSizeUpdateRequest(BaseModel):
    """Request schema for updating a product size."""

    name: str | None = Field(None, min_length=1, max_length=200)
    min_height_cm: float | None = Field(None, gt=0)
    max_height_cm: float | None = Field(None, gt=0)


class ProductSizeResponse(BaseModel):
    """Response schema for product size."""

    product_size_id: int
    code: str
    name: str
    min_height_cm: float | None
    max_height_cm: float | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "ProductSize") -> "ProductSizeResponse":
        """Create response from SQLAlchemy model."""
        from decimal import Decimal
        from typing import cast

        min_h = None
        if model.min_height_cm is not None:
            min_h = (
                float(model.min_height_cm)
                if isinstance(model.min_height_cm, Decimal)
                else model.min_height_cm
            )

        max_h = None
        if model.max_height_cm is not None:
            max_h = (
                float(model.max_height_cm)
                if isinstance(model.max_height_cm, Decimal)
                else model.max_height_cm
            )

        return cls(
            product_size_id=cast(int, model.product_size_id),
            code=cast(str, model.code),
            name=cast(str, model.name),
            min_height_cm=min_h,
            max_height_cm=max_h,
            created_at=cast(datetime, model.created_at),
            updated_at=model.updated_at,
        )
