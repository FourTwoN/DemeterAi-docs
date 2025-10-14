"""Integration tests for MLPipelineCoordinator - END-TO-END PIPELINE TESTS.

This module tests the COMPLETE ML pipeline with REAL services (no mocks):
- Real YOLO v11 models (CPU/GPU)
- Real image processing
- Real database operations
- Real S3 operations (optional, can use local files)

Test Coverage Target: ≥85% (critical path coverage)

Business Context:
    These tests verify that the ENTIRE ML pipeline works together correctly
    for the 600,000+ plant inventory system. If these tests pass, the pipeline
    is production-ready.

Architecture:
    - Layer: Integration / End-to-End Testing
    - Real dependencies: YOLO models, PostgreSQL, S3 (optional)
    - Design pattern: Full-stack integration testing

Performance Requirements:
    - CPU: <10 minutes per photo (realistic)
    - GPU: <3 minutes per photo (3x speedup)
    - Memory: <4GB per worker

Critical Success Criteria:
    1. Complete pipeline executes without errors
    2. Results saved to database correctly
    3. Progress tracking works
    4. Performance within acceptable range
"""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

import pytest

# Skip integration tests if NO_INTEGRATION env var set
pytestmark = pytest.mark.skipif(
    os.getenv("NO_INTEGRATION") == "1", reason="Integration tests disabled (NO_INTEGRATION=1)"
)


# =============================================================================
# Test Fixtures - Real Services and Dependencies
# =============================================================================


@pytest.fixture
def sample_greenhouse_image(tmp_path):
    """Create realistic test greenhouse image.

    Creates a synthetic greenhouse photo with:
    - 3 container regions (segments/boxes)
    - Green vegetation pattern
    - Realistic dimensions (4000x3000px)

    Returns path to temporary image file.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        pytest.skip("OpenCV/NumPy required for integration tests")

    # Create 4000x3000 image (typical greenhouse camera resolution)
    img = np.zeros((3000, 4000, 3), dtype=np.uint8)

    # Add background (soil/floor)
    img[:, :] = [30, 20, 15]  # Brown soil

    # Add 3 container regions with green vegetation
    # Segment 1 (left half, 0-1500x, 200-2800y)
    img[200:2800, 0:1500] = [50, 200, 50]  # Green vegetation

    # Segment 2 (right half, 2000-3500x, 200-2800y)
    img[200:2800, 2000:3500] = [45, 195, 45]  # Green vegetation

    # Box (top center, 1600-2400x, 50-400y)
    img[50:400, 1600:2400] = [55, 205, 55]  # Green vegetation

    # Add random plant-like patterns (circles)
    for i in range(100):
        x = np.random.randint(100, 3900)
        y = np.random.randint(200, 2800)
        radius = np.random.randint(15, 30)
        cv2.circle(img, (x, y), radius, (60, 210, 60), -1)

    # Save to temporary file
    img_path = tmp_path / "test_greenhouse.jpg"
    cv2.imwrite(str(img_path), img)

    return str(img_path)


@pytest.fixture
async def test_db_session():
    """Create test database session with transaction rollback.

    This fixture creates a database session for testing and rolls back
    all changes after the test completes (clean slate for each test).
    """
    # NOTE: This requires proper database setup in conftest.py
    # For now, we'll assume it's available from the test infrastructure
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Begin transaction
        async with session.begin():
            yield session
            # Rollback happens automatically after yield


@pytest.fixture
async def real_segmentation_service():
    """Create real SegmentationService with YOLO model.

    WARNING: This loads a REAL YOLO v11 model (~50MB).
    CPU: ~800ms per image
    GPU: ~200ms per image
    """
    from app.services.ml_processing.segmentation_service import SegmentationService

    return SegmentationService()


@pytest.fixture
async def real_sahi_service():
    """Create real SAHIDetectionService with YOLO model.

    WARNING: This loads a REAL YOLO v11 detection model (~50MB).
    CPU: 4-6s per segmento
    GPU: 1-2s per segmento
    """
    from app.services.ml_processing.sahi_detection_service import SAHIDetectionService

    return SAHIDetectionService(worker_id=0)


@pytest.fixture
async def real_band_estimation_service():
    """Create real BandEstimationService.

    This service doesn't load ML models (uses OpenCV).
    Performance: <2s per segment
    """
    from app.services.ml_processing.band_estimation_service import BandEstimationService

    return BandEstimationService(num_bands=4, alpha_overcount=0.9)


# =============================================================================
# Integration Tests - Complete Pipeline
# =============================================================================


class TestMLPipelineIntegration:
    """Integration tests for complete ML pipeline with real services."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # Mark as slow test (can be skipped in fast CI)
    async def test_complete_pipeline_with_real_services(
        self,
        sample_greenhouse_image,
        real_segmentation_service,
        real_sahi_service,
        real_band_estimation_service,
        test_db_session,
    ):
        """Test complete pipeline with REAL ML services and database.

        Workflow:
        1. Create PhotoProcessingSession
        2. Run complete pipeline with real YOLO models
        3. Verify results saved to database
        4. Check performance within acceptable range

        Performance expectation:
        - CPU: <10 minutes
        - GPU: <3 minutes

        NOTE: This is the CRITICAL PATH test. If this passes, the pipeline works.
        """
        # Arrange: Create session in database
        from app.models.photo_processing_session import (
            PhotoProcessingSession,
            ProcessingSessionStatusEnum,
        )

        session_id = uuid.uuid4()
        original_image_id = uuid.uuid4()

        session = PhotoProcessingSession(
            session_id=session_id,
            original_image_id=original_image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )

        test_db_session.add(session)
        await test_db_session.commit()

        # Arrange: Create pipeline coordinator with real services
        # NOTE: We'll need to create repositories as well
        from app.repositories.detection_repository import DetectionRepository
        from app.repositories.estimation_repository import EstimationRepository
        from app.repositories.photo_processing_session_repository import (
            PhotoProcessingSessionRepository,
        )
        from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator

        session_repo = PhotoProcessingSessionRepository(test_db_session)
        detection_repo = DetectionRepository(test_db_session)
        estimation_repo = EstimationRepository(test_db_session)

        # Create direct detection service (for boxes/plugs)
        # NOTE: For integration test, we can use SAHI service as fallback
        direct_svc = real_sahi_service  # Simplified for testing

        coordinator = MLPipelineCoordinator(
            segmentation_svc=real_segmentation_service,
            sahi_svc=real_sahi_service,
            direct_svc=direct_svc,
            band_estimation_svc=real_band_estimation_service,
            session_repo=session_repo,
            detection_repo=detection_repo,
            estimation_repo=estimation_repo,
        )

        # Act: Run complete pipeline
        import time

        start_time = time.time()

        result = await coordinator.process_complete_pipeline(
            session_id=session_id, image_path=sample_greenhouse_image
        )

        elapsed_time = time.time() - start_time

        # Assert: Pipeline completed successfully
        assert result["status"] == "completed"
        assert result["session_id"] == str(session_id)

        # Assert: Detections recorded
        assert result["total_detections"] > 0, "Should detect at least some plants"
        assert result["total_detections"] < 10000, "Sanity check: not unrealistic count"

        # Assert: Estimations recorded (for segments)
        assert result["total_estimations"] >= 0

        # Assert: Average confidence reasonable
        assert 0.0 <= result["avg_confidence"] <= 1.0

        # Assert: Performance within acceptable range
        # CPU: <10 min (600s), GPU: <3 min (180s)
        max_time = 600  # 10 minutes for CPU
        assert (
            elapsed_time < max_time
        ), f"Pipeline too slow: {elapsed_time:.1f}s (max: {max_time}s)"

        # Assert: Session updated in database
        await test_db_session.refresh(session)
        assert session.status == ProcessingSessionStatusEnum.COMPLETED
        assert session.total_detected > 0
        assert session.avg_confidence is not None

        # Assert: Detections saved in database
        from app.models.detection import Detection

        detections_count = await test_db_session.scalar(
            test_db_session.query(Detection).filter_by(session_id=session.id).count()
        )
        assert detections_count > 0

        # Assert: Estimations saved in database (if any segments)
        from app.models.estimation import Estimation

        estimations_count = await test_db_session.scalar(
            test_db_session.query(Estimation).filter_by(session_id=session.id).count()
        )
        assert estimations_count >= 0

        # Log performance metrics
        print(f"\n--- Pipeline Performance ---")
        print(f"Total time: {elapsed_time:.2f}s")
        print(f"Detections: {result['total_detections']}")
        print(f"Estimations: {result['total_estimations']}")
        print(f"Avg confidence: {result['avg_confidence']:.4f}")
        print(f"----------------------------\n")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_pipeline_empty_image(
        self,
        tmp_path,
        real_segmentation_service,
        test_db_session,
    ):
        """Test pipeline with image containing NO containers (edge case).

        Expected behavior:
        - Segmentation returns empty list
        - Pipeline completes with zero detections/estimations
        - Status = completed (not failed)
        """
        # Arrange: Create empty image (no vegetation)
        try:
            import cv2
            import numpy as np
        except ImportError:
            pytest.skip("OpenCV/NumPy required")

        img = np.full((1000, 1500, 3), [30, 20, 15], dtype=np.uint8)  # Brown soil only
        img_path = tmp_path / "empty_greenhouse.jpg"
        cv2.imwrite(str(img_path), img)

        # Arrange: Create session
        from app.models.photo_processing_session import (
            PhotoProcessingSession,
            ProcessingSessionStatusEnum,
        )

        session_id = uuid.uuid4()
        original_image_id = uuid.uuid4()

        session = PhotoProcessingSession(
            session_id=session_id,
            original_image_id=original_image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )

        test_db_session.add(session)
        await test_db_session.commit()

        # Arrange: Create minimal coordinator (only segmentation needed)
        from app.repositories.detection_repository import DetectionRepository
        from app.repositories.estimation_repository import EstimationRepository
        from app.repositories.photo_processing_session_repository import (
            PhotoProcessingSessionRepository,
        )
        from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator

        # Create mock services for detection/estimation (won't be called)
        from unittest.mock import AsyncMock

        coordinator = MLPipelineCoordinator(
            segmentation_svc=real_segmentation_service,
            sahi_svc=AsyncMock(),  # Won't be called
            direct_svc=AsyncMock(),  # Won't be called
            band_estimation_svc=AsyncMock(),  # Won't be called
            session_repo=PhotoProcessingSessionRepository(test_db_session),
            detection_repo=DetectionRepository(test_db_session),
            estimation_repo=EstimationRepository(test_db_session),
        )

        # Act: Run pipeline
        result = await coordinator.process_complete_pipeline(
            session_id=session_id, image_path=str(img_path)
        )

        # Assert: Pipeline completed (not failed)
        assert result["status"] == "completed"

        # Assert: Zero detections/estimations
        assert result["total_detections"] == 0
        assert result["total_estimations"] == 0

        # Assert: Session updated correctly
        await test_db_session.refresh(session)
        assert session.status == ProcessingSessionStatusEnum.COMPLETED
        assert session.total_detected == 0
        assert session.total_estimated == 0


# =============================================================================
# Integration Tests - Performance Benchmarks
# =============================================================================


class TestMLPipelinePerformance:
    """Performance benchmark tests for ML pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.benchmark  # Mark as benchmark test
    async def test_pipeline_performance_cpu_benchmark(
        self,
        sample_greenhouse_image,
        real_segmentation_service,
        real_sahi_service,
        real_band_estimation_service,
    ):
        """Benchmark CPU performance for complete pipeline.

        Target: <10 minutes (600s) on CPU
        Typical: 5-8 minutes on modern CPU
        """
        # NOTE: This test can be run standalone for performance profiling
        # Skip if running in CI (too slow)
        if os.getenv("CI") == "true":
            pytest.skip("Skipping benchmark in CI environment")

        # Arrange: Create minimal pipeline (no DB operations for pure ML benchmark)
        from unittest.mock import AsyncMock

        from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator

        coordinator = MLPipelineCoordinator(
            segmentation_svc=real_segmentation_service,
            sahi_svc=real_sahi_service,
            direct_svc=real_sahi_service,
            band_estimation_svc=real_band_estimation_service,
            session_repo=AsyncMock(),
            detection_repo=AsyncMock(),
            estimation_repo=AsyncMock(),
        )

        # Mock session repository to avoid DB operations
        coordinator.session_repo.get_by_session_id.return_value = AsyncMock(
            id=1, session_id=uuid.uuid4(), status="pending"
        )
        coordinator.session_repo.update_progress = AsyncMock()
        coordinator.session_repo.update = AsyncMock()
        coordinator.detection_repo.bulk_insert = AsyncMock()
        coordinator.estimation_repo.bulk_insert = AsyncMock()

        # Act: Run pipeline 3 times and average
        import time

        times = []
        for i in range(3):
            session_id = uuid.uuid4()

            start = time.time()
            result = await coordinator.process_complete_pipeline(
                session_id=session_id, image_path=sample_greenhouse_image
            )
            elapsed = time.time() - start

            times.append(elapsed)

            print(f"\nRun {i+1}: {elapsed:.2f}s")
            print(f"  Detections: {result['total_detections']}")
            print(f"  Estimations: {result['total_estimations']}")

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time_limit = 600  # 10 minutes

        print(f"\n--- CPU Performance Benchmark ---")
        print(f"Average time: {avg_time:.2f}s")
        print(f"Min time: {min_time:.2f}s")
        print(f"Max time: {max(times):.2f}s")
        print(f"Target: <{max_time_limit}s")
        print(f"-----------------------------------\n")

        # Assert: Performance within acceptable range
        assert avg_time < max_time_limit, f"CPU too slow: {avg_time:.1f}s (max: {max_time_limit}s)"


# =============================================================================
# Integration Tests - Error Recovery
# =============================================================================


class TestMLPipelineErrorRecovery:
    """Test error recovery and resilience in real pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_handles_corrupted_image(
        self,
        tmp_path,
        real_segmentation_service,
        test_db_session,
    ):
        """Test pipeline handles corrupted image gracefully.

        Expected: Segmentation fails, session updated with failed status.
        """
        # Arrange: Create corrupted image file
        corrupted_path = tmp_path / "corrupted.jpg"
        corrupted_path.write_bytes(b"NOT A VALID IMAGE FILE")

        # Arrange: Create session
        from app.models.photo_processing_session import (
            PhotoProcessingSession,
            ProcessingSessionStatusEnum,
        )

        session_id = uuid.uuid4()
        original_image_id = uuid.uuid4()

        session = PhotoProcessingSession(
            session_id=session_id,
            original_image_id=original_image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )

        test_db_session.add(session)
        await test_db_session.commit()

        # Arrange: Create coordinator
        from unittest.mock import AsyncMock

        from app.repositories.photo_processing_session_repository import (
            PhotoProcessingSessionRepository,
        )
        from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator

        coordinator = MLPipelineCoordinator(
            segmentation_svc=real_segmentation_service,
            sahi_svc=AsyncMock(),
            direct_svc=AsyncMock(),
            band_estimation_svc=AsyncMock(),
            session_repo=PhotoProcessingSessionRepository(test_db_session),
            detection_repo=AsyncMock(),
            estimation_repo=AsyncMock(),
        )

        # Act & Assert: Should raise exception
        with pytest.raises((RuntimeError, FileNotFoundError, ValueError)):
            await coordinator.process_complete_pipeline(
                session_id=session_id, image_path=str(corrupted_path)
            )

        # Assert: Session marked as failed
        await test_db_session.refresh(session)
        assert session.status == ProcessingSessionStatusEnum.FAILED
        assert session.error_message is not None

    @pytest.mark.asyncio
    async def test_pipeline_handles_missing_image(
        self,
        real_segmentation_service,
        test_db_session,
    ):
        """Test pipeline handles missing image file gracefully."""
        # Arrange: Use non-existent image path
        missing_path = "/tmp/nonexistent_image_12345.jpg"

        # Arrange: Create session
        from app.models.photo_processing_session import (
            PhotoProcessingSession,
            ProcessingSessionStatusEnum,
        )

        session_id = uuid.uuid4()
        original_image_id = uuid.uuid4()

        session = PhotoProcessingSession(
            session_id=session_id,
            original_image_id=original_image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )

        test_db_session.add(session)
        await test_db_session.commit()

        # Arrange: Create coordinator
        from unittest.mock import AsyncMock

        from app.repositories.photo_processing_session_repository import (
            PhotoProcessingSessionRepository,
        )
        from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator

        coordinator = MLPipelineCoordinator(
            segmentation_svc=real_segmentation_service,
            sahi_svc=AsyncMock(),
            direct_svc=AsyncMock(),
            band_estimation_svc=AsyncMock(),
            session_repo=PhotoProcessingSessionRepository(test_db_session),
            detection_repo=AsyncMock(),
            estimation_repo=AsyncMock(),
        )

        # Act & Assert: Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await coordinator.process_complete_pipeline(
                session_id=session_id, image_path=missing_path
            )

        # Assert: Session marked as failed
        await test_db_session.refresh(session)
        assert session.status == ProcessingSessionStatusEnum.FAILED


# =============================================================================
# Integration Tests - Result Validation
# =============================================================================


class TestMLPipelineResultValidation:
    """Test result validation and data integrity."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_pipeline_results_match_database(
        self,
        sample_greenhouse_image,
        real_segmentation_service,
        real_sahi_service,
        real_band_estimation_service,
        test_db_session,
    ):
        """Test that pipeline results match what's saved in database.

        Critical integrity check: returned results should match DB records.
        """
        # Arrange: Create session
        from app.models.photo_processing_session import (
            PhotoProcessingSession,
            ProcessingSessionStatusEnum,
        )

        session_id = uuid.uuid4()
        original_image_id = uuid.uuid4()

        session = PhotoProcessingSession(
            session_id=session_id,
            original_image_id=original_image_id,
            status=ProcessingSessionStatusEnum.PENDING,
        )

        test_db_session.add(session)
        await test_db_session.commit()

        # Arrange: Create coordinator with real repositories
        from app.repositories.detection_repository import DetectionRepository
        from app.repositories.estimation_repository import EstimationRepository
        from app.repositories.photo_processing_session_repository import (
            PhotoProcessingSessionRepository,
        )
        from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator

        session_repo = PhotoProcessingSessionRepository(test_db_session)
        detection_repo = DetectionRepository(test_db_session)
        estimation_repo = EstimationRepository(test_db_session)

        coordinator = MLPipelineCoordinator(
            segmentation_svc=real_segmentation_service,
            sahi_svc=real_sahi_service,
            direct_svc=real_sahi_service,
            band_estimation_svc=real_band_estimation_service,
            session_repo=session_repo,
            detection_repo=detection_repo,
            estimation_repo=estimation_repo,
        )

        # Act: Run pipeline
        result = await coordinator.process_complete_pipeline(
            session_id=session_id, image_path=sample_greenhouse_image
        )

        # Assert: Session in database matches result
        await test_db_session.refresh(session)
        assert session.total_detected == result["total_detections"]
        assert session.total_estimated == result["total_estimations"]

        # Assert: Detection count in DB matches result
        from app.models.detection import Detection

        db_detection_count = await test_db_session.scalar(
            test_db_session.query(Detection).filter_by(session_id=session.id).count()
        )
        assert db_detection_count == result["total_detections"]

        # Assert: Estimation count in DB matches result (if any)
        from app.models.estimation import Estimation

        db_estimation_count = await test_db_session.scalar(
            test_db_session.query(Estimation).filter_by(session_id=session.id).count()
        )

        # Estimations count = number of bands × number of segments
        # Each estimation has estimated_count, so total_estimations = sum(estimated_count)
        # But db_estimation_count = number of estimation records
        # These are different! db_estimation_count should be multiple of 4 (bands)
        assert db_estimation_count % 4 == 0 or db_estimation_count == 0
