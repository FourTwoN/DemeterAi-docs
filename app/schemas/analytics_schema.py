"""
Analytics Schemas - Pydantic Models for Analytics Responses

This module defines response schemas for analytics and reporting endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryReportResponse(BaseModel):
    """
    Response schema for inventory analytics report.

    Attributes:
        total_batches: Total number of stock batches in the report scope
        total_plants: Total number of plants across all batches
        warehouse_id: Optional warehouse filter applied to the report
        product_id: Optional product filter applied to the report
        generated_at: Timestamp when the report was generated
    """

    total_batches: int = Field(
        ..., description="Total number of stock batches in the report scope", ge=0
    )
    total_plants: int = Field(..., description="Total number of plants across all batches", ge=0)
    warehouse_id: int | None = Field(
        None, description="Warehouse ID if report was filtered by warehouse"
    )
    product_id: int | None = Field(None, description="Product ID if report was filtered by product")
    generated_at: datetime = Field(..., description="Timestamp when the report was generated")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "total_batches": 150,
                "total_plants": 45000,
                "warehouse_id": 1,
                "product_id": 5,
                "generated_at": "2025-10-21T10:30:00Z",
            }
        },
    )
