"""Analytics and Reporting API Controllers.

This module provides HTTP endpoints for analytics and reporting:
- Daily plant counts (time series)
- Full inventory reports
- Data exports (CSV, JSON)

Architecture:
    Layer: Controller Layer (HTTP only)
    Dependencies: Service layer only (NO business logic here)
    Pattern: Thin controllers - delegate to services

Endpoints:
    GET /api/v1/analytics/daily-counts - Daily plant counts (C024)
    GET /api/v1/analytics/inventory-report - Full inventory report (C025)
    GET /api/v1/analytics/exports/{format} - Export data (C026)
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.analytics_schema import InventoryReportResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# =============================================================================
# Dependency Injection
# =============================================================================


def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
    """Dependency injection for ServiceFactory."""
    return ServiceFactory(session)


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "/daily-counts",
    response_model=list[dict],
    summary="Get daily plant counts",
)
async def get_daily_plant_counts(
    start_date: date = Query(..., description="Start date (inclusive)"),
    end_date: date = Query(..., description="End date (inclusive)"),
    location_id: int | None = Query(None, description="Filter by storage location ID"),
    product_id: int | None = Query(None, description="Filter by product ID"),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """Get daily plant counts time series (C024).

    Aggregates stock movement data by day to show inventory trends.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        location_id: Optional storage location filter
        product_id: Optional product filter

    Returns:
        List of daily count records

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/analytics/daily-counts?start_date=2025-10-01&end_date=2025-10-20"
        ```

    Response:
        ```json
        [
          {
            "date": "2025-10-01",
            "total_plants": 125000,
            "movements_in": 5000,
            "movements_out": 1500,
            "net_change": 3500
          },
          {
            "date": "2025-10-02",
            "total_plants": 128500,
            "movements_in": 6000,
            "movements_out": 2500,
            "net_change": 3500
          }
        ]
        ```
    """
    try:
        logger.info(
            "Getting daily plant counts",
            extra={
                "start_date": start_date,
                "end_date": end_date,
                "location_id": location_id,
                "product_id": product_id,
            },
        )

        # TODO: Implement daily aggregation query
        # This requires:
        # 1. Join StockMovement with StockBatch
        # 2. Filter by date range
        # 3. Optionally filter by location_id and product_id
        # 4. Group by date
        # 5. Aggregate: SUM(quantity WHERE is_inbound=true), SUM(quantity WHERE is_inbound=false)

        logger.warning("Daily counts endpoint not yet fully implemented")

        # Placeholder response
        return [
            {
                "date": str(start_date),
                "total_plants": 0,
                "movements_in": 0,
                "movements_out": 0,
                "net_change": 0,
                "message": "Analytics not yet implemented",
            }
        ]

    except Exception as e:
        logger.error("Failed to get daily counts", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get daily plant counts.",
        )


@router.get(
    "/inventory-report",
    response_model=InventoryReportResponse,
    summary="Get full inventory report",
)
async def get_full_inventory_report(
    warehouse_id: int | None = Query(None, description="Filter by warehouse ID"),
    product_id: int | None = Query(None, description="Filter by product ID"),
    factory: ServiceFactory = Depends(get_factory),
) -> InventoryReportResponse:
    """Get comprehensive inventory report (C025).

    Provides current stock levels across all locations.

    Args:
        warehouse_id: Optional warehouse filter
        product_id: Optional product filter

    Returns:
        Comprehensive inventory report

    Raises:
        HTTPException 500: Report generation error
    """
    try:
        logger.info(
            "Generating inventory report",
            extra={"warehouse_id": warehouse_id, "product_id": product_id},
        )

        service = factory.get_analytics_service()
        report = await service.get_inventory_report(
            warehouse_id=warehouse_id,
            product_id=product_id,
        )

        logger.info(
            "Inventory report generated",
            extra={
                "total_batches": report.total_batches,
                "total_plants": report.total_plants,
            },
        )

        return report

    except Exception as e:
        logger.error(
            "Failed to generate inventory report",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate inventory report.",
        )


@router.get(
    "/exports/{export_format}",
    summary="Export data",
)
async def export_data(
    export_format: str,
    report_type: str = Query(..., description="Report type (inventory, movements, batches)"),
    start_date: date | None = Query(None, description="Start date filter"),
    end_date: date | None = Query(None, description="End date filter"),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Export analytics data in CSV or JSON format (C026).

    Supported formats:
    - csv: Comma-separated values
    - json: JSON array

    Supported report types:
    - inventory: Current stock levels
    - movements: Stock movement history
    - batches: Stock batch details

    Args:
        export_format: Export format (csv or json)
        report_type: Report type (inventory, movements, batches)
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        StreamingResponse with file download

    Raises:
        HTTPException 400: Invalid format or report type
        HTTPException 500: Export error

    Example:
        ```bash
        # Export inventory as CSV
        curl "http://localhost:8000/api/v1/analytics/exports/csv?report_type=inventory" -O

        # Export movements as JSON with date filter
        curl "http://localhost:8000/api/v1/analytics/exports/json?report_type=movements&start_date=2025-10-01&end_date=2025-10-20" -O
        ```
    """
    try:
        logger.info(
            "Exporting data",
            extra={
                "format": export_format,
                "report_type": report_type,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        # Validate format
        if export_format not in ["csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid export format: {export_format}. Must be 'csv' or 'json'.",
            )

        # Validate report type
        if report_type not in ["inventory", "movements", "batches"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report type: {report_type}. Must be 'inventory', 'movements', or 'batches'.",
            )

        # TODO: Implement actual data export
        # This requires:
        # 1. Query data based on report_type
        # 2. Convert to CSV or JSON
        # 3. Stream as file download

        logger.warning("Data export not yet fully implemented")

        # Placeholder response
        import io

        if export_format == "csv":
            content = "id,name,value\n1,placeholder,0\n"
            media_type = "text/csv"
            filename = f"{report_type}_export.csv"
        else:  # json
            content = '[{"id": 1, "name": "placeholder", "value": 0}]'
            media_type = "application/json"
            filename = f"{report_type}_export.json"

        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Failed to export data", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export data.",
        )
