"""Base Celery task classes with model singleton support.

This is a STUB implementation for Testing Expert to write tests against.
The Python Expert will implement the actual logic in parallel.

Provides:
- ModelSingletonTask: Base task with cached model access
- GPU memory cleanup after N tasks
- Worker ID extraction from hostname
"""

import logging
import re
from typing import Any

try:
    import torch  # type: ignore[import-not-found]
    from celery import Task  # type: ignore[import-not-found]
except ImportError:
    # Allow tests to run without celery/torch
    class Task:  # type: ignore[no-redef]
        """Stub Task class for testing."""

        def __init__(self) -> None:
            self.request = None

    torch = None

from app.services.ml_processing.model_cache import ModelCache

logger = logging.getLogger(__name__)


class ModelSingletonTask(Task):  # type: ignore[misc]
    """Base Celery task with singleton model caching.

    This is a STUB - Python Expert will implement.

    Features:
    - Lazy-loaded model properties (seg_model, det_model)
    - Worker ID extraction from hostname
    - GPU memory cleanup every 100 tasks
    """

    _task_counter: int = 0
    _cleanup_interval: int = 100

    @property
    def seg_model(self) -> Any:
        """Get cached segmentation model for this worker.

        Returns:
            YOLO segmentation model instance
        """
        worker_id = self._get_worker_id()
        return ModelCache.get_model("segment", worker_id=worker_id)

    @property
    def det_model(self) -> Any:
        """Get cached detection model for this worker.

        Returns:
            YOLO detection model instance
        """
        worker_id = self._get_worker_id()
        return ModelCache.get_model("detect", worker_id=worker_id)

    def _get_worker_id(self) -> int:
        """Extract worker ID from Celery hostname.

        Hostname format: "gpu0@worker", "gpu1@worker", etc.
        Falls back to 0 if format doesn't match.

        Returns:
            Worker ID (GPU index)
        """
        if not self.request or not self.request.hostname:
            return 0

        hostname = self.request.hostname

        # Parse "gpuN@" pattern
        match = re.match(r"gpu(\d+)@", hostname)
        if match:
            return int(match.group(1))

        # Default to 0 for non-GPU workers
        return 0

    def after_return(
        self,
        status: str,
        retval: Any,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any | None,
    ) -> None:
        """Hook called after task completes.

        Performs GPU memory cleanup every N tasks to prevent fragmentation.

        Args:
            status: Task status ("SUCCESS", "FAILURE", etc.)
            retval: Task return value
            task_id: Task ID
            args: Task args
            kwargs: Task kwargs
            einfo: Exception info (if failed)
        """
        # Increment counter
        ModelSingletonTask._task_counter += 1

        # Cleanup every N tasks
        if (
            ModelSingletonTask._task_counter % self._cleanup_interval == 0
            and torch
            and torch.cuda.is_available()
        ):
            torch.cuda.empty_cache()
            logger.info(
                f"GPU memory cleanup performed after {ModelSingletonTask._task_counter} tasks"
            )
