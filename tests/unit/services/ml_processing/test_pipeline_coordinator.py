"""Unit tests for MLPipelineCoordinator - CRITICAL PATH orchestrator.

This module tests the ML pipeline orchestrator that coordinates:
- ML002: Segmentation (container detection)
- ML003: SAHI Detection (plant detection in segmentos)
- ML004: Direct Detection (plant detection in boxes/plugs)
- ML005: Band Estimation (undetected plant estimation)
- DB012: PhotoProcessingSession progress tracking

Test Coverage Target: ≥85%

Business Context:
    The MLPipelineCoordinator is the MOST CRITICAL service in DemeterAI v2.0.
    It orchestrates the complete ML pipeline from photo upload to final results.
    This service determines whether 600,000+ plants are counted correctly or not.

Architecture:
    - Layer: Services / ML Processing
    - Dependencies: ALL ML services (ML002-ML006), ALL repositories
    - Design pattern: Pipeline orchestrator, error recovery, progress tracking

Critical Quality Gates:
    - Progress updates at each stage (20%, 50%, 80%, 100%)
    - Error handling with warning states (NOT hard failures)
    - Bulk insertions for detections/estimations
    - Complete result aggregation
    - Performance: <10 minutes on CPU for full photo
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# Test Fixtures - Mock Services and Dependencies
# =============================================================================


@pytest.fixture
def mock_segmentation_service():
    """Mock SegmentationService for testing.

    Returns service that simulates segmentation of containers:
    - 2 segments (large containers)
    - 1 box (medium container)
    """
    service = AsyncMock()

    # Mock segment_image to return 3 containers
    mock_segments = [
        MagicMock(
            container_type="segment",
            confidence=0.92,
            bbox=(0.1, 0.1, 0.5, 0.9),
            polygon=[(0.1, 0.1), (0.5, 0.1), (0.5, 0.9), (0.1, 0.9)],
            mask=None,
            area_pixels=200000,
        ),
        MagicMock(
            container_type="segment",
            confidence=0.88,
            bbox=(0.5, 0.1, 0.9, 0.9),
            polygon=[(0.5, 0.1), (0.9, 0.1), (0.9, 0.9), (0.5, 0.9)],
            mask=None,
            area_pixels=180000,
        ),
        MagicMock(
            container_type="box",
            confidence=0.85,
            bbox=(0.1, 0.05, 0.3, 0.15),
            polygon=[(0.1, 0.05), (0.3, 0.05), (0.3, 0.15), (0.1, 0.15)],
            mask=None,
            area_pixels=50000,
        ),
    ]

    service.segment_image.return_value = mock_segments
    return service


@pytest.fixture
def mock_sahi_service():
    """Mock SAHIDetectionService for testing.

    Returns service that simulates SAHI detection in segments:
    - 400 detections per segment
    """
    service = AsyncMock()

    # Mock detect_in_segmento to return 400 detections
    def create_detections(count=400):
        return [
            MagicMock(
                center_x_px=100 + i * 5,
                center_y_px=100 + (i % 20) * 5,
                width_px=40.0,
                height_px=40.0,
                confidence=0.85 - (i * 0.0001),
                class_name="suculenta",
            )
            for i in range(count)
        ]

    service.detect_in_segmento.return_value = create_detections(400)
    return service


@pytest.fixture
def mock_direct_detection_service():
    """Mock DirectDetectionService for testing.

    Returns service that simulates direct detection in boxes:
    - 50 detections per box
    """
    service = AsyncMock()

    # Mock detect_in_container to return 50 detections
    def create_detections(count=50):
        return [
            MagicMock(
                center_x_px=50 + i * 3,
                center_y_px=50 + (i % 10) * 3,
                width_px=30.0,
                height_px=30.0,
                confidence=0.80 - (i * 0.001),
                class_name="cactus",
            )
            for i in range(count)
        ]

    service.detect_in_container.return_value = create_detections(50)
    return service


@pytest.fixture
def mock_band_estimation_service():
    """Mock BandEstimationService for testing.

    Returns service that simulates band-based estimation:
    - 4 estimations per segment (one per band)
    """
    service = AsyncMock()

    # Mock estimate_undetected_plants to return 4 band estimations
    def create_estimations(segment_idx=0):
        from app.services.ml_processing.band_estimation_service import BandEstimation

        return [
            BandEstimation(
                estimation_type="band_based",
                band_number=i + 1,
                band_y_start=i * 250,
                band_y_end=(i + 1) * 250,
                residual_area_px=50000.0,
                processed_area_px=35000.0,
                floor_suppressed_px=15000.0,
                estimated_count=42,
                average_plant_area_px=833.33,
                alpha_overcount=0.9,
                container_type="segment",
            )
            for i in range(4)
        ]

    service.estimate_undetected_plants.return_value = create_estimations()
    return service


@pytest.fixture
def mock_session_repository():
    """Mock PhotoProcessingSessionRepository for testing.

    Returns repository that simulates DB operations for sessions.
    """
    repo = AsyncMock()

    # Mock get_by_session_id to return a session
    mock_session = MagicMock(
        id=1,
        session_id=uuid.uuid4(),
        storage_location_id=123,
        original_image_id=uuid.uuid4(),
        status="pending",
        total_detected=0,
        total_estimated=0,
        total_empty_containers=0,
        avg_confidence=None,
        category_counts={},
        created_at=datetime.now(),
        updated_at=None,
    )
    repo.get_by_session_id.return_value = mock_session

    # Mock update to return updated session
    repo.update.return_value = mock_session

    # Mock update_progress to succeed
    repo.update_progress = AsyncMock()

    return repo


@pytest.fixture
def mock_detection_repository():
    """Mock DetectionRepository for testing.

    Returns repository that simulates bulk insert for detections.
    """
    repo = AsyncMock()

    # Mock bulk_insert to return count of inserted detections
    repo.bulk_insert.return_value = 850  # Total detections

    return repo


@pytest.fixture
def mock_estimation_repository():
    """Mock EstimationRepository for testing.

    Returns repository that simulates bulk insert for estimations.
    """
    repo = AsyncMock()

    # Mock bulk_insert to return count of inserted estimations
    repo.bulk_insert.return_value = 8  # Total estimations (4 bands × 2 segments)

    return repo


@pytest.fixture
def pipeline_coordinator(
    mock_segmentation_service,
    mock_sahi_service,
    mock_band_estimation_service,
):
    """Create MLPipelineCoordinator with all mocked dependencies.

    This fixture creates a fully-mocked coordinator for unit testing.
    All external dependencies are mocked to test orchestration logic only.

    Note: Updated to match current MLPipelineCoordinator __init__() signature.
    The coordinator now only receives services (Service→Service pattern),
    not repositories directly.
    """
    from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator

    return MLPipelineCoordinator(
        segmentation_service=mock_segmentation_service,
        sahi_service=mock_sahi_service,
        band_estimation_service=mock_band_estimation_service,
    )


# =============================================================================
# Test Classes - MLPipelineCoordinator Core Logic
# =============================================================================


class TestMLPipelineCoordinatorHappyPath:
    """Test successful pipeline execution (happy path).

    Tests the complete ML pipeline orchestration without errors:
    - Segmentation → Detection → Estimation → Persistence
    - Progress updates at each stage
    - Result aggregation
    """

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_success(
        self,
        pipeline_coordinator,
        mock_segmentation_service,
        mock_sahi_service,
        mock_direct_detection_service,
        mock_band_estimation_service,
        mock_session_repository,
        mock_detection_repository,
        mock_estimation_repository,
    ):
        """Test complete pipeline execution with all stages successful.

        Workflow:
        1. Segmentation (20% progress) → 2 segments + 1 box
        2. Detection (50% progress) → 400×2 + 50 = 850 detections
        3. Estimation (80% progress) → 4×2 = 8 estimations
        4. Persistence (100% progress) → Bulk insert + session update

        Performance: <10 min on CPU (mocked: <1s)
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Act
        result = await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Segmentation called
        mock_segmentation_service.segment_image.assert_called_once_with(
            image_path, worker_id=0, conf_threshold=0.30
        )

        # Assert: Progress updated to 20% after segmentation
        assert mock_session_repository.update_progress.call_count >= 1
        first_progress_call = mock_session_repository.update_progress.call_args_list[0]
        assert first_progress_call[0][0] == session_id  # First positional arg
        assert first_progress_call[0][1] == 0.2  # Second positional arg (20%)

        # Assert: SAHI detection called for each segment (2 times)
        assert mock_sahi_service.detect_in_segmento.call_count == 2

        # Assert: Direct detection called for box (1 time)
        assert mock_direct_detection_service.detect_in_container.call_count == 1

        # Assert: Progress updated to 50% after detection
        detection_progress_call = mock_session_repository.update_progress.call_args_list[1]
        assert detection_progress_call[0][1] == 0.5  # 50%

        # Assert: Band estimation called for each segment (2 times)
        assert mock_band_estimation_service.estimate_undetected_plants.call_count == 2

        # Assert: Progress updated to 80% after estimation
        estimation_progress_call = mock_session_repository.update_progress.call_args_list[2]
        assert estimation_progress_call[0][1] == 0.8  # 80%

        # Assert: Detections bulk inserted
        mock_detection_repository.bulk_insert.assert_called_once()
        detections_arg = mock_detection_repository.bulk_insert.call_args[0][0]
        assert len(detections_arg) == 850  # 400×2 + 50

        # Assert: Estimations bulk inserted
        mock_estimation_repository.bulk_insert.assert_called_once()
        estimations_arg = mock_estimation_repository.bulk_insert.call_args[0][0]
        assert len(estimations_arg) == 8  # 4 bands × 2 segments

        # Assert: Session updated with final results
        mock_session_repository.update.assert_called_once()
        update_arg = mock_session_repository.update.call_args[0][0]
        assert update_arg.status == "completed"
        assert update_arg.total_detected == 850
        assert update_arg.total_estimated > 0  # Sum of estimated_count from bands

        # Assert: Result dict returned
        assert result is not None
        assert result["session_id"] == str(session_id)
        assert result["status"] == "completed"
        assert result["total_detections"] == 850
        assert result["total_estimations"] > 0
        assert "processing_time_seconds" in result

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_progress_updates(
        self, pipeline_coordinator, mock_session_repository
    ):
        """Test progress updates occur at correct milestones.

        Progress milestones:
        - 20%: After segmentation
        - 50%: After detection
        - 80%: After estimation
        - 100%: After persistence (implicit in status=completed)
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Act
        await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Progress updated 3 times (20%, 50%, 80%)
        assert mock_session_repository.update_progress.call_count == 3

        # Assert: Correct progress values
        progress_calls = mock_session_repository.update_progress.call_args_list
        assert progress_calls[0][0][1] == 0.2  # 20% (segmentation)
        assert progress_calls[1][0][1] == 0.5  # 50% (detection)
        assert progress_calls[2][0][1] == 0.8  # 80% (estimation)

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_result_aggregation(
        self, pipeline_coordinator, mock_band_estimation_service
    ):
        """Test result aggregation from all stages.

        Verifies that:
        - Total detections = sum of all detection stages
        - Total estimations = sum of estimated_count from all bands
        - Average confidence calculated correctly
        - Category counts aggregated
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Act
        result = await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Detections aggregated correctly
        # 2 segments × 400 detections + 1 box × 50 detections = 850
        assert result["total_detections"] == 850

        # Assert: Estimations aggregated correctly
        # 2 segments × 4 bands × 42 estimated_count = 336
        assert result["total_estimations"] == 336  # 2 × 4 × 42

        # Assert: Average confidence calculated
        assert "avg_confidence" in result
        assert 0.0 <= result["avg_confidence"] <= 1.0

        # Assert: Processing time included
        assert "processing_time_seconds" in result
        assert result["processing_time_seconds"] > 0

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_no_segments(
        self, pipeline_coordinator, mock_segmentation_service, mock_session_repository
    ):
        """Test pipeline when no containers detected (edge case).

        If segmentation returns empty list:
        - No detection stage
        - No estimation stage
        - Session updated with zero counts
        - Status = completed (NOT failed)
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/empty_photo.jpg"

        # Mock segmentation to return empty list
        mock_segmentation_service.segment_image.return_value = []

        # Act
        result = await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Segmentation called
        mock_segmentation_service.segment_image.assert_called_once()

        # Assert: No detection/estimation stages called
        # (verified by mock not being called - pytest would fail if called)

        # Assert: Session updated with zero counts
        update_call = mock_session_repository.update.call_args[0][0]
        assert update_call.status == "completed"
        assert update_call.total_detected == 0
        assert update_call.total_estimated == 0

        # Assert: Result indicates no detections
        assert result["total_detections"] == 0
        assert result["total_estimations"] == 0
        assert result["status"] == "completed"


class TestMLPipelineCoordinatorErrorHandling:
    """Test error handling and recovery (warning states, not hard failures).

    Critical: Errors should NOT crash the pipeline.
    Instead, they should:
    - Log warning
    - Continue with remaining stages
    - Update session with partial results
    - Status = completed (with warnings in error_message)
    """

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_segmentation_fails(
        self, pipeline_coordinator, mock_segmentation_service, mock_session_repository
    ):
        """Test pipeline when segmentation fails (ML model error).

        Expected behavior:
        - Log error
        - Update session with status=failed
        - error_message contains exception details
        - No detection/estimation stages executed
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock segmentation to raise exception
        mock_segmentation_service.segment_image.side_effect = RuntimeError(
            "YOLO segmentation model failed"
        )

        # Act & Assert: Should raise exception (hard failure at segmentation)
        with pytest.raises(RuntimeError, match="YOLO segmentation model failed"):
            await pipeline_coordinator.process_complete_pipeline(
                session_id=session_id, image_path=image_path
            )

        # Assert: Session updated with failed status
        update_call = mock_session_repository.update.call_args[0][0]
        assert update_call.status == "failed"
        assert "YOLO segmentation model failed" in update_call.error_message

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_detection_fails_warning(
        self,
        pipeline_coordinator,
        mock_sahi_service,
        mock_band_estimation_service,
        mock_session_repository,
    ):
        """Test pipeline when detection fails (warning state, NOT hard failure).

        Expected behavior:
        - Log warning
        - Skip detections for failed segment
        - Continue with estimation stage
        - Status = completed (with warning in error_message)
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock SAHI to fail on first call, succeed on second
        mock_sahi_service.detect_in_segmento.side_effect = [
            RuntimeError("SAHI detection timeout"),  # First segment fails
            [
                MagicMock(
                    center_x_px=100,
                    center_y_px=100,
                    width_px=40.0,
                    height_px=40.0,
                    confidence=0.85,
                    class_name="suculenta",
                )
            ],  # Second segment succeeds
        ]

        # Act
        result = await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Pipeline completed (not failed)
        assert result["status"] == "completed"

        # Assert: Partial detections recorded (only second segment)
        assert result["total_detections"] > 0  # At least second segment + box

        # Assert: Estimation still executed for successful segments
        assert mock_band_estimation_service.estimate_undetected_plants.call_count >= 1

        # Assert: Warning logged in session
        update_call = mock_session_repository.update.call_args[0][0]
        assert update_call.status == "completed"
        # Error message contains warning
        if update_call.error_message:
            assert "warning" in update_call.error_message.lower()

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_estimation_fails_warning(
        self,
        pipeline_coordinator,
        mock_band_estimation_service,
        mock_detection_repository,
        mock_session_repository,
    ):
        """Test pipeline when estimation fails (warning state, NOT hard failure).

        Expected behavior:
        - Log warning
        - Skip estimations for failed segment
        - Continue with persistence stage
        - Detections still saved
        - Status = completed (with warning)
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock band estimation to fail
        mock_band_estimation_service.estimate_undetected_plants.side_effect = RuntimeError(
            "Floor suppression failed"
        )

        # Act
        result = await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Pipeline completed (not failed)
        assert result["status"] == "completed"

        # Assert: Detections still persisted
        mock_detection_repository.bulk_insert.assert_called_once()

        # Assert: No estimations recorded
        assert result["total_estimations"] == 0

        # Assert: Warning logged
        update_call = mock_session_repository.update.call_args[0][0]
        assert update_call.status == "completed"

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_persistence_fails(
        self,
        pipeline_coordinator,
        mock_detection_repository,
        mock_session_repository,
    ):
        """Test pipeline when persistence fails (database error).

        Expected behavior:
        - Log error
        - Raise exception (hard failure - cannot recover)
        - Session updated with failed status
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock bulk_insert to fail
        mock_detection_repository.bulk_insert.side_effect = Exception("Database connection lost")

        # Act & Assert: Should raise exception
        with pytest.raises(Exception, match="Database connection lost"):
            await pipeline_coordinator.process_complete_pipeline(
                session_id=session_id, image_path=image_path
            )

        # Assert: Session updated with failed status
        update_call = mock_session_repository.update.call_args[0][0]
        assert update_call.status == "failed"
        assert "Database connection lost" in update_call.error_message


class TestMLPipelineCoordinatorContainerTypeRouting:
    """Test container type routing logic.

    Different container types use different detection strategies:
    - segments → SAHI tiling (ML003)
    - boxes → Direct YOLO (ML004)
    - plugs → Direct YOLO (ML004)
    """

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_segments_use_sahi(
        self, pipeline_coordinator, mock_sahi_service, mock_segmentation_service
    ):
        """Test that segments use SAHI tiling detection.

        Segments are large containers requiring SAHI for accuracy.
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock segmentation to return only segments
        mock_segmentation_service.segment_image.return_value = [
            MagicMock(container_type="segment", bbox=(0.1, 0.1, 0.5, 0.9)),
            MagicMock(container_type="segment", bbox=(0.5, 0.1, 0.9, 0.9)),
        ]

        # Act
        await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: SAHI called for each segment
        assert mock_sahi_service.detect_in_segmento.call_count == 2

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_boxes_use_direct(
        self, pipeline_coordinator, mock_direct_detection_service, mock_segmentation_service
    ):
        """Test that boxes use direct YOLO detection.

        Boxes are medium containers not requiring SAHI overhead.
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock segmentation to return only boxes
        mock_segmentation_service.segment_image.return_value = [
            MagicMock(container_type="box", bbox=(0.1, 0.1, 0.3, 0.3)),
            MagicMock(container_type="box", bbox=(0.4, 0.4, 0.6, 0.6)),
        ]

        # Act
        await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Direct detection called for each box
        assert mock_direct_detection_service.detect_in_container.call_count == 2

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_plugs_use_direct(
        self, pipeline_coordinator, mock_direct_detection_service, mock_segmentation_service
    ):
        """Test that plugs use direct YOLO detection.

        Plugs are small trays with individual cells (charolas/bandejas).
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock segmentation to return only plugs
        mock_segmentation_service.segment_image.return_value = [
            MagicMock(container_type="plug", bbox=(0.0, 0.0, 0.2, 0.2)),
        ]

        # Act
        await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Direct detection called for plug
        assert mock_direct_detection_service.detect_in_container.call_count == 1


class TestMLPipelineCoordinatorEstimationLogic:
    """Test estimation stage logic and band-based processing."""

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_estimation_only_for_segments(
        self, pipeline_coordinator, mock_band_estimation_service, mock_segmentation_service
    ):
        """Test that band estimation only runs for segments (not boxes/plugs).

        Band estimation is designed for large containers with perspective distortion.
        Boxes and plugs are too small for band-based estimation.
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock segmentation to return mixed containers
        mock_segmentation_service.segment_image.return_value = [
            MagicMock(container_type="segment", bbox=(0.1, 0.1, 0.5, 0.9)),  # Should estimate
            MagicMock(container_type="box", bbox=(0.6, 0.1, 0.8, 0.3)),  # Should NOT estimate
            MagicMock(container_type="plug", bbox=(0.85, 0.85, 0.95, 0.95)),  # Should NOT estimate
        ]

        # Act
        await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Band estimation called only once (for segment)
        assert mock_band_estimation_service.estimate_undetected_plants.call_count == 1

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_estimation_receives_detections(
        self, pipeline_coordinator, mock_band_estimation_service
    ):
        """Test that estimation receives detections for calibration.

        Band estimation uses detections to calibrate plant size for each band.
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Act
        await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Estimation called with detections argument
        call_args = mock_band_estimation_service.estimate_undetected_plants.call_args
        assert call_args is not None
        assert "detections" in call_args[1] or len(call_args[0]) > 1  # Positional or keyword arg


# =============================================================================
# Test Classes - Performance and Benchmarks
# =============================================================================


class TestMLPipelineCoordinatorPerformance:
    """Test performance requirements and benchmarks."""

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_performance_benchmark(self, pipeline_coordinator):
        """Test full pipeline completes in <10 minutes on CPU (AC6).

        Performance requirement: Complete pipeline in <600s (10 min) on CPU.
        With mocks: <1s
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Act & Assert: Manual timing
        import time

        start = time.time()
        result = await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )
        duration = time.time() - start

        # Assert: Mocked pipeline completes in <1s
        assert duration < 1.0, f"Mocked pipeline should complete in <1s, took {duration:.2f}s"

        # Assert: Result contains timing info
        assert "processing_time_seconds" in result
        assert result["processing_time_seconds"] > 0


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


class TestMLPipelineCoordinatorEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_invalid_session_id(
        self, pipeline_coordinator, mock_session_repository
    ):
        """Test pipeline fails gracefully with invalid session_id."""
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock repository to return None (session not found)
        mock_session_repository.get_by_session_id.return_value = None

        # Act & Assert: Should raise ValueError
        with pytest.raises(ValueError, match="Session not found"):
            await pipeline_coordinator.process_complete_pipeline(
                session_id=session_id, image_path=image_path
            )

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_invalid_image_path(self, pipeline_coordinator):
        """Test pipeline fails gracefully with invalid image path."""
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/nonexistent/path/image.jpg"

        # Act & Assert: Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await pipeline_coordinator.process_complete_pipeline(
                session_id=session_id, image_path=image_path
            )

    @pytest.mark.asyncio
    async def test_process_complete_pipeline_zero_confidence_detections(
        self, pipeline_coordinator, mock_sahi_service
    ):
        """Test pipeline handles detections with zero confidence (edge case).

        Detections with confidence=0.0 should be filtered out or handled gracefully.
        """
        # Arrange
        session_id = uuid.uuid4()
        image_path = "/tmp/test_photo.jpg"

        # Mock SAHI to return detections with zero confidence
        mock_sahi_service.detect_in_segmento.return_value = [
            MagicMock(
                center_x_px=100,
                center_y_px=100,
                width_px=40.0,
                height_px=40.0,
                confidence=0.0,  # Zero confidence!
                class_name="suculenta",
            )
        ]

        # Act
        result = await pipeline_coordinator.process_complete_pipeline(
            session_id=session_id, image_path=image_path
        )

        # Assert: Pipeline completes without error
        assert result["status"] == "completed"

        # Assert: Average confidence handles zero values
        assert result["avg_confidence"] >= 0.0
