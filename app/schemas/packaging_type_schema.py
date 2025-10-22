"""Packaging Type Pydantic schemas."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class PackagingTypeCreateRequest(BaseModel):
    """Request schema for creating packaging type."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)


class PackagingTypeUpdateRequest(BaseModel):
    """Request schema for updating packaging type."""

    name: str | None = Field(None, min_length=1, max_length=200)


class PackagingTypeResponse(BaseModel):
    """Response schema for packaging type."""

    id: int
    code: str
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
