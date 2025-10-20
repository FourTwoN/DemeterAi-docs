"""Density Parameter Pydantic schemas."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.density_parameter import DensityParameter


class DensityParameterCreateRequest(BaseModel):
    """Request schema for creating density parameter."""

    name: str = Field(..., min_length=1, max_length=200)
    plants_per_m2: float = Field(..., gt=0, description="Expected plant density per square meter")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class DensityParameterUpdateRequest(BaseModel):
    """Request schema for updating density parameter."""

    name: str | None = Field(None, min_length=1, max_length=200)
    plants_per_m2: float | None = Field(None, gt=0)
    confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)


class DensityParameterResponse(BaseModel):
    """Response schema for density parameter."""

    density_parameter_id: int
    name: str
    plants_per_m2: float
    confidence_threshold: float
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: "DensityParameter") -> "DensityParameterResponse":
        return cls(
            density_parameter_id=model.density_parameter_id,
            name=model.name,
            plants_per_m2=model.plants_per_m2,
            confidence_threshold=model.confidence_threshold,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
