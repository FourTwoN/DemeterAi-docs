"""Unit tests for PhotoProcessingSession model (DB012).

Tests the PhotoProcessingSession SQLAlchemy model against PostgreSQL database.
Covers CRUD operations, validations, relationships, JSONB fields, aggregates,
enum status, and timestamp behavior.

Test Coverage:
    - Basic CRUD operations (create, read, update, delete)
    - Status enum validation (pending, processing, completed, failed)
    - JSONB fields (category_counts, manual_adjustments)
    - Aggregate fields (total_detected, total_estimated, avg_confidence)
    - Confidence range validation (0.0-1.0)
    - FK relationships (storage_location, s3_images, user)
    - Timestamp auto-population (created_at, updated_at)
    - CASCADE delete behavior
    - UUID session_id generation

Architecture:
    - Layer: Unit Tests (model testing with real PostgreSQL)
    - Dependencies: pytest, PhotoProcessingSession model, db_session fixture
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/unit/models/test_photo_processing_session.py -v
    pytest tests/unit/models/test_photo_processing_session.py --cov=app.models.photo_processing_session --cov-report=term-missing
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.photo_processing_session import PhotoProcessingSession, ProcessingSessionStatusEnum
from app.models.s3_image import ContentTypeEnum, S3Image
from app.models.s3_image import ProcessingStatusEnum as S3ProcessingStatusEnum


class TestPhotoProcessingSessionBasicCRUD:
    """Test suite for PhotoProcessingSession basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_session_minimal_fields(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test creating session with minimal required fields."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id is not None
        assert session.session_id is not None
        assert session.storage_location_id == location.location_id
        assert session.original_image_id == s3_image.image_id
        assert session.status == ProcessingSessionStatusEnum.PENDING
        assert session.total_detected == 0
        assert session.total_estimated == 0
        assert session.total_empty_containers == 0
        assert session.avg_confidence is None
        assert session.category_counts == {}
        assert session.manual_adjustments == {}
        assert session.validated is False

    @pytest.mark.asyncio
    async def test_create_session_all_fields(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory, user_factory
    ):
        """Test creating session with all fields populated."""
        location = await storage_location_factory()

        original_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )

        processed_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"processed/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=3145728,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.READY,
        )

        user = await user_factory(email="test@example.com", first_name="testuser")

        db_session.add_all([original_image, processed_image, user])
        await db_session.commit()
        await db_session.refresh(original_image)
        await db_session.refresh(processed_image)
        await db_session.refresh(user)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=original_image.image_id,
            processed_image_id=processed_image.image_id,
            total_detected=42,
            total_estimated=150,
            total_empty_containers=3,
            avg_confidence=Decimal("0.9200"),
            category_counts={"echeveria": 25, "aloe": 17},
            status=ProcessingSessionStatusEnum.COMPLETED,
            validated=True,
            validated_by_user_id=user.id,
            manual_adjustments={"adjustment_type": "manual_count", "value": 5},
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id is not None
        assert session.total_detected == 42
        assert session.total_estimated == 150
        assert session.total_empty_containers == 3
        assert float(session.avg_confidence) == 0.92
        assert session.category_counts == {"echeveria": 25, "aloe": 17}
        assert session.status == ProcessingSessionStatusEnum.COMPLETED
        assert session.validated is True
        assert session.validated_by_user_id == user.id
        assert session.manual_adjustments == {"adjustment_type": "manual_count", "value": 5}

    @pytest.mark.asyncio
    async def test_read_session_by_id(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test reading session by primary key."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            total_detected=10,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        from sqlalchemy import select

        result = await db_session.execute(
            select(PhotoProcessingSession).where(PhotoProcessingSession.id == session.id)
        )
        found = result.scalar_one()

        assert found.id == session.id
        assert found.session_id == session.session_id
        assert found.total_detected == 10

    @pytest.mark.asyncio
    async def test_update_session_status(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test updating session status."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        session.status = ProcessingSessionStatusEnum.PROCESSING
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == ProcessingSessionStatusEnum.PROCESSING

    @pytest.mark.asyncio
    async def test_delete_session_cascade(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test CASCADE delete when location is deleted."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
        )
        db_session.add(session)
        await db_session.commit()
        session_id = session.id

        await db_session.delete(location)
        await db_session.commit()

        from sqlalchemy import select

        result = await db_session.execute(
            select(PhotoProcessingSession).where(PhotoProcessingSession.id == session_id)
        )
        found = result.scalar_one_or_none()

        assert found is None


class TestPhotoProcessingSessionStatusEnum:
    """Test suite for PhotoProcessingSession status enum validation."""

    @pytest.mark.asyncio
    async def test_status_pending(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test session with PENDING status."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == ProcessingSessionStatusEnum.PENDING
        assert session.status.value == "pending"

    @pytest.mark.asyncio
    async def test_status_processing(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test session with PROCESSING status."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            status=ProcessingSessionStatusEnum.PROCESSING,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == ProcessingSessionStatusEnum.PROCESSING

    @pytest.mark.asyncio
    async def test_status_completed(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test session with COMPLETED status."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            status=ProcessingSessionStatusEnum.COMPLETED,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == ProcessingSessionStatusEnum.COMPLETED

    @pytest.mark.asyncio
    async def test_status_failed(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test session with FAILED status and error message."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            status=ProcessingSessionStatusEnum.FAILED,
            error_message="YOLO model inference timeout",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == ProcessingSessionStatusEnum.FAILED
        assert session.error_message == "YOLO model inference timeout"


class TestPhotoProcessingSessionConfidenceValidation:
    """Test suite for avg_confidence validation (0.0-1.0 range)."""

    @pytest.mark.asyncio
    async def test_avg_confidence_min_value(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test avg_confidence with minimum value (0.0)."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            avg_confidence=Decimal("0.0000"),
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert float(session.avg_confidence) == 0.0

    @pytest.mark.asyncio
    async def test_avg_confidence_max_value(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test avg_confidence with maximum value (1.0)."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            avg_confidence=Decimal("1.0000"),
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert float(session.avg_confidence) == 1.0

    @pytest.mark.asyncio
    async def test_avg_confidence_out_of_range_high(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test that avg_confidence > 1.0 raises ValueError."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        with pytest.raises(ValueError, match="avg_confidence must be between 0.0 and 1.0"):
            session = PhotoProcessingSession(
                session_id=uuid4(),
                storage_location_id=location.location_id,
                original_image_id=s3_image.image_id,
                avg_confidence=Decimal("1.5000"),
            )

    @pytest.mark.asyncio
    async def test_avg_confidence_nullable(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test that avg_confidence can be NULL."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            avg_confidence=None,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.avg_confidence is None


class TestPhotoProcessingSessionJSONBFields:
    """Test suite for JSONB fields (category_counts, manual_adjustments)."""

    @pytest.mark.asyncio
    async def test_category_counts_empty_dict_default(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test category_counts defaults to empty dict."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.category_counts == {}

    @pytest.mark.asyncio
    async def test_category_counts_with_data(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test category_counts with multiple categories."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            category_counts={"echeveria": 25, "aloe": 17, "crassula": 8},
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.category_counts == {"echeveria": 25, "aloe": 17, "crassula": 8}

    @pytest.mark.asyncio
    async def test_manual_adjustments_empty_dict_default(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test manual_adjustments defaults to empty dict."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.manual_adjustments == {}

    @pytest.mark.asyncio
    async def test_manual_adjustments_with_data(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test manual_adjustments with adjustment data."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            manual_adjustments={
                "adjustment_type": "manual_count",
                "value": 5,
                "reason": "Corrected ML misdetection",
            },
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.manual_adjustments["adjustment_type"] == "manual_count"
        assert session.manual_adjustments["value"] == 5


class TestPhotoProcessingSessionAggregates:
    """Test suite for aggregate fields (totals, avg_confidence)."""

    @pytest.mark.asyncio
    async def test_aggregates_default_zero(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test aggregates default to 0."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.total_detected == 0
        assert session.total_estimated == 0
        assert session.total_empty_containers == 0

    @pytest.mark.asyncio
    async def test_aggregates_with_values(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test aggregates with realistic values."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            total_detected=42,
            total_estimated=150,
            total_empty_containers=3,
            avg_confidence=Decimal("0.9200"),
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.total_detected == 42
        assert session.total_estimated == 150
        assert session.total_empty_containers == 3
        assert float(session.avg_confidence) == 0.92


class TestPhotoProcessingSessionTimestamps:
    """Test suite for timestamp auto-population."""

    @pytest.mark.asyncio
    async def test_created_at_auto_populated(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test created_at is auto-populated by database."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.created_at is not None

    @pytest.mark.asyncio
    async def test_updated_at_on_modification(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test updated_at is set when session is modified."""
        location = await storage_location_factory()

        s3_image = S3Image(
            image_id=uuid4(),
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{uuid4()}.jpg",
            content_type=ContentTypeEnum.JPEG,
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            status=S3ProcessingStatusEnum.UPLOADED,
        )
        db_session.add(s3_image)
        await db_session.commit()
        await db_session.refresh(s3_image)

        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=location.location_id,
            original_image_id=s3_image.image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        session.status = ProcessingSessionStatusEnum.COMPLETED
        session.total_detected = 50
        await db_session.commit()
        await db_session.refresh(session)

        assert session.updated_at is not None
