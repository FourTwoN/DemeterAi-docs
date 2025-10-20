"""Packaging Type Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.packaging_type import PackagingType


class PackagingTypeCreateRequest(BaseModel):
    """Request schema for creating packaging type."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)


class PackagingTypeUpdateRequest(BaseModel):
    """Request schema for updating packaging type."""

    name: str | None = Field(None, min_length=1, max_length=200)


class PackagingTypeResponse(BaseModel):
    """Response schema for packaging type."""

    packaging_type_id: int
    code: str
    name: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "PackagingType") -> "PackagingTypeResponse":
        return cls(
            packaging_type_id=model.packaging_type_id,
            code=model.code,
            name=model.name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
