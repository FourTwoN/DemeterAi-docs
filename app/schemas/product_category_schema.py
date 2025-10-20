"""Product Category Pydantic schemas (ROOT taxonomy level)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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

    product_category_id: int
    code: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, category_model):
        """Create response from SQLAlchemy model."""
        return cls(
            product_category_id=category_model.product_category_id,
            code=category_model.code,
            name=category_model.name,
            description=category_model.description,
            created_at=category_model.created_at,
            updated_at=category_model.updated_at,
        )
