"""Packaging Material Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.packaging_material import PackagingMaterial


class PackagingMaterialCreateRequest(BaseModel):
    """Request schema for creating packaging material."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)


class PackagingMaterialUpdateRequest(BaseModel):
    """Request schema for updating packaging material."""

    name: str | None = Field(None, min_length=1, max_length=200)


class PackagingMaterialResponse(BaseModel):
    """Response schema for packaging material."""

    packaging_material_id: int
    code: str
    name: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "PackagingMaterial") -> "PackagingMaterialResponse":
        return cls(
            packaging_material_id=model.packaging_material_id,
            code=model.code,
            name=model.name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
