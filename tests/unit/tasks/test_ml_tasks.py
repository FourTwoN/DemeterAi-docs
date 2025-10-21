"""Unit tests for ML Celery Tasks (CEL004-CEL008).

Tests cover:
- CEL004: Chord pattern implementation
- CEL005: ML parent task (spawning children)
- CEL006: ML child task (pipeline execution)
- CEL007: Callback aggregation
- CEL008: Circuit breaker and retry logic

Test Strategy:
    - Unit tests mock external dependencies (DB, ML services, Celery primitives)
    - Focus on business logic, error handling, retry logic
    - Circuit breaker state management
    - Task routing verification
    - Integration tests (separate file) test real Celery execution

Coverage Target: ≥80%
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from celery.exceptions import Retry

from app.core.exceptions import (
    CircuitBreakerException,
    ValidationException,
)
from app.tasks import ml_tasks
from app.tasks.ml_tasks import (
    CIRCUIT_BREAKER_THRESHOLD,
    CIRCUIT_BREAKER_TIMEOUT,
    check_circuit_breaker,
    ml_aggregation_callback,
    ml_child_task,
    ml_parent_task,
    record_circuit_breaker_failure,
    record_circuit_breaker_success,
)

# ═══════════════════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def reset_circuit_breaker():
    """Reset circuit breaker state before each test."""
    ml_tasks.circuit_breaker_state = {
        "failures": 0,
        "last_failure_time": None,
        "state": "closed",
    }
    yield
    # Reset after test
    ml_tasks.circuit_breaker_state = {
        "failures": 0,
        "last_failure_time": None,
        "state": "closed",
    }


@pytest.fixture
def mock_session_service():
    """Mock PhotoProcessingSessionService."""
    with patch("app.tasks.ml_tasks.PhotoProcessingSessionService") as mock:
        service = Mock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_ml_coordinator():
    """Mock MLPipelineCoordinator."""
    with patch("app.tasks.ml_tasks.MLPipelineCoordinator") as mock:
        coordinator = Mock()
        mock.return_value = coordinator
        yield coordinator


@pytest.fixture
def sample_image_data():
    """Sample image data for parent task."""
    return [
        {"image_id": 1, "image_path": "/photos/001.jpg", "storage_location_id": 10},
        {"image_id": 2, "image_path": "/photos/002.jpg", "storage_location_id": 10},
        {"image_id": 3, "image_path": "/photos/003.jpg", "storage_location_id": 10},
    ]


@pytest.fixture
def sample_pipeline_result():
    """Sample PipelineResult from ML pipeline."""
    from app.services.ml_processing.pipeline_coordinator import PipelineResult

    return PipelineResult(
        session_id=123,
        total_detected=842,
        total_estimated=158,
        segments_processed=15,
        processing_time_seconds=45.6,
        detections=[
            {"bbox": [100, 200, 50, 50], "confidence": 0.87, "class_id": 0},
            {"bbox": [150, 250, 55, 55], "confidence": 0.92, "class_id": 0},
        ],
        estimations=[
            {"band_id": 1, "estimated_count": 78, "density": 0.42},
            {"band_id": 2, "estimated_count": 80, "density": 0.45},
        ],
        avg_confidence=0.87,
        segments=[],
    )


# ═══════════════════════════════════════════════════════════════════════════
# CEL008: Circuit Breaker Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCircuitBreaker:
    """Test circuit breaker functionality (CEL008)."""

    def test_check_circuit_breaker_closed_state(self, reset_circuit_breaker):
        """Test circuit breaker allows requests when CLOSED."""
        # Should not raise exception
        check_circuit_breaker()

    def test_check_circuit_breaker_open_state(self, reset_circuit_breaker):
        """Test circuit breaker rejects requests when OPEN."""
        # Manually open circuit
        ml_tasks.circuit_breaker_state["state"] = "open"
        ml_tasks.circuit_breaker_state["failures"] = 5
        ml_tasks.circuit_breaker_state["last_failure_time"] = datetime.utcnow()

        with pytest.raises(CircuitBreakerException) as exc_info:
            check_circuit_breaker()

        assert "Circuit breaker OPEN" in str(exc_info.value)

    def test_check_circuit_breaker_half_open_allows_request(self, reset_circuit_breaker):
        """Test circuit breaker allows test request when HALF_OPEN."""
        # Set to half_open
        ml_tasks.circuit_breaker_state["state"] = "half_open"

        # Should not raise exception (allows test request)
        check_circuit_breaker()

    def test_check_circuit_breaker_transitions_to_half_open_after_timeout(
        self, reset_circuit_breaker
    ):
        """Test circuit breaker transitions OPEN → HALF_OPEN after cooldown."""
        # Open circuit with old failure time (beyond cooldown)
        ml_tasks.circuit_breaker_state["state"] = "open"
        ml_tasks.circuit_breaker_state["failures"] = 5
        ml_tasks.circuit_breaker_state["last_failure_time"] = datetime.utcnow() - timedelta(
            seconds=CIRCUIT_BREAKER_TIMEOUT + 10
        )

        # Should transition to half_open and not raise
        check_circuit_breaker()
        assert ml_tasks.circuit_breaker_state["state"] == "half_open"

    def test_record_circuit_breaker_success_resets_failures(self, reset_circuit_breaker):
        """Test successful execution resets failure counter."""
        ml_tasks.circuit_breaker_state["failures"] = 2

        record_circuit_breaker_success()

        assert ml_tasks.circuit_breaker_state["failures"] == 0
        assert ml_tasks.circuit_breaker_state["state"] == "closed"

    def test_record_circuit_breaker_success_closes_half_open_circuit(self, reset_circuit_breaker):
        """Test success in HALF_OPEN state closes circuit."""
        ml_tasks.circuit_breaker_state["state"] = "half_open"
        ml_tasks.circuit_breaker_state["failures"] = 3

        record_circuit_breaker_success()

        assert ml_tasks.circuit_breaker_state["state"] == "closed"
        assert ml_tasks.circuit_breaker_state["failures"] == 0

    def test_record_circuit_breaker_failure_increments_counter(self, reset_circuit_breaker):
        """Test failure increments failure counter."""
        assert ml_tasks.circuit_breaker_state["failures"] == 0

        record_circuit_breaker_failure()

        assert ml_tasks.circuit_breaker_state["failures"] == 1
        assert ml_tasks.circuit_breaker_state["last_failure_time"] is not None

    def test_record_circuit_breaker_failure_opens_after_threshold(self, reset_circuit_breaker):
        """Test circuit opens after reaching failure threshold."""
        # Record failures up to threshold
        for _ in range(CIRCUIT_BREAKER_THRESHOLD):
            record_circuit_breaker_failure()

        assert ml_tasks.circuit_breaker_state["state"] == "open"
        assert ml_tasks.circuit_breaker_state["failures"] == CIRCUIT_BREAKER_THRESHOLD


# ═══════════════════════════════════════════════════════════════════════════
# CEL005: ML Parent Task Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLParentTask:
    """Test ML parent task (CEL004, CEL005)."""

    @patch("app.tasks.ml_tasks.chord")
    @patch("app.tasks.ml_tasks._mark_session_processing")
    @patch("app.tasks.ml_tasks.check_circuit_breaker")
    def test_ml_parent_task_success(
        self,
        mock_check_circuit,
        mock_mark_processing,
        mock_chord,
        sample_image_data,
        reset_circuit_breaker,
    ):
        """Test ML parent task successfully spawns children via chord."""
        # Use apply() to call task synchronously with mocked request
        result = ml_parent_task.apply(kwargs={"session_id": 123, "image_data": sample_image_data})

        # Verify circuit breaker checked
        mock_check_circuit.assert_called_once()

        # Verify session marked as processing
        assert mock_mark_processing.call_count == 1

        # Verify chord called (children + callback)
        assert mock_chord.call_count == 1

        # Verify result
        assert result.result["session_id"] == 123
        assert result.result["num_images"] == 3
        assert result.result["status"] == "processing"

    @patch("app.tasks.ml_tasks.check_circuit_breaker")
    @patch("app.tasks.ml_tasks._mark_session_failed")
    def test_ml_parent_task_empty_image_data(
        self, mock_mark_failed, mock_check_circuit, reset_circuit_breaker
    ):
        """Test ML parent task raises ValidationException for empty image_data."""
        mock_self = Mock()
        mock_self.request.id = "parent-task-123"

        with pytest.raises(ValidationException) as exc_info:
            ml_parent_task(mock_self, session_id=123, image_data=[])

        assert "image_data cannot be empty" in str(exc_info.value)
        mock_mark_failed.assert_called_once()

    @patch("app.tasks.ml_tasks.check_circuit_breaker")
    @patch("app.tasks.ml_tasks._mark_session_failed")
    def test_ml_parent_task_circuit_breaker_open(
        self, mock_mark_failed, mock_check_circuit, sample_image_data, reset_circuit_breaker
    ):
        """Test ML parent task fails fast when circuit breaker is open."""
        mock_check_circuit.side_effect = CircuitBreakerException(reason="Too many failures")
        mock_self = Mock()

        with pytest.raises(CircuitBreakerException):
            ml_parent_task(mock_self, session_id=123, image_data=sample_image_data)

        mock_mark_failed.assert_called_once()

    @patch("app.tasks.ml_tasks.chord")
    @patch("app.tasks.ml_tasks._mark_session_processing")
    @patch("app.tasks.ml_tasks.check_circuit_breaker")
    @patch("app.tasks.ml_tasks.record_circuit_breaker_failure")
    @patch("app.tasks.ml_tasks._mark_session_failed")
    def test_ml_parent_task_retries_on_failure(
        self,
        mock_mark_failed,
        mock_record_failure,
        mock_check_circuit,
        mock_mark_processing,
        mock_chord,
        sample_image_data,
        reset_circuit_breaker,
    ):
        """Test ML parent task retries with exponential backoff on failure."""
        mock_self = Mock()
        mock_self.request.id = "parent-task-123"
        mock_self.request.retries = 1  # Second attempt
        mock_self.retry = Mock(side_effect=Retry())

        # Simulate chord failure
        mock_chord.side_effect = Exception("Chord dispatch failed")

        with pytest.raises(Retry):
            ml_parent_task(mock_self, session_id=123, image_data=sample_image_data)

        # Verify retry with exponential backoff (2^1 = 2 seconds)
        mock_self.retry.assert_called_once()
        retry_call = mock_self.retry.call_args
        assert retry_call[1]["countdown"] == 2

        # Verify failure recorded
        mock_record_failure.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# CEL006: ML Child Task Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLChildTask:
    """Test ML child task (CEL006)."""

    @patch("app.tasks.ml_tasks.asyncio.run")
    @patch("app.tasks.ml_tasks.MLPipelineCoordinator")
    @patch("app.tasks.ml_tasks.Path")
    @patch("app.tasks.ml_tasks.record_circuit_breaker_success")
    def test_ml_child_task_success(
        self,
        mock_record_success,
        mock_path,
        mock_coordinator_class,
        mock_asyncio_run,
        sample_pipeline_result,
        reset_circuit_breaker,
    ):
        """Test ML child task successfully processes image through pipeline."""
        # Mock file exists
        mock_image_file = Mock()
        mock_image_file.exists.return_value = True
        mock_path.return_value = mock_image_file

        # Mock pipeline result
        mock_asyncio_run.return_value = sample_pipeline_result

        # Mock coordinator
        mock_coordinator = Mock()
        mock_coordinator_class.return_value = mock_coordinator

        # Mock task instance
        mock_self = Mock()
        mock_self.request.id = "child-task-456"
        mock_self.request.retries = 0

        # Execute
        result = ml_child_task(
            mock_self,
            session_id=123,
            image_id=1,
            image_path="/photos/001.jpg",
            storage_location_id=10,
        )

        # Verify pipeline called
        mock_asyncio_run.assert_called_once()

        # Verify circuit breaker success recorded
        mock_record_success.assert_called_once()

        # Verify result
        assert result["image_id"] == 1
        assert result["total_detected"] == 842
        assert result["total_estimated"] == 158
        assert result["avg_confidence"] == 0.87

    @patch("app.tasks.ml_tasks.Path")
    @patch("app.tasks.ml_tasks.record_circuit_breaker_failure")
    def test_ml_child_task_image_not_found(
        self, mock_record_failure, mock_path, reset_circuit_breaker
    ):
        """Test ML child task raises FileNotFoundError if image doesn't exist."""
        # Mock file doesn't exist
        mock_image_file = Mock()
        mock_image_file.exists.return_value = False
        mock_path.return_value = mock_image_file

        mock_self = Mock()

        with pytest.raises(FileNotFoundError):
            ml_child_task(
                mock_self,
                session_id=123,
                image_id=1,
                image_path="/photos/missing.jpg",
                storage_location_id=10,
            )

        # Verify failure recorded (don't retry file not found)
        mock_record_failure.assert_called_once()

    @patch("app.tasks.ml_tasks.asyncio.run")
    @patch("app.tasks.ml_tasks.MLPipelineCoordinator")
    @patch("app.tasks.ml_tasks.Path")
    @patch("app.tasks.ml_tasks.record_circuit_breaker_failure")
    def test_ml_child_task_retries_on_ml_failure(
        self,
        mock_record_failure,
        mock_path,
        mock_coordinator_class,
        mock_asyncio_run,
        reset_circuit_breaker,
    ):
        """Test ML child task retries with exponential backoff on ML failure."""
        # Mock file exists
        mock_image_file = Mock()
        mock_image_file.exists.return_value = True
        mock_path.return_value = mock_image_file

        # Mock pipeline failure
        mock_asyncio_run.side_effect = RuntimeError("YOLO model failed")

        # Mock task instance
        mock_self = Mock()
        mock_self.request.id = "child-task-456"
        mock_self.request.retries = 1  # Second attempt
        mock_self.max_retries = 3
        mock_self.retry = Mock(side_effect=Retry())

        with pytest.raises(Retry):
            ml_child_task(
                mock_self,
                session_id=123,
                image_id=1,
                image_path="/photos/001.jpg",
                storage_location_id=10,
            )

        # Verify retry with exponential backoff (2^1 = 2 seconds)
        mock_self.retry.assert_called_once()
        retry_call = mock_self.retry.call_args
        assert retry_call[1]["countdown"] == 2

        # Verify failure recorded
        mock_record_failure.assert_called_once()

    @patch("app.tasks.ml_tasks.asyncio.run")
    @patch("app.tasks.ml_tasks.MLPipelineCoordinator")
    @patch("app.tasks.ml_tasks.Path")
    @patch("app.tasks.ml_tasks.record_circuit_breaker_failure")
    def test_ml_child_task_exponential_backoff(
        self,
        mock_record_failure,
        mock_path,
        mock_coordinator_class,
        mock_asyncio_run,
        reset_circuit_breaker,
    ):
        """Test ML child task uses exponential backoff (2s, 4s, 8s)."""
        mock_image_file = Mock()
        mock_image_file.exists.return_value = True
        mock_path.return_value = mock_image_file

        mock_asyncio_run.side_effect = RuntimeError("Transient error")

        # Test retry attempts with different retry counts
        for retry_count, expected_countdown in [(0, 1), (1, 2), (2, 4)]:
            mock_self = Mock()
            mock_self.request.retries = retry_count
            mock_self.max_retries = 3
            mock_self.retry = Mock(side_effect=Retry())

            with pytest.raises(Retry):
                ml_child_task(
                    mock_self,
                    session_id=123,
                    image_id=1,
                    image_path="/photos/001.jpg",
                    storage_location_id=10,
                )

            retry_call = mock_self.retry.call_args
            assert retry_call[1]["countdown"] == expected_countdown


# ═══════════════════════════════════════════════════════════════════════════
# CEL007: Callback Aggregation Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMLAggregationCallback:
    """Test ML aggregation callback (CEL007)."""

    @patch("app.tasks.ml_tasks._mark_session_completed")
    def test_ml_aggregation_callback_all_success(self, mock_mark_completed):
        """Test callback aggregates all successful child results."""
        results = [
            {
                "image_id": 1,
                "total_detected": 842,
                "total_estimated": 158,
                "avg_confidence": 0.87,
                "segments_processed": 15,
                "detections": [],
                "estimations": [],
            },
            {
                "image_id": 2,
                "total_detected": 756,
                "total_estimated": 134,
                "avg_confidence": 0.82,
                "segments_processed": 12,
                "detections": [],
                "estimations": [],
            },
            {
                "image_id": 3,
                "total_detected": 901,
                "total_estimated": 99,
                "avg_confidence": 0.91,
                "segments_processed": 18,
                "detections": [],
                "estimations": [],
            },
        ]

        result = ml_aggregation_callback(results, session_id=123)

        # Verify aggregation
        assert result["session_id"] == 123
        assert result["num_images_processed"] == 3
        assert result["total_detected"] == 842 + 756 + 901
        assert result["total_estimated"] == 158 + 134 + 99
        assert result["avg_confidence"] == pytest.approx((0.87 + 0.82 + 0.91) / 3)
        assert result["status"] == "completed"

        # Verify session marked as completed
        mock_mark_completed.assert_called_once()

    @patch("app.tasks.ml_tasks._mark_session_completed")
    def test_ml_aggregation_callback_partial_success(self, mock_mark_completed):
        """Test callback handles partial failures (some children failed)."""
        results = [
            {
                "image_id": 1,
                "total_detected": 842,
                "total_estimated": 158,
                "avg_confidence": 0.87,
                "segments_processed": 15,
                "detections": [],
                "estimations": [],
            },
            None,  # Child task failed
            {
                "image_id": 3,
                "total_detected": 901,
                "total_estimated": 99,
                "avg_confidence": 0.91,
                "segments_processed": 18,
                "detections": [],
                "estimations": [],
            },
        ]

        result = ml_aggregation_callback(results, session_id=123)

        # Verify only valid results aggregated
        assert result["num_images_processed"] == 2
        assert result["total_detected"] == 842 + 901
        assert result["total_estimated"] == 158 + 99
        assert result["status"] == "warning"  # Partial success

    @patch("app.tasks.ml_tasks._mark_session_failed")
    def test_ml_aggregation_callback_all_failed(self, mock_mark_failed):
        """Test callback handles case where all children failed."""
        results = [None, None, None]  # All failed

        result = ml_aggregation_callback(results, session_id=123)

        # Verify session marked as failed
        assert result["status"] == "failed"
        assert result["num_images_processed"] == 0
        mock_mark_failed.assert_called_once()

    @patch("app.tasks.ml_tasks._mark_session_completed")
    def test_ml_aggregation_callback_aggregates_detections(self, mock_mark_completed):
        """Test callback aggregates detections/estimations from all children."""
        results = [
            {
                "image_id": 1,
                "total_detected": 10,
                "total_estimated": 5,
                "avg_confidence": 0.85,
                "segments_processed": 2,
                "detections": [{"bbox": [1, 2, 3, 4], "confidence": 0.9}],
                "estimations": [{"band_id": 1, "count": 5}],
            },
            {
                "image_id": 2,
                "total_detected": 8,
                "total_estimated": 3,
                "avg_confidence": 0.80,
                "segments_processed": 1,
                "detections": [{"bbox": [5, 6, 7, 8], "confidence": 0.8}],
                "estimations": [{"band_id": 2, "count": 3}],
            },
        ]

        result = ml_aggregation_callback(results, session_id=123)

        # Verify aggregation (detections/estimations combined)
        assert result["total_detected"] == 18
        assert result["total_estimated"] == 8


# ═══════════════════════════════════════════════════════════════════════════
# Helper Function Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestHelperFunctions:
    """Test helper functions (_mark_session_* methods)."""

    @patch("app.tasks.ml_tasks.asyncio.run")
    @patch("app.tasks.ml_tasks.get_async_session")
    def test_mark_session_processing(self, mock_get_session, mock_asyncio_run):
        """Test _mark_session_processing helper."""
        from app.tasks.ml_tasks import _mark_session_processing

        _mark_session_processing(session_id=123, celery_task_id="task-456")

        # Verify asyncio.run called
        mock_asyncio_run.assert_called_once()

    @patch("app.tasks.ml_tasks.asyncio.run")
    @patch("app.tasks.ml_tasks.get_async_session")
    def test_mark_session_completed(self, mock_get_session, mock_asyncio_run):
        """Test _mark_session_completed helper."""
        from app.tasks.ml_tasks import _mark_session_completed

        _mark_session_completed(
            session_id=123,
            total_detected=1000,
            total_estimated=200,
            total_empty_containers=10,
            avg_confidence=0.87,
            category_counts={},
            processed_image_id=None,
        )

        # Verify asyncio.run called
        mock_asyncio_run.assert_called_once()

    @patch("app.tasks.ml_tasks.asyncio.run")
    @patch("app.tasks.ml_tasks.get_async_session")
    def test_mark_session_failed(self, mock_get_session, mock_asyncio_run):
        """Test _mark_session_failed helper."""
        from app.tasks.ml_tasks import _mark_session_failed

        _mark_session_failed(session_id=123, error_message="Pipeline failed")

        # Verify asyncio.run called
        mock_asyncio_run.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# Task Routing Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestTaskRouting:
    """Test task routing configuration."""

    def test_ml_parent_task_routes_to_cpu_queue(self):
        """Test ml_parent_task is routed to cpu_queue."""
        # Check task configuration
        assert ml_parent_task.queue == "cpu_queue"

    def test_ml_child_task_routes_to_gpu_queue(self):
        """Test ml_child_task is routed to gpu_queue."""
        # Check task configuration
        assert ml_child_task.queue == "gpu_queue"

    def test_ml_aggregation_callback_routes_to_cpu_queue(self):
        """Test ml_aggregation_callback is routed to cpu_queue."""
        # Check task configuration
        assert ml_aggregation_callback.queue == "cpu_queue"

    def test_ml_child_task_has_max_retries(self):
        """Test ml_child_task has max_retries configured."""
        assert ml_child_task.max_retries == 3

    def test_ml_parent_task_has_max_retries(self):
        """Test ml_parent_task has max_retries configured."""
        assert ml_parent_task.max_retries == 2
