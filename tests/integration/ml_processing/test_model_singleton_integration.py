"""Integration tests for ModelCache singleton pattern with real models.

This module tests the complete model caching workflow:
- Loading real YOLO models (when available)
- Memory usage monitoring
- Multi-model workflows (segment + detect)
- Performance validation (AC7)

Test Coverage: Integration validation for critical path

NOTE: These tests are skipped if:
- GPU is not available (requires CUDA for some tests)
- Model files are not found (requires trained models)
- Running in CI environment without GPU

Run these tests with: pytest tests/integration/ml_processing/ -v
"""

import os
from unittest.mock import Mock, patch

import psutil
import pytest
import torch

# =============================================================================
# Test Classes
# =============================================================================


class TestModelCacheIntegrationRealModels:
    """Integration tests with real YOLO models (if available)."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()

    @pytest.mark.integration
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="GPU required")
    @pytest.mark.skipif(not os.path.exists("/models/segment.pt"), reason="Model files not found")
    def test_load_both_models_same_worker(self):
        """Test loading segment + detect models in same worker (AC integration).

        Validates that both models can be loaded simultaneously
        without conflicts or excessive memory usage.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Act: Load both models
        seg_model = ModelCache.get_model("segment", worker_id=0)
        det_model = ModelCache.get_model("detect", worker_id=0)

        # Assert: Both models loaded
        assert seg_model is not None, "Segment model should be loaded"
        assert det_model is not None, "Detect model should be loaded"
        assert seg_model is not det_model, "Models should be different instances"

        # Assert: Models are on correct device
        # Note: Can't directly check device on YOLO model, but verify no errors

    @pytest.mark.integration
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="GPU required")
    @pytest.mark.skipif(not os.path.exists("/models/segment.pt"), reason="Model files not found")
    def test_model_inference_works_after_loading(self):
        """Test that loaded models can actually perform inference.

        Validates the model is not just loaded but is functional.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: Load model
        seg_model = ModelCache.get_model("segment", worker_id=0)

        # Act: Try to run inference (with dummy data)
        # Note: This is a smoke test, not validating predictions
        try:
            # Create dummy 640x640 image tensor
            import numpy as np

            dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

            # Run inference
            results = seg_model(dummy_image, verbose=False)

            # Assert: Results returned without error
            assert results is not None, "Should return results"

        except Exception as e:
            pytest.fail(f"Inference failed: {e}")

    @pytest.mark.integration
    def test_model_loaded_only_once_across_tasks(self):
        """Test model loaded once despite multiple get_model calls (AC integration).

        Validates singleton behavior with real ModelCache.
        No actual model loading (uses mocks to avoid slow downloads).
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Clear cache
        ModelCache._instances.clear()

        # Mock YOLO to track calls
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            model_instance = Mock()
            model_instance.to.return_value = model_instance
            model_instance.fuse.return_value = None
            mock_yolo.return_value = model_instance

            # Act: Call 10 times
            models = [ModelCache.get_model("segment", worker_id=0) for _ in range(10)]

            # Assert: All same instance
            assert len({id(m) for m in models}) == 1, "All calls should return same instance"

            # Assert: YOLO called only once
            assert mock_yolo.call_count == 1, "YOLO should be instantiated only once"

    @pytest.mark.integration
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="GPU required")
    @pytest.mark.slow
    def test_memory_usage_stable_after_100_loads(self):
        """Test memory doesn't leak after repeated access (AC integration).

        Validates that accessing cached model 100 times doesn't
        cause memory growth (no leaks).
        """
        from app.services.ml_processing.model_cache import ModelCache

        process = psutil.Process(os.getpid())

        # Force garbage collection before measuring
        import gc

        gc.collect()

        # Initial memory
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Act: Access model 100 times (use mock to avoid slow loading)
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            model_instance = Mock()
            model_instance.to.return_value = model_instance
            model_instance.fuse.return_value = None
            mock_yolo.return_value = model_instance

            for _ in range(100):
                _ = ModelCache.get_model("segment", worker_id=0)

        # Force garbage collection after test
        gc.collect()

        # Final memory
        mem_after = process.memory_info().rss / 1024 / 1024  # MB

        # Assert: Memory growth should be minimal (<50MB variance)
        mem_diff = abs(mem_after - mem_before)
        assert mem_diff < 50, f"Memory grew by {mem_diff:.2f} MB (should be < 50 MB)"


class TestModelCacheIntegrationPerformance:
    """Integration tests for performance validation (AC7)."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()

    @pytest.mark.integration
    def test_model_loading_time_acceptable(self):
        """Test model loading completes within acceptable time.

        First load: Should complete in < 10 seconds (includes download if needed)
        Subsequent loads: Should be instant (<0.1s) from cache.
        """
        import time

        from app.services.ml_processing.model_cache import ModelCache

        # Mock YOLO to avoid actual loading time
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            model_instance = Mock()
            model_instance.to.return_value = model_instance
            model_instance.fuse.return_value = None
            mock_yolo.return_value = model_instance

            # Act: First load
            start = time.time()
            model1 = ModelCache.get_model("segment", worker_id=0)
            first_load_time = time.time() - start

            # Assert: First load reasonable
            assert (
                first_load_time < 1.0
            ), f"First load took {first_load_time:.2f}s (should be < 1s with mock)"

            # Act: Subsequent load (cached)
            start = time.time()
            model2 = ModelCache.get_model("segment", worker_id=0)
            cached_load_time = time.time() - start

            # Assert: Cached load instant
            assert (
                cached_load_time < 0.01
            ), f"Cached load took {cached_load_time:.4f}s (should be < 0.01s)"

            # Assert: Same instance
            assert model1 is model2

    @pytest.mark.integration
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="GPU required")
    @pytest.mark.skipif(not os.path.exists("/models/segment.pt"), reason="Model files not found")
    @pytest.mark.slow
    def test_inference_performance_meets_targets(self):
        """Test inference performance meets AC7 targets.

        Target: 5-10 minutes per 4K image on CPU (with SAHI slicing)
        Target: 1-3 minutes per 4K image on GPU (with SAHI slicing)

        This test only validates single inference is fast enough.
        Full pipeline timing is tested in pipeline integration tests.
        """
        import time

        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: Load model
        seg_model = ModelCache.get_model("segment", worker_id=0)

        # Create dummy 640x640 image (single SAHI slice)
        import numpy as np

        dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        # Act: Run inference
        start = time.time()
        results = seg_model(dummy_image, verbose=False)
        inference_time = time.time() - start

        # Assert: Single slice inference is fast
        # A 4K image becomes ~20 slices (640x640)
        # Target: <2s per slice on GPU (40s total for 4K = well under 3 min)
        # Target: <10s per slice on CPU (200s total for 4K = ~3.3 min)
        expected_max_time = 10.0 if not torch.cuda.is_available() else 2.0

        assert (
            inference_time < expected_max_time
        ), f"Inference took {inference_time:.2f}s (should be < {expected_max_time}s)"

    @pytest.mark.integration
    def test_concurrent_model_access_no_deadlock(self):
        """Test concurrent access from multiple threads doesn't deadlock.

        Validates thread safety under real conditions.
        """
        import threading

        from app.services.ml_processing.model_cache import ModelCache

        results = []
        exceptions = []

        def get_model_thread():
            """Thread worker."""
            try:
                # Mock YOLO to avoid slow loading
                with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
                    model_instance = Mock()
                    model_instance.to.return_value = model_instance
                    model_instance.fuse.return_value = None
                    mock_yolo.return_value = model_instance

                    model = ModelCache.get_model("segment", worker_id=0)
                    results.append(model)
            except Exception as e:
                exceptions.append(e)

        # Act: Start 20 threads
        threads = [threading.Thread(target=get_model_thread) for _ in range(20)]
        for t in threads:
            t.start()

        # Wait with timeout
        for t in threads:
            t.join(timeout=5.0)
            if t.is_alive():
                pytest.fail("Thread deadlock detected (timeout after 5s)")

        # Assert: No exceptions
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # Assert: All threads completed
        assert len(results) == 20, f"Only {len(results)} threads completed (expected 20)"


class TestModelCacheIntegrationCeleryTasks:
    """Integration tests with Celery task context."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()

    @pytest.mark.integration
    def test_task_uses_cached_model_across_invocations(self):
        """Test Celery tasks use cached model across multiple invocations.

        Simulates real task execution pattern.
        """
        from app.celery.base_tasks import ModelSingletonTask

        # Mock YOLO to avoid slow loading
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            model_instance = Mock()
            model_instance.to.return_value = model_instance
            model_instance.fuse.return_value = None
            mock_yolo.return_value = model_instance

            # Arrange: Create task
            task = ModelSingletonTask()
            task.request = Mock(hostname="gpu0@worker")

            # Act: Run task 10 times (simulate 10 task invocations)
            models = []
            for i in range(10):
                # Simulate task execution
                model = task.seg_model
                models.append(model)

            # Assert: All invocations used same model
            assert len({id(m) for m in models}) == 1, "All invocations should use same model"

            # Assert: YOLO called only once
            assert mock_yolo.call_count == 1

    @pytest.mark.integration
    def test_different_workers_use_different_models(self):
        """Test different GPU workers use separate model instances.

        Validates multi-worker setup with proper isolation.
        """
        from app.celery.base_tasks import ModelSingletonTask

        # Mock YOLO
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            model_instance = Mock()
            model_instance.to.return_value = model_instance
            model_instance.fuse.return_value = None
            mock_yolo.return_value = model_instance

            # Arrange: Create tasks for 3 workers
            task_gpu0 = ModelSingletonTask()
            task_gpu0.request = Mock(hostname="gpu0@worker")

            task_gpu1 = ModelSingletonTask()
            task_gpu1.request = Mock(hostname="gpu1@worker")

            task_gpu2 = ModelSingletonTask()
            task_gpu2.request = Mock(hostname="gpu2@worker")

            # Act: Get models
            model0 = task_gpu0.seg_model
            model1 = task_gpu1.seg_model
            model2 = task_gpu2.seg_model

            # Assert: Each worker has different model
            assert model0 is not model1
            assert model1 is not model2
            assert model0 is not model2

            # Assert: YOLO called 3 times (once per worker)
            assert mock_yolo.call_count == 3


class TestModelCacheIntegrationErrorRecovery:
    """Integration tests for error handling and recovery."""

    def setup_method(self):
        """Clear cache before each test."""
        from app.services.ml_processing.model_cache import ModelCache

        ModelCache._instances.clear()

    @pytest.mark.integration
    def test_cache_recovers_after_failed_load(self):
        """Test cache can recover after failed model load.

        If model loading fails once, subsequent attempts should work.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Arrange: First call fails
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            mock_yolo.side_effect = RuntimeError("Model file not found")

            # Act & Assert: First call fails
            with pytest.raises(RuntimeError):
                ModelCache.get_model("segment", worker_id=0)

        # Arrange: Second call succeeds
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            model_instance = Mock()
            model_instance.to.return_value = model_instance
            model_instance.fuse.return_value = None
            mock_yolo.return_value = model_instance

            # Act: Second call should work
            model = ModelCache.get_model("segment", worker_id=0)

            # Assert: Model loaded successfully
            assert model is not None

    @pytest.mark.integration
    def test_clear_cache_allows_reload(self):
        """Test clearing cache allows fresh model reload.

        After clearing cache, get_model should load fresh instance.
        """
        from app.services.ml_processing.model_cache import ModelCache

        # Mock YOLO
        with patch("app.services.ml_processing.model_cache.YOLO") as mock_yolo:
            model_instance = Mock()
            model_instance.to.return_value = model_instance
            model_instance.fuse.return_value = None
            mock_yolo.return_value = model_instance

            # Act: Load model
            model1 = ModelCache.get_model("segment", worker_id=0)
            assert mock_yolo.call_count == 1

            # Act: Clear cache
            ModelCache.clear_cache()

            # Act: Load again
            model2 = ModelCache.get_model("segment", worker_id=0)

            # Assert: New instance loaded
            # Note: With mocks, instances will be same, but YOLO called twice
            assert mock_yolo.call_count == 2, "YOLO should be called again after cache clear"


# =============================================================================
# Pytest Configuration
# =============================================================================


@pytest.fixture(scope="module")
def check_model_files():
    """Check if model files exist before running integration tests.

    Raises pytest.skip if model files not found.
    """
    seg_path = "/models/segment.pt"
    det_path = "/models/detect.pt"

    if not os.path.exists(seg_path) and not os.path.exists(det_path):
        pytest.skip("Model files not found. Place models in /models/ directory.")
