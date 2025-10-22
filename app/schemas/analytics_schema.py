"""
Analytics Schemas - Pydantic Models for Analytics Responses

This module defines response schemas for analytics and reporting endpoints.
"""

from datetime import date, datetime

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


class DailyPlantCountResponse(BaseModel):
    """Response schema for daily plant count analytics."""

    date: date = Field(..., description="Date of the count")
    total_plants: int = Field(..., description="Total plants in inventory on this date", ge=0)
    movements_in: int = Field(..., description="Plants moved in on this date", ge=0)
    movements_out: int = Field(..., description="Plants moved out on this date", ge=0)
    net_change: int = Field(..., description="Net change in inventory (in - out)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "date": "2025-10-21",
                "total_plants": 45000,
                "movements_in": 1200,
                "movements_out": 800,
                "net_change": 400,
            }
        },
    )


class DataExportResponse(BaseModel):
    """Response schema for data export operations."""

    export_format: str = Field(..., description="Format of the exported data (csv, json, xlsx)")
    file_url: str | None = Field(None, description="URL to download the exported file")
    file_size: int | None = Field(None, description="Size of the exported file in bytes")
    record_count: int = Field(..., description="Number of records exported", ge=0)
    generated_at: datetime = Field(..., description="Timestamp when export was generated")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "export_format": "csv",
                "file_url": "https://s3.example.com/exports/inventory_2025-10-21.csv",
                "file_size": 524288,
                "record_count": 1500,
                "generated_at": "2025-10-21T10:30:00Z",
            }
        },
    )
