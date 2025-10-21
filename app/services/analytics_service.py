"""
Analytics Service - Business Logic for Inventory Analytics

This service provides business intelligence and reporting capabilities
for inventory management, including aggregated stock reports and metrics.

Architecture: Service Layer (uses StockBatchRepository for data access)
"""

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_batch import StockBatch
from app.repositories.stock_batch_repository import StockBatchRepository
from app.schemas.analytics_schema import InventoryReportResponse

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for inventory analytics and reporting.

    This service aggregates stock data to provide business insights
    about inventory levels, distribution, and trends.

    Architecture Pattern:
    - Uses StockBatchRepository for database access
    - Returns Pydantic schemas (not SQLAlchemy models)
    - All methods are async
    - Comprehensive logging for audit trails
    """

    def __init__(self, stock_batch_repo: StockBatchRepository):
        """
        Initialize AnalyticsService with required dependencies.

        Args:
            stock_batch_repo: Repository for stock batch data access
        """
        self.stock_batch_repo = stock_batch_repo
        logger.info("AnalyticsService initialized")

    async def get_inventory_report(
        self, warehouse_id: int | None = None, product_id: int | None = None
    ) -> InventoryReportResponse:
        """
        Generate inventory analytics report with optional filters.

        This method aggregates stock batch data to provide:
        - Total number of batches
        - Total number of plants across all batches
        - Filtered by warehouse and/or product if specified

        Args:
            warehouse_id: Optional warehouse ID to filter results.
                         If None, includes all warehouses.
            product_id: Optional product ID to filter results.
                       If None, includes all products.

        Returns:
            InventoryReportResponse containing aggregated inventory metrics

        Raises:
            SQLAlchemyError: If database query fails

        Examples:
            >>> # Get global inventory report
            >>> report = await service.get_inventory_report()
            >>> print(f"Total plants: {report.total_plants}")

            >>> # Get report for specific warehouse
            >>> report = await service.get_inventory_report(warehouse_id=1)

            >>> # Get report for specific product across all warehouses
            >>> report = await service.get_inventory_report(product_id=5)

            >>> # Get report for specific product in specific warehouse
            >>> report = await service.get_inventory_report(
            ...     warehouse_id=1,
            ...     product_id=5
            ... )
        """
        logger.info(
            "Generating inventory report",
            extra={"warehouse_id": warehouse_id, "product_id": product_id},
        )

        # Access database session through repository
        session: AsyncSession = self.stock_batch_repo.session

        # Build base query with aggregations
        stmt = select(
            func.count(StockBatch.id).label("total_batches"),
            func.coalesce(func.sum(StockBatch.quantity), 0).label("total_plants"),
        )

        # Apply filters if provided
        filters = []
        if warehouse_id is not None:
            filters.append(StockBatch.warehouse_id == warehouse_id)
            logger.debug(f"Applied warehouse filter: warehouse_id={warehouse_id}")

        if product_id is not None:
            filters.append(StockBatch.product_id == product_id)
            logger.debug(f"Applied product filter: product_id={product_id}")

        if filters:
            stmt = stmt.where(*filters)

        # Execute query
        try:
            result = await session.execute(stmt)
            row = result.one()

            total_batches = row.total_batches or 0
            total_plants = row.total_plants or 0

            logger.info(
                "Inventory report generated successfully",
                extra={
                    "total_batches": total_batches,
                    "total_plants": total_plants,
                    "warehouse_id": warehouse_id,
                    "product_id": product_id,
                },
            )

            # Return Pydantic schema (not SQLAlchemy model)
            return InventoryReportResponse(
                total_batches=total_batches,
                total_plants=total_plants,
                warehouse_id=warehouse_id,
                product_id=product_id,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                "Failed to generate inventory report",
                extra={"warehouse_id": warehouse_id, "product_id": product_id, "error": str(e)},
                exc_info=True,
            )
            raise
