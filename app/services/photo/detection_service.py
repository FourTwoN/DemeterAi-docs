"""Detection Service - Business logic for ML detection results.

This service handles all detection operations including:
- Bulk creating detections from ML results
- Bounding box validation
- Linking detections to sessions
- Detection statistics

Architecture:
    Layer: Service Layer (Business Logic)
    Dependencies: DetectionRepository (own repo), PhotoProcessingSessionService
    Pattern: Clean Architecture - Service→Service communication

Critical Rules:
    - Service→Service pattern enforced (calls PhotoProcessingSessionService)
    - Bounding box validation (0-1 range, xmin < xmax, ymin < ymax)
    - Bulk insert for performance (1000+ detections per photo)
    - All database operations are async
"""

from app.core.exceptions import (
    ValidationException,
)
from app.core.logging import get_logger
from app.repositories.detection_repository import DetectionRepository
from app.schemas.detection_schema import (
    DetectionBulkCreateRequest,
    DetectionCreate,
    DetectionResponse,
    DetectionStatistics,
)

logger = get_logger(__name__)


class DetectionService:
    """Service for managing ML detection results.

    This service provides business logic for detection operations including
    bulk creation from ML results, validation, and statistics.

    Key Features:
        - Bulk insert detections (performance optimized)
        - Bounding box validation (coordinates, dimensions)
        - Detection statistics (count, avg confidence)
        - Query by session

    Attributes:
        repo: DetectionRepository for database operations
    """

    def __init__(self, repo: DetectionRepository) -> None:
        """Initialize DetectionService with repository.

        Args:
            repo: DetectionRepository for database operations
        """
        self.repo = repo

    async def create_detection(self, request: DetectionCreate) -> DetectionResponse:
        """Create single detection.

        Args:
            request: Detection creation data

        Returns:
            DetectionResponse with created detection

        Raises:
            ValidationException: If detection data is invalid

        Business Rules:
            - Bounding box coordinates must be valid
            - detection_confidence must be 0.0-1.0
            - width_px and height_px must be > 0
        """
        # Validate bounding box
        self._validate_bounding_box(request.bbox_coordinates)

        # Validate dimensions
        if request.width_px <= 0:
            raise ValidationException(
                field="width_px",
                message=f"width_px must be > 0, got {request.width_px}",
            )
        if request.height_px <= 0:
            raise ValidationException(
                field="height_px",
                message=f"height_px must be > 0, got {request.height_px}",
            )

        # Validate confidence
        if not (0.0 <= request.detection_confidence <= 1.0):
            raise ValidationException(
                field="detection_confidence",
                message=f"detection_confidence must be 0.0-1.0, got {request.detection_confidence}",
            )

        # Create detection
        detection_data = request.model_dump()
        detection = await self.repo.create(detection_data)

        logger.info(
            "Detection created",
            extra={
                "detection_id": detection.id,
                "session_id": detection.session_id,
                "confidence": float(detection.detection_confidence),
            },
        )

        return DetectionResponse.model_validate(detection)

    async def bulk_create_detections(
        self, request: DetectionBulkCreateRequest
    ) -> list[DetectionResponse]:
        """Bulk create detections from ML results (optimized for performance).

        Args:
            request: Bulk creation request with list of detections

        Returns:
            List of DetectionResponse with created detections

        Raises:
            ValidationException: If any detection data is invalid

        Business Rules:
            - All detections validated before insert
            - Uses bulk_insert_mappings for performance
            - All detections for same session_id
        """
        logger.info(
            "Bulk creating detections",
            extra={
                "session_id": request.session_id,
                "count": len(request.detections),
            },
        )

        # Validate all detections first
        for idx, detection in enumerate(request.detections):
            try:
                self._validate_bounding_box(detection.bbox_coordinates)

                if detection.width_px <= 0:
                    raise ValidationException(
                        field=f"detections[{idx}].width_px",
                        message=f"width_px must be > 0, got {detection.width_px}",
                    )
                if detection.height_px <= 0:
                    raise ValidationException(
                        field=f"detections[{idx}].height_px",
                        message=f"height_px must be > 0, got {detection.height_px}",
                    )
                if not (0.0 <= detection.detection_confidence <= 1.0):
                    raise ValidationException(
                        field=f"detections[{idx}].detection_confidence",
                        message=f"detection_confidence must be 0.0-1.0, got {detection.detection_confidence}",
                    )
            except ValidationException as e:
                logger.error(
                    f"Validation failed for detection {idx}",
                    extra={"error": str(e)},
                )
                raise

        # Prepare bulk data
        detection_dicts = [
            {
                "session_id": request.session_id,
                **detection.model_dump(),
            }
            for detection in request.detections
        ]

        # Bulk insert
        created = await self.repo.bulk_create(detection_dicts)

        logger.info(
            "Bulk detections created successfully",
            extra={
                "session_id": request.session_id,
                "count": len(created),
            },
        )

        return [DetectionResponse.model_validate(d) for d in created]

    async def get_detection_by_id(self, detection_id: int) -> DetectionResponse | None:
        """Get detection by ID.

        Args:
            detection_id: Detection database ID

        Returns:
            DetectionResponse if found, None otherwise
        """
        detection = await self.repo.get(detection_id)
        if not detection:
            return None

        return DetectionResponse.model_validate(detection)

    async def get_detections_by_session(
        self, session_id: int, limit: int = 1000
    ) -> list[DetectionResponse]:
        """Get all detections for a session.

        Args:
            session_id: Photo processing session ID
            limit: Max results (default 1000)

        Returns:
            List of DetectionResponse
        """
        detections = await self.repo.get_by_session(session_id, limit=limit)
        return [DetectionResponse.model_validate(d) for d in detections]

    async def get_detection_statistics(self, session_id: int) -> DetectionStatistics:
        """Calculate detection statistics for a session.

        Args:
            session_id: Photo processing session ID

        Returns:
            DetectionStatistics with count, avg_confidence, etc.

        Business Rules:
            - Only counts live plants (is_alive=True, is_empty_container=False)
            - avg_confidence is mean of all confidences
        """
        # Get all detections for session
        detections = await self.repo.get_by_session(session_id, limit=10000)

        if not detections:
            return DetectionStatistics(
                total_count=0,
                live_count=0,
                empty_container_count=0,
                dead_count=0,
                avg_confidence=0.0,
                min_confidence=0.0,
                max_confidence=0.0,
            )

        # Calculate statistics
        total_count = len(detections)
        live_count = sum(1 for d in detections if d.is_alive and not d.is_empty_container)
        empty_container_count = sum(1 for d in detections if d.is_empty_container)
        dead_count = sum(1 for d in detections if not d.is_alive)

        confidences = [float(d.detection_confidence) for d in detections]
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)

        logger.info(
            "Detection statistics calculated",
            extra={
                "session_id": session_id,
                "total_count": total_count,
                "live_count": live_count,
                "avg_confidence": avg_confidence,
            },
        )

        return DetectionStatistics(
            total_count=total_count,
            live_count=live_count,
            empty_container_count=empty_container_count,
            dead_count=dead_count,
            avg_confidence=avg_confidence,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
        )

    def _validate_bounding_box(self, bbox: dict) -> None:
        """Validate bounding box coordinates.

        Args:
            bbox: Bounding box dict with x1, y1, x2, y2

        Raises:
            ValidationException: If bbox is invalid

        Business Rules:
            - Must have keys: x1, y1, x2, y2
            - x1 < x2 (valid width)
            - y1 < y2 (valid height)
            - All values must be numeric
        """
        required_keys = {"x1", "y1", "x2", "y2"}
        if not required_keys.issubset(bbox.keys()):
            raise ValidationException(
                field="bbox_coordinates",
                message=f"bbox must have keys {required_keys}, got {bbox.keys()}",
            )

        # Validate x1 < x2
        if bbox["x1"] >= bbox["x2"]:
            raise ValidationException(
                field="bbox_coordinates",
                message=f"x1 must be < x2 (got x1={bbox['x1']}, x2={bbox['x2']})",
            )

        # Validate y1 < y2
        if bbox["y1"] >= bbox["y2"]:
            raise ValidationException(
                field="bbox_coordinates",
                message=f"y1 must be < y2 (got y1={bbox['y1']}, y2={bbox['y2']})",
            )
