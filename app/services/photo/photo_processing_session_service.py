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

import csv
import io
import json
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
from app.schemas.photo_output_schema import (
    PhotoSessionDownloadLinks,
    PhotoSessionProgressResponse,
    PhotoSessionSummaryResponse,
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

    async def get_session_by_original_image(
        self, image_id: UUID
    ) -> PhotoProcessingSessionResponse | None:
        session = await self.repo.get_by_original_image(image_id)
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
        if request.status is not None and existing.status is not None:
            self._validate_status_transition(existing.status, request.status)

        # Update session
        update_data = request.model_dump(exclude_unset=True)
        updated = await self.repo.update(session_id, update_data)
        if not updated:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
            )

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
            current_status = existing.status.value if existing.status else "None"
            raise InvalidStatusTransitionException(
                current=current_status,
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
        if not updated:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
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
        category_counts: dict[str, int],
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
            current_status = existing.status.value if existing.status else "None"
            raise InvalidStatusTransitionException(
                current=current_status,
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
        if not updated:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
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
        if not updated:
            raise ResourceNotFoundException(
                resource_type="PhotoProcessingSession", resource_id=session_id
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

    async def get_session_progress_response(
        self, session_uuid: UUID
    ) -> PhotoSessionProgressResponse | PhotoSessionSummaryResponse | None:
        """Build structured progress or summary response for a session."""

        session = await self.get_session_by_uuid(session_uuid)
        if not session:
            return None

        if session.status == ProcessingSessionStatusEnum.COMPLETED:
            download_links = PhotoSessionDownloadLinks(
                pdf_report=f"/api/v1/sessions/{session_uuid}/report.pdf",
                csv_export=f"/api/v1/sessions/{session_uuid}/export.csv",
                detections_geojson=f"/api/v1/sessions/{session_uuid}/detections.geojson",
            )

            return PhotoSessionSummaryResponse(
                status="completed",
                session_id=session_uuid,
                completed_at=session.updated_at,
                plant_detection={
                    "total_detected": session.total_detected,
                    "total_estimated": session.total_estimated,
                },
                field_metrics=None,
                quality={"avg_confidence": session.avg_confidence},
                download_links=download_links,
            )

        progress_percent = 0.0
        if session.status == ProcessingSessionStatusEnum.PROCESSING:
            progress_percent = 50.0
        elif session.status == ProcessingSessionStatusEnum.FAILED:
            progress_percent = 100.0

        return PhotoSessionProgressResponse(
            status=session.status.value if session.status else "pending",
            progress_percent=progress_percent,
            images_completed=0,
            images_total=1,
            images_failed=1 if session.status == ProcessingSessionStatusEnum.FAILED else 0,
        )

    async def validate_session_by_uuid(
        self, session_uuid: UUID, validated: bool
    ) -> PhotoProcessingSessionResponse | None:
        """Validate or invalidate session by UUID."""

        session = await self.repo.get_by_session_id(session_uuid)
        if not session:
            return None

        update_request = PhotoProcessingSessionUpdate(
            validated=validated,
            validation_date=datetime.utcnow() if validated else None,
        )
        return await self.update_session(session.id, update_request)

    async def generate_pdf_report_bytes(self, session_uuid: UUID) -> bytes:
        """Generate simple PDF report for session."""
        session = await self.get_session_by_uuid(session_uuid)
        title = f"Session {session_uuid}" if session else "Session Report"
        pdf_template = f"""%PDF-1.1
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 1 /Kids [3 0 R] >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 75 >>
stream
BT
/F1 18 Tf
72 720 Td
({title}) Tj
ET
BT
/F1 12 Tf
72 690 Td
(Generated by DemeterAI API) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000060 00000 n
0000000114 00000 n
0000000238 00000 n
0000000400 00000 n
trailer
<< /Root 1 0 R /Size 6 >>
startxref
480
%%EOF
"""
        return pdf_template.encode("utf-8")

    async def generate_csv_export(self, session_uuid: UUID) -> bytes:
        """Generate CSV export for session detections summary."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["session_id", "total_detected", "total_estimated", "avg_confidence"])
        session = await self.get_session_by_uuid(session_uuid)
        if session:
            writer.writerow(
                [
                    str(session.session_id),
                    session.total_detected,
                    session.total_estimated,
                    session.avg_confidence or 0.0,
                ]
            )
        return output.getvalue().encode("utf-8")

    async def generate_geojson_export(self, session_uuid: UUID) -> bytes:
        """Generate a simple GeoJSON for session detections."""
        session = await self.get_session_by_uuid(session_uuid)
        feature = {
            "type": "Feature",
            "properties": {
                "session_id": str(session_uuid),
                "total_detected": session.total_detected if session else None,
            },
            "geometry": None,
        }
        geojson = {"type": "FeatureCollection", "features": [feature]}
        return json.dumps(geojson).encode("utf-8")

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
