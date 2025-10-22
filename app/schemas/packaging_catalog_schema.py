"""Packaging Catalog Pydantic schemas."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class PackagingCatalogCreateRequest(BaseModel):
    """Request schema for creating packaging catalog."""

    sku: str = Field(..., min_length=6, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    packaging_type_id: int
    packaging_material_id: int
    packaging_color_id: int
    volume_liters: float | None = Field(None, gt=0)
    diameter_cm: float | None = Field(None, gt=0)
    height_cm: float | None = Field(None, gt=0)


class PackagingCatalogUpdateRequest(BaseModel):
    """Request schema for updating packaging catalog."""

    name: str | None = Field(None, min_length=1, max_length=200)
    volume_liters: float | None = Field(None, gt=0)
    diameter_cm: float | None = Field(None, gt=0)
    height_cm: float | None = Field(None, gt=0)


class PackagingCatalogResponse(BaseModel):
    """Response schema for packaging catalog."""

    id: int
    packaging_type_id: int
    packaging_material_id: int
    packaging_color_id: int
    sku: str
    name: str
    volume_liters: float | None
    diameter_cm: float | None
    height_cm: float | None

    model_config = ConfigDict(from_attributes=True)
