"""Packaging Color Pydantic schemas."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


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

    id: int
    name: str
    hex_code: str

    model_config = ConfigDict(from_attributes=True)
