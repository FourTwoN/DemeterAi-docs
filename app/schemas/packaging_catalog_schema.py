"""Packaging Catalog Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.packaging_catalog import PackagingCatalog


class PackagingCatalogCreateRequest(BaseModel):
    """Request schema for creating packaging catalog."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    packaging_type_id: int
    packaging_material_id: int
    packaging_color_id: int
    volume_liters: float = Field(..., gt=0)
    diameter_cm: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)


class PackagingCatalogUpdateRequest(BaseModel):
    """Request schema for updating packaging catalog."""

    name: str | None = Field(None, min_length=1, max_length=200)
    volume_liters: float | None = Field(None, gt=0)
    diameter_cm: float | None = Field(None, gt=0)
    height_cm: float | None = Field(None, gt=0)


class PackagingCatalogResponse(BaseModel):
    """Response schema for packaging catalog."""

    packaging_catalog_id: int
    code: str
    name: str
    packaging_type_id: int
    packaging_material_id: int
    packaging_color_id: int
    volume_liters: float
    diameter_cm: float
    height_cm: float
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "PackagingCatalog") -> "PackagingCatalogResponse":
        return cls(
            packaging_catalog_id=model.packaging_catalog_id,
            code=model.code,
            name=model.name,
            packaging_type_id=model.packaging_type_id,
            packaging_material_id=model.packaging_material_id,
            packaging_color_id=model.packaging_color_id,
            volume_liters=model.volume_liters,
            diameter_cm=model.diameter_cm,
            height_cm=model.height_cm,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
