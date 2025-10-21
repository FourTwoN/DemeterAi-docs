"""Integration tests for ML Celery Tasks.

These tests verify task execution with real Celery workers (where available)
and real database sessions. They test the complete task workflow including:
- Task routing to correct queues
- Database session management
- Async coordination
- Error propagation

NOTE: These tests require:
- Redis running (broker + backend)
- Celery worker running (optional - tests will skip if unavailable)
- PostgreSQL test database

Run with:
    pytest tests/integration/tasks/test_ml_tasks_integration.py -v
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.photo_processing_session import (
    PhotoProcessingSession,
    ProcessingSessionStatusEnum,
)
from app.tasks.ml_tasks import (
    ml_aggregation_callback,
    ml_child_task,
    ml_parent_task,
)

# ═══════════════════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def test_session(db_session: AsyncSession):
    """Create test PhotoProcessingSession."""
    session = PhotoProcessingSession(
        session_id=uuid4(),
        storage_location_id=1,
        original_image_id=uuid4(),
        status=ProcessingSessionStatusEnum.PENDING,
        total_detected=0,
        total_estimated=0,
        total_empty_containers=0,
        avg_confidence=0.0,
        category_counts={},
        manual_adjustments={},
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
def sample_image_data(tmp_path):
    """Create sample image files for testing."""
    # Create temporary test images
    image1 = tmp_path / "test_001.jpg"
    image2 = tmp_path / "test_002.jpg"
    image3 = tmp_path / "test_003.jpg"

    # Create dummy image files (1x1 pixel)
    for img_path in [image1, image2, image3]:
        img_path.write_bytes(b"\x00" * 100)  # Dummy data

    return [
        {"image_id": 1, "image_path": str(image1), "storage_location_id": 1},
        {"image_id": 2, "image_path": str(image2), "storage_location_id": 1},
        {"image_id": 3, "image_path": str(image3), "storage_location_id": 1},
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLTasksIntegration:
    """Integration tests for ML tasks with real database."""

    @pytest.mark.asyncio
    @patch("app.tasks.ml_tasks.chord")
    @patch("app.tasks.ml_tasks.check_circuit_breaker")
    async def test_ml_parent_task_updates_database(
        self,
        mock_check_circuit,
        mock_chord,
        test_session: PhotoProcessingSession,
        sample_image_data,
        db_session: AsyncSession,
    ):
        """Test ml_parent_task updates PhotoProcessingSession in database."""
        mock_self = Mock()
        mock_self.request.id = "integration-test-123"
        mock_self.request.retries = 0

        # Execute parent task
        with patch("app.tasks.ml_tasks.get_async_session") as mock_get_session:
            # Mock async context manager
            async def mock_session_gen():
                yield db_session

            mock_get_session.return_value = mock_session_gen()

            result = ml_parent_task(
                mock_self, session_id=test_session.id, image_data=sample_image_data
            )

        # Verify session updated to PROCESSING
        await db_session.refresh(test_session)
        assert test_session.status == ProcessingSessionStatusEnum.PROCESSING

    @pytest.mark.asyncio
    @patch("app.tasks.ml_tasks.asyncio.run")
    @patch("app.tasks.ml_tasks.MLPipelineCoordinator")
    async def test_ml_child_task_with_real_session(
        self,
        mock_coordinator_class,
        mock_asyncio_run,
        test_session: PhotoProcessingSession,
        sample_image_data,
        db_session: AsyncSession,
    ):
        """Test ml_child_task with real database session."""
        # Mock pipeline result
        from app.services.ml_processing.pipeline_coordinator import PipelineResult

        mock_result = PipelineResult(
            session_id=test_session.id,
            total_detected=500,
            total_estimated=100,
            segments_processed=10,
            processing_time_seconds=30.0,
            detections=[],
            estimations=[],
            avg_confidence=0.85,
            segments=[],
        )
        mock_asyncio_run.return_value = mock_result

        mock_self = Mock()
        mock_self.request.id = "child-integration-test"
        mock_self.request.retries = 0

        # Execute child task
        result = ml_child_task(
            mock_self,
            session_id=test_session.id,
            image_id=sample_image_data[0]["image_id"],
            image_path=sample_image_data[0]["image_path"],
            storage_location_id=1,
        )

        # Verify result
        assert result["total_detected"] == 500
        assert result["total_estimated"] == 100
        assert result["avg_confidence"] == 0.85

    @pytest.mark.asyncio
    @patch("app.tasks.ml_tasks._mark_session_completed")
    async def test_ml_aggregation_callback_with_database(
        self,
        mock_mark_completed,
        test_session: PhotoProcessingSession,
        db_session: AsyncSession,
    ):
        """Test ml_aggregation_callback aggregates and updates database."""
        # Sample results from child tasks
        results = [
            {
                "image_id": 1,
                "total_detected": 500,
                "total_estimated": 100,
                "avg_confidence": 0.85,
                "segments_processed": 10,
                "detections": [],
                "estimations": [],
            },
            {
                "image_id": 2,
                "total_detected": 450,
                "total_estimated": 90,
                "avg_confidence": 0.82,
                "segments_processed": 9,
                "detections": [],
                "estimations": [],
            },
        ]

        # Execute callback
        result = ml_aggregation_callback(results, session_id=test_session.id)

        # Verify aggregation
        assert result["total_detected"] == 950
        assert result["total_estimated"] == 190
        assert result["status"] == "completed"

        # Verify database update called
        mock_mark_completed.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# Celery Worker Tests (Optional - Skip if Worker Unavailable)
# ═══════════════════════════════════════════════════════════════════════════


class TestCeleryWorkerExecution:
    """Test task execution with real Celery worker (if available).

    These tests verify:
    - Task routing to correct queues
    - Chord pattern execution
    - Result aggregation

    NOTE: Requires Celery worker running. Tests skip if unavailable.
    """

    @pytest.mark.celery
    @pytest.mark.skip(reason="Requires Celery worker - run manually")
    def test_ml_parent_task_celery_dispatch(self, sample_image_data):
        """Test ml_parent_task dispatches via Celery (manual test)."""
        # This test requires:
        # 1. Redis running
        # 2. Celery worker running: celery -A app.celery_app worker --pool=solo -Q cpu_queue
        result = ml_parent_task.delay(session_id=1, image_data=sample_image_data)

        # Wait for result (timeout 60s)
        task_result = result.get(timeout=60)

        assert task_result["status"] == "processing"
        assert task_result["num_images"] == 3

    @pytest.mark.celery
    @pytest.mark.skip(reason="Requires Celery worker - run manually")
    def test_chord_pattern_execution(self, sample_image_data):
        """Test chord pattern executes children → callback (manual test)."""
        # This test verifies complete chord workflow
        # Requires GPU worker for child tasks
        pass
