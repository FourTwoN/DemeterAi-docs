"""Stock Management API Controllers.

This module provides HTTP endpoints for stock operations:
- Photo-based stock initialization (ML pipeline)
- Manual stock initialization
- Stock movements (plantado, muerte, trasplante, ventas)
- Batch tracking and history

Architecture:
    Layer: Controller Layer (HTTP only)
    Dependencies: Service layer only (NO business logic here)
    Pattern: Thin controllers - delegate to services

Endpoints:
    POST /api/v1/stock/photo - Upload photo for ML processing (C001)
    POST /api/v1/stock/manual - Manual stock initialization (C002)
    GET /api/v1/stock/tasks/{task_id} - Celery task status (C003)
    POST /api/v1/stock/movements - Create stock movement (C004)
    GET /api/v1/stock/batches - List stock batches (C005)
    GET /api/v1/stock/batches/{id} - Get batch details (C006)
    GET /api/v1/stock/history - Transaction history (C007)
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.photo_schema import PhotoUploadResponse
from app.schemas.stock_batch_schema import StockBatchResponse
from app.schemas.stock_movement_schema import (
    ManualStockInitRequest,
    StockMovementCreateRequest,
    StockMovementResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])


# =============================================================================
# Dependency Injection Helpers
# =============================================================================


def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
    """Dependency injection for ServiceFactory."""
    return ServiceFactory(session)


# =============================================================================
# API Endpoints
# =============================================================================


@router.post(
    "/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload photo for ML processing",
)
async def upload_photo_for_stock_count(
    file: Annotated[UploadFile, File(description="Photo file (max 20MB, JPEG/PNG/WEBP)")],
    longitude: Annotated[float, Form(description="GPS longitude coordinate")],
    latitude: Annotated[float, Form(description="GPS latitude coordinate")],
    user_id: Annotated[int, Form(description="User ID for tracking")],
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoUploadResponse:
    """Upload photo for ML-powered stock counting (C001).

  Complete workflow:
  1. Validate file (type, size)
  2. GPS-based location lookup
  3. Upload to S3
  4. Create processing session
  5. Dispatch ML pipeline (Celery)

  Args:
      file: Photo file (JPEG/PNG/WEBP, max 20MB)
      longitude: GPS longitude coordinate
      latitude: GPS latitude coordinate
      user_id: User ID for audit trail

  Returns:
      PhotoUploadResponse with task_id for polling

  Raises:
      HTTPException 400: Invalid file type/size
      HTTPException 404: GPS location not found
      HTTPException 500: Upload/processing error

  Example:
      ```bash
      curl -X POST "http://localhost:8000/api/v1/stock/photo" \\
        -H "Content-Type: multipart/form-data" \\
        -F "file=@photo.jpg" \\
        -F "longitude=10.5" \\
        -F "latitude=20.5" \\
        -F "user_id=1"
      ```
  """
    try:
        logger.info(
            "Photo upload request received",
            extra={
                "filename": file.filename,
                "content_type": file.content_type,
                "longitude": longitude,
                "latitude": latitude,
                "user_id": user_id,
            },
        )

        service = factory.get_photo_upload_service()
        result = await service.upload_photo(file, longitude, latitude, user_id)

        logger.info(
            "Photo upload successful",
            extra={
                "task_id": str(result.task_id),
                "session_id": result.session_id,
                "status": result.status,
            },
        )

        return result

    except ValidationException as e:
        logger.warning("Photo upload validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except ResourceNotFoundException as e:
        logger.warning("GPS location not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    except Exception as e:
        logger.error("Photo upload failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Photo upload failed. Please try again.",
        ) from e


@router.post(
    "/manual",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manual stock initialization",
)
async def create_manual_stock_initialization(
    request: ManualStockInitRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> StockMovementResponse:
    """Create manual stock initialization without photo/ML (C002).

    Business rules:
    1. Location must have configuration
    2. Product must match configured product
    3. Packaging must match configured packaging
    4. Quantity must be > 0

    Args:
        request: Manual stock initialization request

    Returns:
        StockMovementResponse with created movement

    Raises:
        HTTPException 400: Validation error (product mismatch, etc.)
        HTTPException 404: Location configuration not found
        HTTPException 500: Database error

    Example:
        ```json
        {
          "storage_location_id": 1,
          "product_id": 10,
          "packaging_catalog_id": 5,
          "product_size_id": 2,
          "quantity": 100,
          "planting_date": "2025-10-01",
          "notes": "Initial inventory count"
        }
        ```
    """
    try:
        logger.info(
            "Manual stock initialization request",
            extra={
                "storage_location_id": request.storage_location_id,
                "product_id": request.product_id,
                "quantity": request.quantity,
            },
        )

        # BatchLifecycleService will handle validation and creation
        service = factory.get_batch_lifecycle_service()
        result = await service.create_manual_initialization(request)  # type: ignore[attr-defined]

        logger.info(
            "Manual stock initialization successful",
            extra={
                "movement_id": str(result.movement_id),
                "batch_id": result.batch_id,
            },
        )

        return result  # type: ignore[no-any-return]

    except ValidationException as e:
        logger.warning("Manual stock validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except ResourceNotFoundException as e:
        logger.warning("Location config not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    except Exception as e:
        logger.error("Manual stock initialization failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Manual stock initialization failed.",
        ) from e


@router.get(
    "/tasks/{task_id}",
    response_model=dict[str, object],
    summary="Get Celery task status",
)
async def get_celery_task_status(
    task_id: UUID,
) -> dict[str, object]:
    """Get Celery task status for photo processing (C003).

    Args:
        task_id: Celery task UUID

    Returns:
        Task status information

    Example:
        ```json
        {
          "task_id": "550e8400-e29b-41d4-a716-446655440000",
          "status": "SUCCESS",
          "result": {
            "detections": 150,
            "estimations": 142,
            "confidence": 0.92
          }
        }
        ```

    Note:
        This endpoint requires Celery integration (CEL005).
        Currently returns placeholder response.
    """
    try:
        from app.celery_app import app as celery_app

        logger.info("Getting task status", extra={"task_id": str(task_id)})

        task_result = celery_app.AsyncResult(str(task_id))

        return {
            "task_id": str(task_id),
            "status": task_result.state,
            "result": task_result.result if task_result.ready() else None,
            "info": task_result.info if hasattr(task_result, "info") else None,
        }

    except Exception as e:
        logger.error("Task status lookup failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task status lookup failed.",
        ) from e


@router.post(
    "/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create stock movement",
)
async def create_stock_movement(
    request: StockMovementCreateRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> StockMovementResponse:
    """Create stock movement (plantado, muerte, trasplante, ventas) (C004).

    Args:
        request: Stock movement request

    Returns:
        StockMovementResponse with created movement

    Raises:
        HTTPException 400: Validation error
        HTTPException 404: Batch not found
        HTTPException 500: Database error

    Example:
        ```json
        {
          "batch_id": 5,
          "movement_type": "muerte",
          "quantity": -10,
          "user_id": 1,
          "is_inbound": false,
          "reason_description": "Plant disease"
        }
        ```
    """
    try:
        logger.info(
            "Stock movement request",
            extra={
                "batch_id": request.batch_id,
                "movement_type": request.movement_type,
                "quantity": request.quantity,
            },
        )

        service = factory.get_stock_movement_service()
        result = await service.create_stock_movement(request)

        logger.info(
            "Stock movement created",
            extra={
                "movement_id": str(result.movement_id),
                "batch_id": result.batch_id,
            },
        )

        return result

    except ValidationException as e:
        logger.warning("Stock movement validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except ResourceNotFoundException as e:
        logger.warning("Batch not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    except Exception as e:
        logger.error("Stock movement creation failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stock movement creation failed.",
        ) from e


@router.get(
    "/batches",
    response_model=list[StockBatchResponse],
    summary="List stock batches",
)
async def list_stock_batches(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    factory: ServiceFactory = Depends(get_factory),
) -> list[StockBatchResponse]:
    """List stock batches with pagination (C005).

    Args:
        skip: Offset (default 0)
        limit: Max results (default 100, max 1000)

    Returns:
        List of StockBatchResponse

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/stock/batches?skip=0&limit=50"
        ```
    """
    try:
        logger.info("Listing stock batches", extra={"skip": skip, "limit": limit})

        batch_service = factory.get_stock_batch_service()
        batches = await batch_service.get_multi(skip=skip, limit=limit)
        return batches

    except Exception as e:
        logger.error("Failed to list batches", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list batches.",
        ) from e


@router.get(
    "/batches/{batch_id}",
    response_model=StockBatchResponse,
    summary="Get batch details",
)
async def get_batch_details(
    batch_id: int,
    factory: ServiceFactory = Depends(get_factory),
) -> StockBatchResponse:
    """Get stock batch details by ID (C006).

    Args:
        batch_id: Stock batch ID

    Returns:
        StockBatchResponse with batch details

    Raises:
        HTTPException 404: Batch not found

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/stock/batches/5"
        ```
    """
    try:
        logger.info("Getting batch details", extra={"batch_id": batch_id})

        batch_service = factory.get_stock_batch_service()
        batch = await batch_service.get_by_id(batch_id)
        return batch

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    except Exception as e:
        logger.error("Failed to get batch", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get batch details.",
        ) from e


@router.get(
    "/history",
    response_model=list[StockMovementResponse],
    summary="Get transaction history",
)
async def get_stock_movement_history(
    batch_id: int | None = Query(None, description="Filter by batch ID"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    factory: ServiceFactory = Depends(get_factory),
) -> list[StockMovementResponse]:
    """Get stock movement transaction history (C007).

    Args:
        batch_id: Optional batch ID filter
        skip: Offset (default 0)
        limit: Max results (default 100, max 1000)

    Returns:
        List of StockMovementResponse

    Example:
        ```bash
        # All movements
        curl "http://localhost:8000/api/v1/stock/history?skip=0&limit=50"

        # Filter by batch
        curl "http://localhost:8000/api/v1/stock/history?batch_id=5"
        ```
    """
    try:
        logger.info(
            "Getting movement history",
            extra={"batch_id": batch_id, "skip": skip, "limit": limit},
        )

        service = factory.get_stock_movement_service()
        if batch_id:
            movements = await service.get_movements_by_batch(batch_id)
        else:
            movements = await service.get_multi(skip=skip, limit=limit)

        return movements

    except Exception as e:
        logger.error("Failed to get movement history", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get movement history.",
        ) from e
