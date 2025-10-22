"""Product State Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.product_state import ProductState


class ProductStateCreateRequest(BaseModel):
    """Request schema for creating a product state."""

    code: str = Field(..., min_length=1, max_length=50, description="State code")
    name: str = Field(..., min_length=1, max_length=200, description="State name")
    is_sellable: bool = Field(default=False, description="Can be sold in this state")


class ProductStateUpdateRequest(BaseModel):
    """Request schema for updating a product state."""

    name: str | None = Field(None, min_length=1, max_length=200)
    is_sellable: bool | None = None


class ProductStateResponse(BaseModel):
    """Response schema for product state."""

    product_state_id: int
    code: str
    name: str
    is_sellable: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "ProductState") -> "ProductStateResponse":
        """Create response from SQLAlchemy model."""
        return cls(
            product_state_id=cast(int, model.product_state_id),
            code=cast(str, model.code),
            name=cast(str, model.name),
            is_sellable=cast(bool, model.is_sellable),
            created_at=cast(datetime, model.created_at),
            updated_at=model.updated_at,
        )
