"""
Analytics Service - Business Logic for Inventory Analytics

This service provides business intelligence and reporting capabilities
for inventory management, including aggregated stock reports and metrics.

Architecture: Service Layer (uses Service→Service pattern for dependencies)
"""

import csv
import io
import json
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_batch import StockBatch
from app.models.stock_movement import StockMovement
from app.schemas.analytics_schema import (
    AnalyticsAIQueryRequest,
    AnalyticsAIQueryResponse,
    AnalyticsFilterOptionsResponse,
    AnalyticsManualQueryRequest,
    AnalyticsManualQueryResponse,
    DailyPlantCountResponse,
    DataExportResponse,
    InventoryReportResponse,
    LargeExportRequest,
    SalesComparisonRequest,
    SalesComparisonResponse,
)
from app.services.product_category_service import ProductCategoryService
from app.services.product_service import ProductService
from app.services.stock_batch_service import StockBatchService
from app.services.stock_movement_service import StockMovementService
from app.services.warehouse_service import WarehouseService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for inventory analytics and reporting.

    This service aggregates stock data to provide business insights
    about inventory levels, distribution, and trends.

    Architecture Pattern:
    - Uses Service→Service pattern (StockBatchService, StockMovementService)
    - Returns Pydantic schemas (not SQLAlchemy models)
    - All methods are async
    - Comprehensive logging for audit trails
    """

    def __init__(
        self,
        stock_batch_service: StockBatchService,
        stock_movement_service: StockMovementService,
        warehouse_service: WarehouseService,
        product_category_service: ProductCategoryService,
        product_service: ProductService,
    ):
        """
        Initialize AnalyticsService with required dependencies.

        Args:
            stock_batch_service: Service for stock batch operations
            stock_movement_service: Service for stock movement operations
        """
        self.stock_batch_service = stock_batch_service
        self.stock_movement_service = stock_movement_service
        self.warehouse_service = warehouse_service
        self.product_category_service = product_category_service
        self.product_service = product_service
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
            >>> # Total plants: {report.total_plants}

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

        # Access database session through repository within service
        session: AsyncSession = self.stock_batch_service.batch_repo.session

        # Build base query with aggregations
        stmt = select(
            func.count(StockBatch.id).label("total_batches"),
            func.coalesce(func.sum(StockBatch.quantity_current), 0).label("total_plants"),
        )

        # Apply filters if provided
        if warehouse_id is not None:
            # StockBatch → current_storage_bin → storage_location → storage_area → warehouse
            from app.models.storage_area import StorageArea
            from app.models.storage_bin import StorageBin
            from app.models.storage_location import StorageLocation
            from app.models.warehouse import Warehouse

            stmt = (
                stmt.join(StockBatch.current_storage_bin)
                .join(StorageBin.storage_location)
                .join(StorageLocation.storage_area)
                .join(StorageArea.warehouse)
                .where(Warehouse.warehouse_id == warehouse_id)
            )
            logger.debug(f"Applied warehouse filter: warehouse_id={warehouse_id}")

        if product_id is not None:
            stmt = stmt.where(StockBatch.product_id == product_id)
            logger.debug(f"Applied product filter: product_id={product_id}")

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

    async def get_daily_plant_counts(
        self,
        start_date: date,
        end_date: date,
        location_id: int | None = None,
        product_id: int | None = None,
    ) -> list[DailyPlantCountResponse]:
        """Get daily plant count aggregations over a date range."""
        logger.info(
            "Generating daily plant counts",
            extra={
                "start_date": start_date,
                "end_date": end_date,
                "location_id": location_id,
                "product_id": product_id,
            },
        )

        session: AsyncSession = self.stock_movement_service.movement_repo.session
        results = []

        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)

            stmt_in = select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
                and_(
                    StockMovement.created_at >= current_date,
                    StockMovement.created_at < next_date,
                    StockMovement.is_inbound == True,  # noqa: E712
                )
            )

            stmt_out = select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(
                and_(
                    StockMovement.created_at >= current_date,
                    StockMovement.created_at < next_date,
                    StockMovement.is_inbound == False,  # noqa: E712
                )
            )

            if location_id:
                # StockMovement uses bin_id, need to join to get location_id
                from app.models.storage_bin import StorageBin

                stmt_in = stmt_in.join(
                    StorageBin, StockMovement.destination_bin_id == StorageBin.bin_id
                ).where(StorageBin.storage_location_id == location_id)

                stmt_out = stmt_out.join(
                    StorageBin, StockMovement.source_bin_id == StorageBin.bin_id
                ).where(StorageBin.storage_location_id == location_id)

            try:
                result_in = await session.execute(stmt_in)
                result_out = await session.execute(stmt_out)

                movements_in = result_in.scalar() or 0
                movements_out = result_out.scalar() or 0
                net_change = movements_in - movements_out

                stmt_total = select(func.coalesce(func.sum(StockBatch.quantity_current), 0))
                if location_id:
                    # StockBatch → current_storage_bin → storage_location
                    from app.models.storage_bin import StorageBin

                    stmt_total = stmt_total.join(
                        StorageBin, StockBatch.current_storage_bin_id == StorageBin.bin_id
                    ).where(StorageBin.storage_location_id == location_id)
                if product_id:
                    stmt_total = stmt_total.where(StockBatch.product_id == product_id)

                result_total = await session.execute(stmt_total)
                total_plants = result_total.scalar() or 0

                results.append(
                    DailyPlantCountResponse(
                        date=current_date,
                        total_plants=total_plants,
                        movements_in=movements_in,
                        movements_out=movements_out,
                        net_change=net_change,
                    )
                )
            except Exception as e:
                logger.error(
                    f"Failed to get counts for {current_date}",
                    extra={"date": current_date, "error": str(e)},
                    exc_info=True,
                )

            current_date = next_date

        logger.info(f"Generated {len(results)} daily count records")
        return results

    async def export_data(
        self, export_format: str = "csv", warehouse_id: int | None = None
    ) -> DataExportResponse:
        """Export inventory data in specified format."""
        logger.info("Exporting data", extra={"format": export_format, "warehouse_id": warehouse_id})

        session: AsyncSession = self.stock_batch_service.batch_repo.session

        stmt = select(StockBatch)
        if warehouse_id:
            # StockBatch → current_storage_bin → storage_location → storage_area → warehouse
            from app.models.storage_area import StorageArea
            from app.models.storage_bin import StorageBin
            from app.models.storage_location import StorageLocation
            from app.models.warehouse import Warehouse

            stmt = (
                stmt.join(StockBatch.current_storage_bin)
                .join(StorageBin.storage_location)
                .join(StorageLocation.storage_area)
                .join(StorageArea.warehouse)
                .where(Warehouse.warehouse_id == warehouse_id)
            )

        try:
            result = await session.execute(stmt)
            batches = result.scalars().all()

            if export_format == "csv":
                output = io.StringIO()
                writer = csv.DictWriter(
                    output,
                    fieldnames=[
                        "id",
                        "batch_code",
                        "warehouse_id",
                        "product_id",
                        "quantity",
                        "created_at",
                    ],
                )
                writer.writeheader()
                for batch in batches:
                    writer.writerow(
                        {
                            "id": batch.id,
                            "batch_code": batch.batch_code,
                            "warehouse_id": batch.current_storage_bin.storage_location.storage_area.warehouse_id,
                            "product_id": batch.product_id,
                            "quantity": batch.quantity_current,
                            "created_at": batch.created_at.isoformat()
                            if batch.created_at
                            else None,
                        }
                    )
                data = output.getvalue()
                file_size = len(data.encode("utf-8"))

            elif export_format == "json":
                data_list = [
                    {
                        "id": batch.id,
                        "batch_code": batch.batch_code,
                        "warehouse_id": batch.current_storage_bin.storage_location.storage_area.warehouse_id,
                        "product_id": batch.product_id,
                        "quantity": batch.quantity_current,
                        "created_at": batch.created_at.isoformat() if batch.created_at else None,
                    }
                    for batch in batches
                ]
                data = json.dumps(data_list, indent=2)
                file_size = len(data.encode("utf-8"))

            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            logger.info(
                "Data export completed",
                extra={"format": export_format, "record_count": len(batches), "size": file_size},
            )

            return DataExportResponse(
                export_format=export_format,
                file_url=None,
                file_size=file_size,
                record_count=len(batches),
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(
                "Failed to export data",
                extra={"format": export_format, "warehouse_id": warehouse_id, "error": str(e)},
                exc_info=True,
            )
            raise

    async def get_filter_options(self) -> AnalyticsFilterOptionsResponse:
        warehouses = await self.warehouse_service.get_active_warehouses(include_areas=False)
        categories = await self.product_category_service.get_all_categories()
        products = await self.product_service.get_all_products()

        return AnalyticsFilterOptionsResponse(
            warehouses=[{"id": w.warehouse_id, "name": w.name} for w in warehouses],
            product_categories=[{"id": c.category_id, "name": c.name} for c in categories],
            products=[{"id": p.product_id, "name": p.common_name} for p in products],
        )

    async def run_manual_query(
        self, request: AnalyticsManualQueryRequest
    ) -> AnalyticsManualQueryResponse:
        batches = await self.stock_batch_service.batch_repo.get_multi(limit=1000)
        aggregated: dict[int, int] = {}
        for batch in batches:
            product_id = int(batch.product_id)
            aggregated[product_id] = aggregated.get(product_id, 0) + int(
                batch.quantity_current or 0
            )

        rows = [{"product_id": pid, "total_quantity": qty} for pid, qty in aggregated.items()]
        metadata = {"row_count": len(rows), "analysis_type": request.analysis_type}

        return AnalyticsManualQueryResponse(data=rows, metadata=metadata)

    async def run_ai_query(self, request: AnalyticsAIQueryRequest) -> AnalyticsAIQueryResponse:
        batches = await self.stock_batch_service.batch_repo.get_multi(limit=200)
        total = sum(int(b.quantity_current or 0) for b in batches)
        answer = (
            f"Total current quantity across sampled batches is {total}. Prompt: {request.prompt}"
        )
        return AnalyticsAIQueryResponse(answer=answer, suggested_visualizations=["bar", "table"])

    async def compare_sales_vs_stock(
        self, request: SalesComparisonRequest
    ) -> SalesComparisonResponse:
        movements = await self.stock_movement_service.get_multi(limit=300)
        total_sales = sum(int(m.quantity or 0) for m in movements if m.movement_type == "ventas")
        total_stock = sum(int(m.quantity or 0) for m in movements if m.movement_type != "ventas")

        items = [
            {"metric": "sales", "value": total_sales},
            {"metric": "stock", "value": total_stock},
        ]
        summary = {"net": total_stock - total_sales}
        return SalesComparisonResponse(items=items, summary=summary)

    async def export_large_dataset(self, request: LargeExportRequest) -> DataExportResponse:
        batches = await self.stock_batch_service.batch_repo.get_multi(limit=1000)
        return DataExportResponse(
            export_format=request.export_format,
            file_url=None,
            file_size=None,
            record_count=len(batches),
            generated_at=datetime.utcnow(),
        )
