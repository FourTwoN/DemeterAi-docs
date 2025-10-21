"""Product Category Pydantic schemas (ROOT taxonomy level)."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.product_category import ProductCategory


class ProductCategoryCreateRequest(BaseModel):
    """Request schema for creating a product category."""

    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique category code (alphanumeric + underscores)",
    )
    name: str = Field(..., min_length=1, max_length=200, description="Human-readable category name")
    description: str | None = Field(None, description="Optional detailed description")


class ProductCategoryUpdateRequest(BaseModel):
    """Request schema for updating a product category."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None


class ProductCategoryResponse(BaseModel):
    """Response schema for product category."""

    id: int
    code: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, category_model: "ProductCategory") -> "ProductCategoryResponse":
        """Create response from SQLAlchemy model."""
        return cls(
            id=category_model.id,
            code=category_model.code,
            name=category_model.name,
            description=category_model.description,
            created_at=category_model.created_at,
            updated_at=category_model.updated_at,
        )
