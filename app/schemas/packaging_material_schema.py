"""Packaging Material Pydantic schemas."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class PackagingMaterialCreateRequest(BaseModel):
    """Request schema for creating packaging material."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)


class PackagingMaterialUpdateRequest(BaseModel):
    """Request schema for updating packaging material."""

    name: str | None = Field(None, min_length=1, max_length=200)


class PackagingMaterialResponse(BaseModel):
    """Response schema for packaging material."""

    id: int
    code: str
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
