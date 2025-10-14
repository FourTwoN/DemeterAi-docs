"""Unit tests for ModelCache singleton pattern.

This module tests the ModelCache implementation for:
- Singleton pattern behavior (AC6.1, AC6.2)
- GPU/CPU device assignment (AC6.3)
- Thread safety with concurrent access (AC6.4)
- GPU memory cleanup (AC6.5)
- Model optimization (fuse)
- Cache clearing and instance management

Test Coverage Target: ≥85%
"""

import threading
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Test Classes
# =============================================================================


class TestModelCacheSingleton:
    """Test singleton pattern behavior (AC6.1, AC6.2)."""

    def setup_method(self):
        """Clear cache before each test."""
        # Import here to avoid circular imports
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()
        ModelCache._lock = threading.Lock()

    def test_same_instance_returned_for_same_params(self, mock_yolo):
        """Test singleton returns same instance on repeated calls (AC6.1).

        Validates that calling get_model() with identical parameters
        returns the exact same model instance, not a new copy.
        YOLO should only be instantiated once.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act: Get model twice with same params
        model1 = ModelCache.get_model("segment", worker_id=0)
        model2 = ModelCache.get_model("segment", worker_id=0)

        # Assert: Same instance returned
        assert model1 is model2, "Singleton should return same instance"

        # Assert: YOLO called only once
        assert mock_yolo.call_count == 1, "YOLO should be instantiated only once"

    def test_separate_instances_for_different_workers(self, mock_yolo):
        """Test separate instances for different GPU IDs (AC6.2).

        Each GPU worker should get its own model instance
        to avoid contention and GPU memory conflicts.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act: Get models for different workers
        model_gpu0 = ModelCache.get_model("segment", worker_id=0)
        model_gpu1 = ModelCache.get_model("segment", worker_id=1)

        # Assert: Different instances
        assert model_gpu0 is not model_gpu1, "Different workers should get different instances"

        # Assert: YOLO called twice (once per worker)
        assert mock_yolo.call_count == 2, "YOLO should be instantiated for each worker"

    def test_separate_instances_for_different_model_types(self, mock_yolo):
        """Test separate instances for segment vs detect (AC6.2).

        Segmentation and detection models should be cached separately
        even for the same worker.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act: Get different model types
        seg_model = ModelCache.get_model("segment", worker_id=0)
        det_model = ModelCache.get_model("detect", worker_id=0)

        # Assert: Different instances
        assert seg_model is not det_model, "Different model types should be separate instances"

        # Assert: YOLO called twice (once per model type)
        assert mock_yolo.call_count == 2, "YOLO should be instantiated for each model type"

    def test_cache_key_format(self, mock_yolo):
        """Test cache key generation format.

        Cache keys should follow format: <model_type>_worker_<worker_id>
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act: Get models
        ModelCache.get_model("segment", worker_id=0)
        ModelCache.get_model("detect", worker_id=1)

        # Assert: Cache keys exist
        assert "segment_worker_0" in ModelCache._instances
        assert "detect_worker_1" in ModelCache._instances
        assert len(ModelCache._instances) == 2


class TestModelCacheDeviceAssignment:
    """Test GPU/CPU device assignment (AC6.3)."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()
        ModelCache._lock = threading.Lock()

    def test_gpu_assignment_when_available(self, mock_yolo):
        """Test model assigned to correct GPU when available (AC6.3).

        When CUDA is available, model should be assigned to the
        GPU corresponding to the worker_id.
        """
        from app.services.ml_processing.model_cache import ModelCache

        with (
            patch("torch.cuda.is_available", return_value=True),
            patch("torch.cuda.device_count", return_value=2),
        ):
            # Act: Get model for worker 0
            model = ModelCache.get_model("segment", worker_id=0)

            # Assert: Model moved to cuda:0
            assert model.to.called, "to() should be called"
            model.to.assert_called_with("cuda:0")

        # Clear cache for second test
        ModelCache._instances.clear()

        with (
            patch("torch.cuda.is_available", return_value=True),
            patch("torch.cuda.device_count", return_value=2),
        ):
            # Act: Get model for worker 1
            model = ModelCache.get_model("segment", worker_id=1)

            # Assert: Model moved to cuda:1
            model.to.assert_called_with("cuda:1")

    def test_cpu_fallback_when_gpu_unavailable(self, mock_yolo, caplog):
        """Test CPU fallback when GPU unavailable (AC6.3).

        When CUDA is not available, model should fallback to CPU
        and log a warning.
        """
        from app.services.ml_processing.model_cache import ModelCache

        with patch("torch.cuda.is_available", return_value=False):
            # Act: Get model when GPU unavailable
            with caplog.at_level("WARNING"):
                model = ModelCache.get_model("segment", worker_id=0)

            # Assert: Model moved to CPU
            model.to.assert_called_with("cpu")

            # Assert: Warning logged
            assert any(
                "GPU not available" in record.message for record in caplog.records
            ), "Should log warning about GPU unavailability"

    def test_gpu_fallback_when_worker_id_exceeds_gpu_count(self, mock_yolo):
        """Test GPU fallback when worker_id exceeds available GPUs.

        If worker_id=2 but only 1 GPU available, should use modulo
        to wrap around (worker 2 -> GPU 0).
        """
        from app.services.ml_processing.model_cache import ModelCache

        with (
            patch("torch.cuda.is_available", return_value=True),
            patch("torch.cuda.device_count", return_value=1),
        ):
            # Act: Request worker 2 when only 1 GPU available
            model = ModelCache.get_model("segment", worker_id=2)

            # Assert: Should use GPU 0 (2 % 1 = 0)
            model.to.assert_called_with("cuda:0")

    def test_model_fuse_called_for_optimization(self, mock_yolo):
        """Test model.fuse() called for 10-15% speedup.

        YOLO's fuse() operation merges Conv+BN layers for faster inference.
        This should be called during model loading.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act: Get model
        model = ModelCache.get_model("segment", worker_id=0)

        # Assert: fuse() was called
        model.fuse.assert_called_once(), "Model should be fused for optimization"

    def test_device_assignment_logged(self, mock_yolo, caplog):
        """Test device assignment is logged for debugging."""
        from app.services.ml_processing.model_cache import ModelCache

        with patch("torch.cuda.is_available", return_value=True):
            # Act: Get model
            with caplog.at_level("INFO"):
                model = ModelCache.get_model("segment", worker_id=0)

            # Assert: Device logged (look for "Assigning" message)
            assert any(
                "assign" in record.message.lower() for record in caplog.records
            ), "Should log device assignment"


class TestModelCacheThreadSafety:
    """Test thread safety with concurrent access (AC6.4)."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()
        ModelCache._lock = threading.Lock()

    def test_concurrent_access_from_multiple_threads(self, mock_yolo):
        """Test thread safety with concurrent access from 10 threads (AC6.4).

        Multiple threads requesting the same model simultaneously
        should all get the same instance, and YOLO should only be
        instantiated once.
        """
        from app.services.ml_processing.model_cache import ModelCache

        results: list = []

        def get_model() -> None:
            """Thread worker function."""
            model = ModelCache.get_model("segment", worker_id=0)
            results.append(model)

        # Act: Start 10 threads
        threads = [Thread(target=get_model) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert: All threads got same instance
        assert len(results) == 10, "All threads should have completed"
        assert len({id(m) for m in results}) == 1, "All threads should get the exact same instance"

        # Assert: YOLO called only once despite 10 threads
        assert mock_yolo.call_count == 1, "YOLO should be instantiated only once"

    def test_concurrent_access_different_models(self, mock_yolo):
        """Test concurrent access for different model types.

        Threads requesting different models (segment vs detect)
        should get different instances without race conditions.
        """
        from app.services.ml_processing.model_cache import ModelCache

        seg_results: list = []
        det_results: list = []

        def get_seg_model() -> None:
            model = ModelCache.get_model("segment", worker_id=0)
            seg_results.append(model)

        def get_det_model() -> None:
            model = ModelCache.get_model("detect", worker_id=0)
            det_results.append(model)

        # Act: Start 10 threads for each model type
        threads = []
        for _ in range(10):
            threads.append(Thread(target=get_seg_model))
            threads.append(Thread(target=get_det_model))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert: Each model type has consistent instances
        assert len(seg_results) == 10
        assert len(det_results) == 10
        assert len({id(m) for m in seg_results}) == 1, "All seg threads get same instance"
        assert len({id(m) for m in det_results}) == 1, "All det threads get same instance"

        # Assert: Segment and detect models are different
        assert seg_results[0] is not det_results[0]

        # Assert: YOLO called twice (once per model type)
        assert mock_yolo.call_count == 2

    def test_lock_released_after_exception(self, mock_yolo_error):
        """Test lock is released even if model loading fails.

        If YOLO instantiation raises an exception, the lock should
        be released to avoid deadlock.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act & Assert: Exception should propagate
        with pytest.raises(RuntimeError, match="Model loading failed"):
            ModelCache.get_model("segment", worker_id=0)

        # Assert: Lock should be released (can be acquired again)
        assert ModelCache._lock.acquire(blocking=False), "Lock should be released after exception"
        ModelCache._lock.release()


class TestModelCacheMemoryManagement:
    """Test GPU memory cleanup (AC6.5)."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()
        ModelCache._lock = threading.Lock()

    def test_clear_cache_empties_instances(self, mock_yolo):
        """Test clear_cache() removes all cached models (AC6.5).

        After clearing, _instances dict should be empty.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: Load multiple models
        ModelCache.get_model("segment", worker_id=0)
        ModelCache.get_model("detect", worker_id=0)
        ModelCache.get_model("segment", worker_id=1)

        assert len(ModelCache._instances) == 3, "Should have 3 cached models"

        # Act: Clear cache
        ModelCache.clear_cache()

        # Assert: All instances removed
        assert len(ModelCache._instances) == 0, "Cache should be empty after clear"

    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.empty_cache")
    def test_clear_cache_empties_gpu_memory(self, mock_empty_cache, mock_cuda, mock_yolo):
        """Test clear_cache() calls torch.cuda.empty_cache() (AC6.5).

        When clearing cache, GPU memory should be released.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: Load model on GPU
        ModelCache.get_model("segment", worker_id=0)

        # Act: Clear cache
        ModelCache.clear_cache()

        # Assert: GPU memory freed
        mock_empty_cache.assert_called_once(), "Should call torch.cuda.empty_cache()"

    @patch("torch.cuda.is_available", return_value=False)
    @patch("torch.cuda.empty_cache")
    def test_clear_cache_skips_gpu_cleanup_on_cpu(self, mock_empty_cache, mock_cuda, mock_yolo):
        """Test clear_cache() skips GPU cleanup when using CPU.

        torch.cuda.empty_cache() should not be called if GPU not available.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: Load model on CPU
        ModelCache.get_model("segment", worker_id=0)

        # Act: Clear cache
        ModelCache.clear_cache()

        # Assert: GPU cleanup not called
        mock_empty_cache.assert_not_called(), "Should not call empty_cache() on CPU"

    def test_clear_cache_thread_safe(self, mock_yolo):
        """Test clear_cache() is thread-safe.

        Multiple threads calling clear_cache() simultaneously
        should not cause race conditions.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: Load models
        ModelCache.get_model("segment", worker_id=0)

        # Act: Clear cache from multiple threads
        threads = [Thread(target=ModelCache.clear_cache) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert: Cache is empty (no exceptions raised)
        assert len(ModelCache._instances) == 0


class TestModelCacheErrorHandling:
    """Test error handling and edge cases."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()
        ModelCache._lock = threading.Lock()

    def test_invalid_model_type_raises_error(self):
        """Test invalid model_type raises ValueError.

        Only 'segment' and 'detect' should be valid model types.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act & Assert: Invalid model type
        with pytest.raises(ValueError, match="Invalid model_type"):
            ModelCache.get_model("invalid_type", worker_id=0)

    def test_negative_worker_id_raises_error(self):
        """Test negative worker_id raises ValueError.

        Worker IDs must be non-negative integers.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act & Assert: Negative worker ID
        with pytest.raises(ValueError, match="worker_id must be non-negative"):
            ModelCache.get_model("segment", worker_id=-1)

    @patch("app.services.ml_processing.model_cache.YOLO")
    def test_model_loading_exception_propagates(self, mock_yolo_class):
        """Test exceptions during model loading propagate correctly.

        If YOLO() raises an exception, it should propagate to the caller.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: YOLO raises exception
        mock_yolo_class.side_effect = RuntimeError("Model file not found")

        # Act & Assert: Exception propagates
        with pytest.raises(RuntimeError, match="Model file not found"):
            ModelCache.get_model("segment", worker_id=0)

    def test_get_model_paths_returns_valid_paths(self):
        """Test _get_model_paths() returns valid file paths.

        Model paths should be absolute paths to .pt files.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act: Get paths
        seg_path, det_path = ModelCache._get_model_paths()

        # Assert: Valid paths
        assert seg_path.endswith(".pt"), "Segment model should be .pt file"
        assert det_path.endswith(".pt"), "Detect model should be .pt file"
        assert "segment" in seg_path.lower(), "Segment path should contain 'segment'"
        assert "detect" in det_path.lower(), "Detect path should contain 'detect'"


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def mock_yolo():
    """Mock YOLO model for testing.

    Returns a MagicMock that simulates YOLO model behavior:
    - to() method for device assignment
    - fuse() method for optimization
    - Chainable method calls
    - Each call to YOLO() returns a NEW instance
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
def mock_yolo_error():
    """Mock YOLO that raises an exception during loading.

    Used to test error handling and lock release.
    """
    with patch("app.services.ml_processing.model_cache.YOLO") as mock:
        mock.side_effect = RuntimeError("Model loading failed")
        yield mock


@pytest.fixture
def mock_cuda_available():
    """Mock CUDA as available with 2 GPUs."""
    with (
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.device_count", return_value=2),
    ):
        yield


@pytest.fixture
def mock_cuda_unavailable():
    """Mock CUDA as unavailable (CPU-only mode)."""
    with patch("torch.cuda.is_available", return_value=False):
        yield
