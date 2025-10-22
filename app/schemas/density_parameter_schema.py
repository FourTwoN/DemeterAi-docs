"""Density Parameter Pydantic schemas."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


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

    id: int
    storage_bin_type_id: int
    product_id: int
    packaging_catalog_id: int
    avg_area_per_plant_cm2: float
    plants_per_m2: float
    overlap_adjustment_factor: float
    avg_diameter_cm: float
    notes: str | None

    model_config = ConfigDict(from_attributes=True)
