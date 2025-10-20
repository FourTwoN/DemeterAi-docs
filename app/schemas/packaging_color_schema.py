"""Packaging Color Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.packaging_color import PackagingColor


class PackagingColorCreateRequest(BaseModel):
    """Request schema for creating packaging color."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    hex_code: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")


class PackagingColorUpdateRequest(BaseModel):
    """Request schema for updating packaging color."""

    name: str | None = Field(None, min_length=1, max_length=200)
    hex_code: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class PackagingColorResponse(BaseModel):
    """Response schema for packaging color."""

    packaging_color_id: int
    code: str
    name: str
    hex_code: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "PackagingColor") -> "PackagingColorResponse":
        return cls(
            packaging_color_id=model.packaging_color_id,
            code=model.code,
            name=model.name,
            hex_code=model.hex_code,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
