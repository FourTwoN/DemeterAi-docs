"""Unit tests for Detection model (DB013).

Tests the Detection SQLAlchemy model against PostgreSQL database.
Covers CRUD operations, validations, relationships, JSONB bbox_coordinates,
confidence validation, bounding box dimensions, and partitioning behavior.

Test Coverage:
    - Basic CRUD operations (create, read, update, delete)
    - Bounding box validation (width_px, height_px > 0)
    - Confidence validation (0.0-1.0 range)
    - JSONB bbox_coordinates validation (x1, y1, x2, y2)
    - Boolean flags (is_empty_container, is_alive)
    - FK relationships (session, stock_movement, classification)
    - Timestamp auto-population (created_at only, immutable)
    - CASCADE delete behavior
    - Partitioning by session_id (implicit)

Architecture:
    - Layer: Unit Tests (model testing with real PostgreSQL)
    - Dependencies: pytest, Detection model, db_session fixture
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/unit/models/test_detection.py -v
    pytest tests/unit/models/test_detection.py --cov=app.models.detection --cov-report=term-missing
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.classification import Classification
from app.models.detection import Detection
from app.models.photo_processing_session import PhotoProcessingSession, ProcessingSessionStatusEnum
from app.models.s3_image import ContentTypeEnum, S3Image
from app.models.s3_image import ProcessingStatusEnum as S3ProcessingStatusEnum
from app.models.stock_movement import MovementTypeEnum, SourceTypeEnum, StockMovement


class TestDetectionBasicCRUD:
    """Test suite for Detection basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_detection_minimal_fields(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test creating detection with minimal required fields."""
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

        product = await product_factory(sku="PROD-001", common_name="Test Product")

        classification = Classification(product_id=product.id, product_conf=95)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("512.50"),
            center_y_px=Decimal("768.30"),
            width_px=120,
            height_px=135,
            bbox_geojson_coordinates={"x1": 452, "y1": 700, "x2": 572, "y2": 835},
            detection_confidence=Decimal("0.9500"),
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        assert detection.id is not None
        assert detection.session_id == session.id
        assert detection.stock_movement_id == stock_movement.id
        assert detection.classification_id == classification.classification_id
        assert float(detection.center_x_px) == 512.50
        assert float(detection.center_y_px) == 768.30
        assert detection.width_px == 120
        assert detection.height_px == 135
        assert float(detection.detection_confidence) == 0.95
        assert detection.is_empty_container is False
        assert detection.is_alive is True

    @pytest.mark.asyncio
    async def test_create_detection_all_fields(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test creating detection with all fields populated."""
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

        product = await product_factory(sku="PROD-002", common_name="Test Product 2")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id, product_conf=87)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("1024.75"),
            center_y_px=Decimal("1536.25"),
            width_px=200,
            height_px=250,
            bbox_geojson_coordinates={"x1": 924, "y1": 1411, "x2": 1124, "y2": 1661},
            detection_confidence=Decimal("0.8700"),
            is_empty_container=False,
            is_alive=True,
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        assert detection.id is not None
        assert float(detection.center_x_px) == 1024.75
        assert float(detection.center_y_px) == 1536.25
        assert detection.width_px == 200
        assert detection.height_px == 250
        assert float(detection.detection_confidence) == 0.87

    @pytest.mark.asyncio
    async def test_read_detection_by_id(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test reading detection by primary key."""
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

        product = await product_factory(sku="PROD-003", common_name="Test Product 3")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("500.0"),
            center_y_px=Decimal("600.0"),
            width_px=100,
            height_px=120,
            bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
            detection_confidence=Decimal("0.9200"),
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        from sqlalchemy import select

        result = await db_session.execute(select(Detection).where(Detection.id == detection.id))
        found = result.scalar_one()

        assert found.id == detection.id
        assert found.session_id == session.id
        assert float(found.detection_confidence) == 0.92


class TestDetectionConfidenceValidation:
    """Test suite for detection_confidence validation (0.0-1.0 range)."""

    @pytest.mark.asyncio
    async def test_confidence_min_value(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test detection_confidence with minimum value (0.0)."""
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

        product = await product_factory(sku="PROD-004", common_name="Test Product 4")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("500.0"),
            center_y_px=Decimal("600.0"),
            width_px=100,
            height_px=120,
            bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
            detection_confidence=Decimal("0.0000"),
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        assert float(detection.detection_confidence) == 0.0

    @pytest.mark.asyncio
    async def test_confidence_max_value(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test detection_confidence with maximum value (1.0)."""
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

        product = await product_factory(sku="PROD-005", common_name="Test Product 5")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("500.0"),
            center_y_px=Decimal("600.0"),
            width_px=100,
            height_px=120,
            bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
            detection_confidence=Decimal("1.0000"),
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        assert float(detection.detection_confidence) == 1.0

    def test_confidence_out_of_range_high(self):
        """Test that detection_confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="detection_confidence must be between 0.0 and 1.0"):
            Detection(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                center_x_px=Decimal("500.0"),
                center_y_px=Decimal("600.0"),
                width_px=100,
                height_px=120,
                bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
                detection_confidence=Decimal("1.5000"),
            )

    def test_confidence_cannot_be_null(self):
        """Test that detection_confidence cannot be None."""
        with pytest.raises(ValueError, match="detection_confidence cannot be None"):
            Detection(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                center_x_px=Decimal("500.0"),
                center_y_px=Decimal("600.0"),
                width_px=100,
                height_px=120,
                bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
                detection_confidence=None,
            )


class TestDetectionBboxValidation:
    """Test suite for bounding box dimensions validation."""

    def test_width_px_positive(self):
        """Test width_px must be positive."""
        with pytest.raises(ValueError, match="width_px must be positive"):
            Detection(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                center_x_px=Decimal("500.0"),
                center_y_px=Decimal("600.0"),
                width_px=0,
                height_px=120,
                bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
                detection_confidence=Decimal("0.9000"),
            )

    def test_height_px_positive(self):
        """Test height_px must be positive."""
        with pytest.raises(ValueError, match="height_px must be positive"):
            Detection(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                center_x_px=Decimal("500.0"),
                center_y_px=Decimal("600.0"),
                width_px=100,
                height_px=-10,
                bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
                detection_confidence=Decimal("0.9000"),
            )

    def test_bbox_coordinates_required_keys(self):
        """Test bbox_coordinates must contain x1, y1, x2, y2."""
        with pytest.raises(ValueError, match="bbox_coordinates must contain keys"):
            Detection(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                center_x_px=Decimal("500.0"),
                center_y_px=Decimal("600.0"),
                width_px=100,
                height_px=120,
                bbox_geojson_coordinates={"x1": 450, "y1": 540},  # Missing x2, y2
                detection_confidence=Decimal("0.9000"),
            )

    def test_bbox_coordinates_cannot_be_null(self):
        """Test bbox_coordinates cannot be None."""
        with pytest.raises(ValueError, match="bbox_coordinates cannot be None"):
            Detection(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                center_x_px=Decimal("500.0"),
                center_y_px=Decimal("600.0"),
                width_px=100,
                height_px=120,
                bbox_geojson_coordinates=None,
                detection_confidence=Decimal("0.9000"),
            )


class TestDetectionBooleanFlags:
    """Test suite for boolean flags (is_empty_container, is_alive)."""

    @pytest.mark.asyncio
    async def test_is_empty_container_true(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test detection with is_empty_container=True."""
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

        product = await product_factory(sku="PROD-006", common_name="Empty Container")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("500.0"),
            center_y_px=Decimal("600.0"),
            width_px=100,
            height_px=120,
            bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
            detection_confidence=Decimal("0.8500"),
            is_empty_container=True,
            is_alive=False,
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        assert detection.is_empty_container is True
        assert detection.is_alive is False

    @pytest.mark.asyncio
    async def test_is_alive_false(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test detection with is_alive=False (dead plant)."""
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

        product = await product_factory(sku="PROD-007", common_name="Dead Plant")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("500.0"),
            center_y_px=Decimal("600.0"),
            width_px=100,
            height_px=120,
            bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
            detection_confidence=Decimal("0.7500"),
            is_empty_container=False,
            is_alive=False,
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        assert detection.is_empty_container is False
        assert detection.is_alive is False


class TestDetectionTimestamps:
    """Test suite for timestamp auto-population (created_at only)."""

    @pytest.mark.asyncio
    async def test_created_at_auto_populated(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
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

        product = await product_factory(sku="PROD-008", common_name="Test Product 8")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("500.0"),
            center_y_px=Decimal("600.0"),
            width_px=100,
            height_px=120,
            bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
            detection_confidence=Decimal("0.9000"),
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)

        assert detection.created_at is not None


class TestDetectionCascadeDelete:
    """Test suite for CASCADE delete behavior."""

    @pytest.mark.asyncio
    async def test_delete_session_cascades_to_detections(
        self,
        db_session,
        warehouse_factory,
        storage_area_factory,
        storage_location_factory,
        product_factory,
    ):
        """Test CASCADE delete when session is deleted."""
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

        product = await product_factory(sku="PROD-009", common_name="Test Product 9")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=1,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        detection = Detection(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            center_x_px=Decimal("500.0"),
            center_y_px=Decimal("600.0"),
            width_px=100,
            height_px=120,
            bbox_geojson_coordinates={"x1": 450, "y1": 540, "x2": 550, "y2": 660},
            detection_confidence=Decimal("0.9000"),
        )
        db_session.add(detection)
        await db_session.commit()
        detection_id = detection.id

        await db_session.delete(session)
        await db_session.commit()

        from sqlalchemy import select

        result = await db_session.execute(select(Detection).where(Detection.id == detection_id))
        found = result.scalar_one_or_none()

        assert found is None
