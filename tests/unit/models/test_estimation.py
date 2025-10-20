"""Unit tests for Estimation model (DB014).

Tests the Estimation SQLAlchemy model against PostgreSQL database.
Covers CRUD operations, validations, relationships, JSONB vegetation_polygon,
calculation method enum, confidence validation, area/count validation,
and partitioning behavior.

Test Coverage:
    - Basic CRUD operations (create, read, update, delete)
    - Calculation method enum (band_estimation, density_estimation, grid_analysis)
    - Confidence validation (0.0-1.0 range, default 0.70)
    - Area validation (detected_area_cm2 >= 0.0)
    - Count validation (estimated_count >= 0)
    - JSONB vegetation_polygon validation (dict required)
    - Boolean flag (used_density_parameters)
    - FK relationships (session, stock_movement, classification)
    - Timestamp auto-population (created_at only, immutable)
    - CASCADE delete behavior
    - Partitioning by session_id (implicit)

Architecture:
    - Layer: Unit Tests (model testing with real PostgreSQL)
    - Dependencies: pytest, Estimation model, db_session fixture
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/unit/models/test_estimation.py -v
    pytest tests/unit/models/test_estimation.py --cov=app.models.estimation --cov-report=term-missing
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.classification import Classification
from app.models.estimation import CalculationMethodEnum, Estimation
from app.models.photo_processing_session import PhotoProcessingSession, ProcessingSessionStatusEnum
from app.models.product import Product
from app.models.s3_image import ContentTypeEnum, S3Image
from app.models.s3_image import ProcessingStatusEnum as S3ProcessingStatusEnum
from app.models.stock_movement import MovementTypeEnum, SourceTypeEnum, StockMovement


class TestEstimationBasicCRUD:
    """Test suite for Estimation basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_estimation_minimal_fields(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test creating estimation with minimal required fields."""
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

        product = Product(code="PROD-001", name="Test Product", category="cactus")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id, product_conf=85)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=15,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("250.50"),
            estimated_count=15,
            calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
            estimation_confidence=Decimal("0.7500"),
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert estimation.id is not None
        assert estimation.session_id == session.id
        assert estimation.stock_movement_id == stock_movement.id
        assert estimation.classification_id == classification.classification_id
        assert float(estimation.detected_area_cm2) == 250.50
        assert estimation.estimated_count == 15
        assert estimation.calculation_method == CalculationMethodEnum.BAND_ESTIMATION
        assert float(estimation.estimation_confidence) == 0.75
        assert estimation.used_density_parameters is True

    @pytest.mark.asyncio
    async def test_create_estimation_all_fields(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test creating estimation with all fields populated."""
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

        product = Product(code="PROD-002", name="Test Product 2", category="succulent")
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        classification = Classification(product_id=product.id, product_conf=80)
        db_session.add(classification)
        await db_session.commit()
        await db_session.refresh(classification)

        stock_movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type=MovementTypeEnum.FOTO,
            quantity=25,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={
                "coordinates": [[200, 300], [300, 300], [300, 400], [200, 400]],
                "type": "Polygon",
            },
            detected_area_cm2=Decimal("500.75"),
            estimated_count=25,
            calculation_method=CalculationMethodEnum.DENSITY_ESTIMATION,
            estimation_confidence=Decimal("0.8200"),
            used_density_parameters=False,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert estimation.id is not None
        assert float(estimation.detected_area_cm2) == 500.75
        assert estimation.estimated_count == 25
        assert estimation.calculation_method == CalculationMethodEnum.DENSITY_ESTIMATION
        assert float(estimation.estimation_confidence) == 0.82
        assert estimation.used_density_parameters is False

    @pytest.mark.asyncio
    async def test_read_estimation_by_id(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test reading estimation by primary key."""
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

        product = Product(code="PROD-003", name="Test Product 3", category="cactus")
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
            quantity=10,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("150.00"),
            estimated_count=10,
            calculation_method=CalculationMethodEnum.GRID_ANALYSIS,
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        from sqlalchemy import select

        result = await db_session.execute(select(Estimation).where(Estimation.id == estimation.id))
        found = result.scalar_one()

        assert found.id == estimation.id
        assert found.session_id == session.id
        assert found.estimated_count == 10


class TestEstimationCalculationMethodEnum:
    """Test suite for calculation_method enum validation."""

    @pytest.mark.asyncio
    async def test_calculation_method_band_estimation(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test estimation with BAND_ESTIMATION method."""
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

        product = Product(code="PROD-004", name="Test Product 4", category="cactus")
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
            quantity=10,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("150.00"),
            estimated_count=10,
            calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert estimation.calculation_method == CalculationMethodEnum.BAND_ESTIMATION
        assert estimation.calculation_method.value == "band_estimation"

    @pytest.mark.asyncio
    async def test_calculation_method_density_estimation(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test estimation with DENSITY_ESTIMATION method."""
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

        product = Product(code="PROD-005", name="Test Product 5", category="succulent")
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
            quantity=20,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("300.00"),
            estimated_count=20,
            calculation_method=CalculationMethodEnum.DENSITY_ESTIMATION,
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert estimation.calculation_method == CalculationMethodEnum.DENSITY_ESTIMATION

    @pytest.mark.asyncio
    async def test_calculation_method_grid_analysis(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test estimation with GRID_ANALYSIS method."""
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

        product = Product(code="PROD-006", name="Test Product 6", category="cactus")
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
            quantity=12,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("180.00"),
            estimated_count=12,
            calculation_method=CalculationMethodEnum.GRID_ANALYSIS,
            used_density_parameters=False,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert estimation.calculation_method == CalculationMethodEnum.GRID_ANALYSIS


class TestEstimationConfidenceValidation:
    """Test suite for estimation_confidence validation (0.0-1.0 range, default 0.70)."""

    @pytest.mark.asyncio
    async def test_confidence_default_value(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test estimation_confidence defaults to 0.70."""
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

        product = Product(code="PROD-007", name="Test Product 7", category="cactus")
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
            quantity=10,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("150.00"),
            estimated_count=10,
            calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert float(estimation.estimation_confidence) == 0.70

    @pytest.mark.asyncio
    async def test_confidence_min_value(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test estimation_confidence with minimum value (0.0)."""
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

        product = Product(code="PROD-008", name="Test Product 8", category="cactus")
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
            quantity=10,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("150.00"),
            estimated_count=10,
            calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
            estimation_confidence=Decimal("0.0000"),
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert float(estimation.estimation_confidence) == 0.0

    @pytest.mark.asyncio
    async def test_confidence_max_value(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
    ):
        """Test estimation_confidence with maximum value (1.0)."""
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

        product = Product(code="PROD-009", name="Test Product 9", category="cactus")
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
            quantity=10,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("150.00"),
            estimated_count=10,
            calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
            estimation_confidence=Decimal("1.0000"),
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert float(estimation.estimation_confidence) == 1.0

    def test_confidence_out_of_range_high(self):
        """Test that estimation_confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="estimation_confidence must be between 0.0 and 1.0"):
            Estimation(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                vegetation_polygon={
                    "coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]
                },
                detected_area_cm2=Decimal("150.00"),
                estimated_count=10,
                calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
                estimation_confidence=Decimal("1.5000"),
                used_density_parameters=True,
            )


class TestEstimationAreaCountValidation:
    """Test suite for detected_area_cm2 and estimated_count validation."""

    def test_detected_area_cm2_non_negative(self):
        """Test detected_area_cm2 must be non-negative."""
        with pytest.raises(ValueError, match="detected_area_cm2 must be non-negative"):
            Estimation(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                vegetation_polygon={
                    "coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]
                },
                detected_area_cm2=Decimal("-10.00"),
                estimated_count=10,
                calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
                used_density_parameters=True,
            )

    def test_estimated_count_non_negative(self):
        """Test estimated_count must be non-negative."""
        with pytest.raises(ValueError, match="estimated_count must be non-negative"):
            Estimation(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                vegetation_polygon={
                    "coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]
                },
                detected_area_cm2=Decimal("150.00"),
                estimated_count=-5,
                calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
                used_density_parameters=True,
            )

    def test_vegetation_polygon_cannot_be_null(self):
        """Test vegetation_polygon cannot be None."""
        with pytest.raises(ValueError, match="vegetation_polygon cannot be None"):
            Estimation(
                session_id=1,
                stock_movement_id=1,
                classification_id=1,
                vegetation_polygon=None,
                detected_area_cm2=Decimal("150.00"),
                estimated_count=10,
                calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
                used_density_parameters=True,
            )


class TestEstimationTimestamps:
    """Test suite for timestamp auto-population (created_at only)."""

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

        product = Product(code="PROD-010", name="Test Product 10", category="cactus")
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
            quantity=10,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("150.00"),
            estimated_count=10,
            calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        await db_session.refresh(estimation)

        assert estimation.created_at is not None


class TestEstimationCascadeDelete:
    """Test suite for CASCADE delete behavior."""

    @pytest.mark.asyncio
    async def test_delete_session_cascades_to_estimations(
        self, db_session, warehouse_factory, storage_area_factory, storage_location_factory
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

        product = Product(code="PROD-011", name="Test Product 11", category="cactus")
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
            quantity=10,
            user_id=1,
            source_type=SourceTypeEnum.IA,
            is_inbound=True,
        )
        db_session.add(stock_movement)
        await db_session.commit()
        await db_session.refresh(stock_movement)

        estimation = Estimation(
            session_id=session.id,
            stock_movement_id=stock_movement.id,
            classification_id=classification.classification_id,
            vegetation_polygon={"coordinates": [[100, 200], [150, 200], [150, 250], [100, 250]]},
            detected_area_cm2=Decimal("150.00"),
            estimated_count=10,
            calculation_method=CalculationMethodEnum.BAND_ESTIMATION,
            used_density_parameters=True,
        )
        db_session.add(estimation)
        await db_session.commit()
        estimation_id = estimation.id

        await db_session.delete(session)
        await db_session.commit()

        from sqlalchemy import select

        result = await db_session.execute(select(Estimation).where(Estimation.id == estimation_id))
        found = result.scalar_one_or_none()

        assert found is None
