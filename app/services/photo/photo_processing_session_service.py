"""Photo Processing Session Service - Business logic for ML photo session lifecycle.

This service handles all photo processing session operations including:
- Session CRUD operations
- Status transition validation
- Query by location/date range
- Session completion with ML results

Architecture:
    Layer: Service Layer (Business Logic)
    Dependencies: PhotoProcessingSessionRepository (own repo)
    Pattern: Clean Architecture - Service layer enforces business rules

Critical Rules:
    - Service→Service pattern enforced (NO direct repository access except own)
    - Status transitions validated (pending → processing → completed/failed)
    - All database operations are async
    - Type hints on all methods
    - Business exceptions for validation failures
"""

from datetime import datetime
from uuid import UUID

from app.core.exceptions import (
    InvalidStatusTransitionException,
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.models.photo_processing_session import ProcessingSessionStatusEnum
from app.repositories.photo_processing_session_repository import (
    PhotoProcessingSessionRepository,
)
from app.schemas.photo_processing_session_schema import (
    PhotoProcessingSessionCreate,
    PhotoProcessingSessionResponse,
    PhotoProcessingSessionUpdate,
)

logger = get_logger(__name__)


class PhotoProcessingSessionService:
    """Service for managing photo processing sessions.

    This service provides business logic for photo processing session lifecycle
    including creation, status transitions, and completion handling.

    Key Features:
        - Session CRUD with validation
        - Status transition validation (pending → processing → completed/failed)
        - Query by location/date range
        - Session completion with ML results
        - Business rule enforcement

    Attributes:
        repo: PhotoProcessingSessionRepository for database operations
    """

    # Valid status transitions
    VALID_TRANSITIONS = {
        ProcessingSessionStatusEnum.PENDING: {
            ProcessingSessionStatusEnum.PROCESSING,
            ProcessingSessionStatusEnum.FAILED,
        },
        ProcessingSessionStatusEnum.PROCESSING: {
            ProcessingSessionStatusEnum.COMPLETED,
            ProcessingSessionStatusEnum.FAILED,
        },
        ProcessingSessionStatusEnum.COMPLETED: set(),  # Terminal state
        ProcessingSessionStatusEnum.FAILED: set(),  # Terminal state
    }

    def __init__(self, repo: PhotoProcessingSessionRepository) -> None:
        """Initialize PhotoProcessingSessionService with repository.

        Args:
            repo: PhotoProcessingSessionRepository for database operations
        """
        self.repo = repo

    async def create_session(
        self, request: PhotoProcessingSessionCreate
    ) -> PhotoProcessingSessionResponse:
        """Create new photo processing session.

        Args:
            request: Session creation data with storage_location_id, original_image_id

        Returns:
            PhotoProcessingSessionResponse with created session

        Raises:
            ValidationException: If session data is invalid

        Business Rules:
            - status defaults to PENDING
            - session_id is auto-generated UUID
            - total_detected, total_estimated default to 0
            - category_counts, manual_adjustments default to {}
        """
        logger.info(
            "Creating photo processing session",
            extra={
                "storage_location_id": request.storage_location_id,
                "status": request.status or ProcessingSessionStatusEnum.PENDING.value,
            },
        )

        # Create session via repository
        session_data = request.model_dump()
        session = await self.repo.create(session_data)

        logger.info(
            "Photo processing session created successfully",
            extra={"session_id": str(session.session_id), "id": session.id},
        )

        return PhotoProcessingSessionResponse.model_validate(session)

    async def get_session_by_id(self, session_id: int) -> PhotoProcessingSessionResponse | None:
        """Get photo processing session by ID.

        Args:
            session_id: Session database ID

        Returns:
            PhotoProcessingSessionResponse if found, None otherwise
        """
        session = await self.repo.get(session_id)
        if not session:
            return None

        return PhotoProcessingSessionResponse.model_validate(session)

    async def get_session_by_uuid(
        self, session_uuid: UUID
    ) -> PhotoProcessingSessionResponse | None:
        """Get photo processing session by UUID.

        Args:
            session_uuid: Session UUID identifier

        Returns:
            PhotoProcessingSessionResponse if found, None otherwise
        """
        session = await self.repo.get_by_session_id(session_uuid)
        if not session:
            return None

        return PhotoProcessingSessionResponse.model_validate(session)

    async def update_session(
        self, session_id: int, request: PhotoProcessingSessionUpdate
    ) -> PhotoProcessingSessionResponse:
        """Update photo processing session.

        Args:
            session_id: Session database ID
            request: Session update data

        Returns:
            PhotoProcessingSessionResponse with updated session

        Raises:
            ResourceNotFoundException: If session not found
            InvalidStatusTransitionException: If status transition is invalid
        """
        # Get existing session
        existing = await self.repo.get(session_id)
        if not existing:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
            )

        # Validate status transition if status is being updated
        if request.status is not None:
            self._validate_status_transition(existing.status, request.status)

        # Update session
        update_data = request.model_dump(exclude_unset=True)
        updated = await self.repo.update(session_id, update_data)

        logger.info(
            "Photo processing session updated",
            extra={"session_id": str(updated.session_id), "updates": list(update_data.keys())},
        )

        return PhotoProcessingSessionResponse.model_validate(updated)

    async def mark_session_processing(
        self, session_id: int, celery_task_id: str
    ) -> PhotoProcessingSessionResponse:
        """Mark session as processing (called when ML pipeline starts).

        Args:
            session_id: Session database ID
            celery_task_id: Celery task ID for tracking

        Returns:
            PhotoProcessingSessionResponse with updated session

        Raises:
            ResourceNotFoundException: If session not found
            InvalidStatusTransitionException: If not in PENDING status

        Business Rules:
            - Session must be in PENDING status
            - Transitions to PROCESSING status
            - Stores celery_task_id for tracking
        """
        existing = await self.repo.get(session_id)
        if not existing:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
            )

        # Validate status is PENDING
        if existing.status != ProcessingSessionStatusEnum.PENDING:
            raise InvalidStatusTransitionException(
                current=existing.status.value,
                target=ProcessingSessionStatusEnum.PROCESSING.value,
                reason="Session must be PENDING to start processing",
            )

        # Update to PROCESSING
        updated = await self.repo.update(
            session_id,
            {
                "status": ProcessingSessionStatusEnum.PROCESSING,
            },
        )

        logger.info(
            "Session marked as processing",
            extra={
                "session_id": str(updated.session_id),
                "celery_task_id": celery_task_id,
            },
        )

        return PhotoProcessingSessionResponse.model_validate(updated)

    async def mark_session_completed(
        self,
        session_id: int,
        total_detected: int,
        total_estimated: int,
        total_empty_containers: int,
        avg_confidence: float,
        category_counts: dict,
        processed_image_id: UUID,
    ) -> PhotoProcessingSessionResponse:
        """Mark session as completed with ML results.

        Args:
            session_id: Session database ID
            total_detected: Total detections count
            total_estimated: Total estimations count
            total_empty_containers: Empty container count
            avg_confidence: Average ML confidence score
            category_counts: Detection counts by category
            processed_image_id: S3 image ID for processed/visualization image

        Returns:
            PhotoProcessingSessionResponse with updated session

        Raises:
            ResourceNotFoundException: If session not found
            InvalidStatusTransitionException: If not in PROCESSING status
            ValidationException: If confidence is invalid

        Business Rules:
            - Session must be in PROCESSING status
            - avg_confidence must be 0.0-1.0
            - total_detected, total_estimated, total_empty_containers must be ≥0
        """
        existing = await self.repo.get(session_id)
        if not existing:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
            )

        # Validate status is PROCESSING
        if existing.status != ProcessingSessionStatusEnum.PROCESSING:
            raise InvalidStatusTransitionException(
                current=existing.status.value,
                target=ProcessingSessionStatusEnum.COMPLETED.value,
                reason="Session must be PROCESSING to mark as completed",
            )

        # Validate avg_confidence
        if not (0.0 <= avg_confidence <= 1.0):
            raise ValidationException(
                field="avg_confidence",
                message=f"avg_confidence must be 0.0-1.0, got {avg_confidence}",
            )

        # Validate counts
        if total_detected < 0:
            raise ValidationException(
                field="total_detected",
                message=f"total_detected must be ≥0, got {total_detected}",
            )
        if total_estimated < 0:
            raise ValidationException(
                field="total_estimated",
                message=f"total_estimated must be ≥0, got {total_estimated}",
            )
        if total_empty_containers < 0:
            raise ValidationException(
                field="total_empty_containers",
                message=f"total_empty_containers must be ≥0, got {total_empty_containers}",
            )

        # Update to COMPLETED with results
        updated = await self.repo.update(
            session_id,
            {
                "status": ProcessingSessionStatusEnum.COMPLETED,
                "total_detected": total_detected,
                "total_estimated": total_estimated,
                "total_empty_containers": total_empty_containers,
                "avg_confidence": avg_confidence,
                "category_counts": category_counts,
                "processed_image_id": processed_image_id,
            },
        )

        logger.info(
            "Session marked as completed",
            extra={
                "session_id": str(updated.session_id),
                "total_detected": total_detected,
                "total_estimated": total_estimated,
                "avg_confidence": avg_confidence,
            },
        )

        return PhotoProcessingSessionResponse.model_validate(updated)

    async def mark_session_failed(
        self, session_id: int, error_message: str
    ) -> PhotoProcessingSessionResponse:
        """Mark session as failed with error message.

        Args:
            session_id: Session database ID
            error_message: Error description

        Returns:
            PhotoProcessingSessionResponse with updated session

        Raises:
            ResourceNotFoundException: If session not found

        Business Rules:
            - Can transition from PENDING or PROCESSING
            - Stores error_message for debugging
        """
        existing = await self.repo.get(session_id)
        if not existing:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
            )

        # Update to FAILED
        updated = await self.repo.update(
            session_id,
            {
                "status": ProcessingSessionStatusEnum.FAILED,
                "error_message": error_message,
            },
        )

        logger.warning(
            "Session marked as failed",
            extra={
                "session_id": str(updated.session_id),
                "error_message": error_message,
            },
        )

        return PhotoProcessingSessionResponse.model_validate(updated)

    async def get_sessions_by_location(
        self, storage_location_id: int, limit: int = 50
    ) -> list[PhotoProcessingSessionResponse]:
        """Get sessions for a storage location.

        Args:
            storage_location_id: Storage location ID
            limit: Max results (default 50)

        Returns:
            List of PhotoProcessingSessionResponse ordered by created_at DESC
        """
        sessions = await self.repo.get_by_storage_location(storage_location_id, limit=limit)
        return [PhotoProcessingSessionResponse.model_validate(s) for s in sessions]

    async def get_sessions_by_status(
        self, status: ProcessingSessionStatusEnum, limit: int = 100
    ) -> list[PhotoProcessingSessionResponse]:
        """Get sessions by status.

        Args:
            status: Processing status to filter by
            limit: Max results (default 100)

        Returns:
            List of PhotoProcessingSessionResponse ordered by created_at DESC
        """
        sessions = await self.repo.get_by_status(status, limit=limit)
        return [PhotoProcessingSessionResponse.model_validate(s) for s in sessions]

    async def get_sessions_by_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 100
    ) -> list[PhotoProcessingSessionResponse]:
        """Get sessions within date range.

        Args:
            start_date: Start datetime (inclusive)
            end_date: End datetime (inclusive)
            limit: Max results (default 100)

        Returns:
            List of PhotoProcessingSessionResponse ordered by created_at DESC
        """
        sessions = await self.repo.get_by_date_range(start_date, end_date, limit=limit)
        return [PhotoProcessingSessionResponse.model_validate(s) for s in sessions]

    def _validate_status_transition(
        self,
        current_status: ProcessingSessionStatusEnum,
        target_status: ProcessingSessionStatusEnum,
    ) -> None:
        """Validate status transition is allowed.

        Args:
            current_status: Current session status
            target_status: Target session status

        Raises:
            InvalidStatusTransitionException: If transition is invalid

        Business Rules:
            - PENDING → PROCESSING, FAILED
            - PROCESSING → COMPLETED, FAILED
            - COMPLETED → (terminal state, no transitions)
            - FAILED → (terminal state, no transitions)
        """
        # Convert to enum if string
        if isinstance(current_status, str):
            current_status = ProcessingSessionStatusEnum(current_status)
        if isinstance(target_status, str):
            target_status = ProcessingSessionStatusEnum(target_status)

        # Check if transition is valid
        valid_targets = self.VALID_TRANSITIONS.get(current_status, set())
        if target_status not in valid_targets:
            raise InvalidStatusTransitionException(
                current=current_status.value,
                target=target_status.value,
                reason=f"Cannot transition from {current_status.value} to {target_status.value}",
            )
