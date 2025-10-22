"""Estimation Pydantic schemas for ML estimation results."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.models.estimation import CalculationMethodEnum


class EstimationCreate(BaseModel):
    """Schema for creating an estimation."""

    session_id: int = Field(..., description="Photo processing session ID")
    stock_movement_id: int = Field(..., description="Stock movement ID")
    classification_id: int = Field(..., description="Classification ID")
    vegetation_polygon: dict[str, Any] = Field(..., description="Vegetation polygon coordinates")
    detected_area_cm2: Decimal = Field(..., ge=0.0, description="Detected area in cm²")
    estimated_count: int = Field(..., ge=0, description="Estimated plant count")
    calculation_method: CalculationMethodEnum = Field(..., description="Calculation method")
    estimation_confidence: Decimal = Field(
        Decimal("0.70"), ge=0.0, le=1.0, description="ML confidence score"
    )
    used_density_parameters: bool = Field(False, description="Whether density parameters were used")

    model_config = {"from_attributes": True}


class EstimationBulkCreateRequest(BaseModel):
    """Schema for bulk creating estimations."""

    session_id: int = Field(..., description="Photo processing session ID")
    estimations: list[EstimationCreate] = Field(..., description="List of estimations")

    model_config = {"from_attributes": True}


class EstimationResponse(BaseModel):
    """Schema for estimation responses."""

    id: int = Field(..., description="Estimation ID")
    session_id: int = Field(...)
    stock_movement_id: int = Field(...)
    classification_id: int = Field(...)
    vegetation_polygon: dict[str, Any] = Field(...)
    detected_area_cm2: Decimal = Field(...)
    estimated_count: int = Field(...)
    calculation_method: CalculationMethodEnum = Field(...)
    estimation_confidence: Decimal = Field(...)
    used_density_parameters: bool = Field(...)
    created_at: datetime = Field(...)

    model_config = {"from_attributes": True}


class EstimationStatistics(BaseModel):
    """Schema for estimation statistics."""

    total_count: int = Field(..., description="Total estimations")
    total_estimated_plants: int = Field(..., description="Sum of all estimated counts")
    avg_confidence: Decimal = Field(..., description="Average confidence score")
    min_confidence: Decimal = Field(..., description="Minimum confidence score")
    max_confidence: Decimal = Field(..., description="Maximum confidence score")
    band_estimation_count: int = Field(..., description="Band estimation count")
    density_estimation_count: int = Field(..., description="Density estimation count")
    grid_analysis_count: int = Field(..., description="Grid analysis count")

    model_config = {"from_attributes": True}
