"""Product Family Pydantic schemas (LEVEL 2 taxonomy)."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.product_family import ProductFamily


class ProductFamilyCreateRequest(BaseModel):
    """Request schema for creating a product family."""

    category_id: int = Field(..., gt=0, description="Parent category ID (FK to product_categories)")
    name: str = Field(..., min_length=1, max_length=255, description="Family name")
    scientific_name: str | None = Field(
        None, max_length=255, description="Scientific name (optional)"
    )
    description: str | None = Field(None, description="Optional detailed description")


class ProductFamilyUpdateRequest(BaseModel):
    """Request schema for updating a product family."""

    name: str | None = Field(None, min_length=1, max_length=255)
    scientific_name: str | None = None
    description: str | None = None


class ProductFamilyResponse(BaseModel):
    """Response schema for product family."""

    family_id: int
    category_id: int
    name: str
    scientific_name: str | None
    description: str | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, family_model: "ProductFamily") -> "ProductFamilyResponse":
        """Create response from SQLAlchemy model."""
        from typing import cast

        return cls(
            family_id=cast(int, family_model.family_id),
            category_id=cast(int, family_model.category_id),
            name=cast(str, family_model.name),
            scientific_name=family_model.scientific_name,
            description=family_model.description,
        )
