"""Unit tests for ModelSingletonTask base class.

This module tests the Celery base task implementation for:
- Model property accessors (seg_model, det_model)
- Worker ID extraction from hostname
- GPU memory cleanup after N tasks
- Model caching behavior in task context

Test Coverage Target: ≥85%
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

# =============================================================================
# Test Classes
# =============================================================================


class TestModelSingletonTaskModelProperties:
    """Test model property accessors (seg_model, det_model)."""

    def setup_method(self):
        """Clear ModelCache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()

    def test_seg_model_property_returns_cached_instance(self, mock_yolo):
        """Test seg_model property uses singleton cache.

        Accessing seg_model multiple times should return the same
        cached instance from ModelCache.
        """
        from app.celery.base_tasks import ModelSingletonTask

        # Arrange: Create task with mocked request
        task = ModelSingletonTask()
        with patch.object(task, "request", Mock(hostname="gpu0@worker")):
            # Act: Access seg_model twice
            model1 = task.seg_model
            model2 = task.seg_model

            # Assert: Same instance returned
            assert model1 is model2, "seg_model should return cached instance"

            # Assert: YOLO called only once
            assert mock_yolo.call_count == 1

    def test_det_model_property_returns_cached_instance(self, mock_yolo):
        """Test det_model property uses singleton cache.

        Accessing det_model multiple times should return the same
        cached instance from ModelCache.
        """
        from app.celery.base_tasks import ModelSingletonTask

        # Arrange: Create task with worker ID
        task = ModelSingletonTask()
        task.request = Mock(hostname="gpu0@worker")

        # Act: Access det_model twice
        model1 = task.det_model
        model2 = task.det_model

        # Assert: Same instance returned
        assert model1 is model2, "det_model should return cached instance"

        # Assert: YOLO called only once
        assert mock_yolo.call_count == 1

    def test_seg_and_det_models_are_different(self, mock_yolo):
        """Test seg_model and det_model return different instances.

        Segmentation and detection models should be separate instances.
        """
        from app.celery.base_tasks import ModelSingletonTask

        # Arrange: Create task
        task = ModelSingletonTask()
        task.request = Mock(hostname="gpu0@worker")

        # Act: Access both models
        seg_model = task.seg_model
        det_model = task.det_model

        # Assert: Different instances
        assert seg_model is not det_model

        # Assert: YOLO called twice (once per model type)
        assert mock_yolo.call_count == 2

    def test_models_use_correct_worker_id(self, mock_yolo):
        """Test models are loaded with correct worker_id from hostname.

        The worker_id extracted from hostname should be passed
        to ModelCache.get_model().
        """
        from app.celery.base_tasks import ModelSingletonTask
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: Create task with specific hostname
        task = ModelSingletonTask()
        task.request = Mock(hostname="gpu2@worker")

        # Act: Access model
        with patch.object(ModelCache, "get_model", wraps=ModelCache.get_model) as mock_get:
            model = task.seg_model

        # Assert: get_model called with worker_id=2
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "segment"  # model_type
        assert call_args[1]["worker_id"] == 2  # worker_id


class TestModelSingletonTaskWorkerID:
    """Test worker ID extraction from hostname."""

    def test_worker_id_extracted_from_gpu_hostname(self):
        """Test _get_worker_id() parses 'gpuN@worker' format.

        Standard GPU worker hostname format: gpu0@worker, gpu1@worker, etc.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()

        # Test gpu0
        task.request = Mock(hostname="gpu0@worker")
        assert task._get_worker_id() == 0

        # Test gpu1
        task.request = Mock(hostname="gpu1@worker")
        assert task._get_worker_id() == 1

        # Test gpu5
        task.request = Mock(hostname="gpu5@worker")
        assert task._get_worker_id() == 5

    def test_worker_id_defaults_to_zero_for_invalid_format(self):
        """Test _get_worker_id() defaults to 0 for non-standard hostname.

        If hostname doesn't match 'gpuN@' pattern, default to worker_id=0.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()

        # Test generic hostname
        task.request = Mock(hostname="worker@hostname")
        assert task._get_worker_id() == 0, "Should default to 0 for generic hostname"

        # Test cpu worker hostname
        task.request = Mock(hostname="cpu0@worker")
        assert task._get_worker_id() == 0, "Should default to 0 for CPU worker"

        # Test empty hostname
        task.request = Mock(hostname="")
        assert task._get_worker_id() == 0, "Should default to 0 for empty hostname"

    def test_worker_id_handles_no_request(self):
        """Test _get_worker_id() handles missing request attribute.

        If task.request is None (shouldn't happen in prod), default to 0.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()
        task.request = None

        # Should not raise exception
        assert task._get_worker_id() == 0, "Should default to 0 when request is None"

    def test_worker_id_handles_missing_hostname(self):
        """Test _get_worker_id() handles missing hostname attribute.

        If request.hostname is None, default to 0.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()
        task.request = Mock(hostname=None)

        # Should not raise exception
        assert task._get_worker_id() == 0, "Should default to 0 when hostname is None"


class TestModelSingletonTaskGPUCleanup:
    """Test GPU memory cleanup after N tasks (AC3 validation)."""

    def setup_method(self):
        """Reset task counter before each test."""
        from app.celery.base_tasks import ModelSingletonTask

        # Reset class-level counter
        if hasattr(ModelSingletonTask, "_task_counter"):
            ModelSingletonTask._task_counter = 0

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    def test_gpu_cleanup_every_100_tasks(self, mock_empty_cache, mock_cuda):
        """Test GPU memory cleanup after 100 task completions (AC3).

        After every 100 tasks, torch.cuda.empty_cache() should be called
        to prevent memory fragmentation.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()

        # Act: Simulate 100 task completions
        for i in range(100):
            task.after_return(
                status="SUCCESS", retval=None, task_id=f"task-{i}", args=(), kwargs={}, einfo=None
            )

        # Assert: empty_cache called once after 100 tasks
        assert mock_empty_cache.call_count == 1, "Should call empty_cache once after 100 tasks"

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    def test_gpu_cleanup_every_100_tasks_multiple_cycles(self, mock_empty_cache, mock_cuda):
        """Test GPU cleanup occurs multiple times over 300 tasks.

        Should call empty_cache at tasks 100, 200, 300.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()

        # Act: Simulate 300 task completions
        for i in range(300):
            task.after_return(
                status="SUCCESS", retval=None, task_id=f"task-{i}", args=(), kwargs={}, einfo=None
            )

        # Assert: empty_cache called 3 times (at 100, 200, 300)
        assert mock_empty_cache.call_count == 3, "Should call empty_cache 3 times for 300 tasks"

    @patch("torch.cuda.is_available", return_value=False)
    @patch("torch.cuda.empty_cache")
    def test_gpu_cleanup_skipped_on_cpu(self, mock_empty_cache, mock_cuda):
        """Test GPU cleanup skipped when running on CPU.

        torch.cuda.empty_cache() should not be called if GPU not available.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()

        # Act: Simulate 100 task completions on CPU
        for i in range(100):
            task.after_return(
                status="SUCCESS", retval=None, task_id=f"task-{i}", args=(), kwargs={}, einfo=None
            )

        # Assert: empty_cache not called on CPU
        mock_empty_cache.assert_not_called(), "Should not call empty_cache on CPU"

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    def test_gpu_cleanup_logged(self, mock_empty_cache, mock_cuda, caplog):
        """Test GPU cleanup is logged for monitoring.

        When cleanup occurs, should log for observability.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()

        # Act: Simulate 100 task completions
        with caplog.at_level("INFO"):
            for i in range(100):
                task.after_return(
                    status="SUCCESS",
                    retval=None,
                    task_id=f"task-{i}",
                    args=(),
                    kwargs={},
                    einfo=None,
                )

        # Assert: Cleanup logged
        assert any(
            "GPU memory cleanup" in record.message for record in caplog.records
        ), "Should log GPU cleanup event"

    def test_after_return_handles_task_failure(self):
        """Test after_return() handles failed tasks gracefully.

        Counter should still increment even if task failed.
        """
        from app.celery.base_tasks import ModelSingletonTask

        task = ModelSingletonTask()

        # Act: Simulate failed task
        try:
            task.after_return(
                status="FAILURE",
                retval=None,
                task_id="task-fail",
                args=(),
                kwargs={},
                einfo=Mock(),  # Exception info
            )
        except Exception as e:
            pytest.fail(f"after_return should not raise exception: {e}")

        # Assert: No exception raised


class TestModelSingletonTaskIntegrationWithCache:
    """Test integration between ModelSingletonTask and ModelCache."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()

    def test_multiple_tasks_share_same_model_instance(self, mock_yolo):
        """Test multiple task instances share cached models.

        Different task instances for the same worker should share
        the same model instance via ModelCache.
        """
        from app.celery.base_tasks import ModelSingletonTask

        # Arrange: Create two task instances for same worker
        task1 = ModelSingletonTask()
        task1.request = Mock(hostname="gpu0@worker")

        task2 = ModelSingletonTask()
        task2.request = Mock(hostname="gpu0@worker")

        # Act: Access models from both tasks
        model1 = task1.seg_model
        model2 = task2.seg_model

        # Assert: Same instance shared
        assert model1 is model2, "Different tasks should share same model instance"

        # Assert: YOLO called only once
        assert mock_yolo.call_count == 1

    def test_tasks_on_different_workers_use_different_models(self, mock_yolo):
        """Test tasks on different GPU workers use different model instances.

        Tasks with different worker IDs should get separate models
        to avoid GPU contention.
        """
        from app.celery.base_tasks import ModelSingletonTask

        # Arrange: Create tasks for different workers
        task_gpu0 = ModelSingletonTask()
        task_gpu0.request = Mock(hostname="gpu0@worker")

        task_gpu1 = ModelSingletonTask()
        task_gpu1.request = Mock(hostname="gpu1@worker")

        # Act: Access models
        model_gpu0 = task_gpu0.seg_model
        model_gpu1 = task_gpu1.seg_model

        # Assert: Different instances
        assert model_gpu0 is not model_gpu1

        # Assert: YOLO called twice
        assert mock_yolo.call_count == 2


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def mock_yolo():
    """Mock YOLO model for testing.

    Returns a MagicMock that simulates YOLO model behavior.
    Each call to YOLO() returns a NEW instance.
    """
    with patch("app.services.ml_processing.model_cache.YOLO") as mock:

        def create_model_instance(*args, **kwargs):
            """Factory function that creates a new model instance per call."""
            model_instance = MagicMock()
            # Mock to() to return self (chainable)
            model_instance.to.return_value = model_instance
            # Mock fuse() with no return value
            model_instance.fuse.return_value = None
            return model_instance

        # YOLO() calls factory (returns NEW instance each time)
        mock.side_effect = create_model_instance

        yield mock


@pytest.fixture
def mock_cuda_available():
    """Mock CUDA as available."""
    with patch("torch.cuda.is_available", return_value=True):
        yield


@pytest.fixture
def mock_cuda_unavailable():
    """Mock CUDA as unavailable."""
    with patch("torch.cuda.is_available", return_value=False):
        yield
