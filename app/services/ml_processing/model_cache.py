"""ModelCache singleton for YOLO model management.

Provides:
- Singleton pattern for model caching
- Thread-safe model loading
- GPU/CPU device assignment
- Memory cleanup utilities
"""

import logging
import threading
from typing import Literal

try:
    import torch  # type: ignore[import-not-found]
    from ultralytics import YOLO  # type: ignore[import-not-found]
except ImportError:
    # Allow tests to run without torch/ultralytics
    YOLO = None
    torch = None

logger = logging.getLogger(__name__)

ModelType = Literal["segment", "detect"]


class ModelCache:
    """Singleton cache for YOLO models (per worker, per model type)."""

    _instances: dict[str, "YOLO"] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_model(cls, model_type: ModelType, worker_id: int = 0) -> "YOLO":
        """Get or create cached model instance.

        Args:
            model_type: "segment" or "detect"
            worker_id: GPU worker ID (0, 1, 2, etc.)

        Returns:
            Cached YOLO model instance

        Raises:
            ValueError: If model_type invalid or worker_id negative
            RuntimeError: If model loading fails
        """
        # Validation
        if model_type not in ["segment", "detect"]:
            raise ValueError(f"Invalid model_type: {model_type}. Must be 'segment' or 'detect'")

        if worker_id < 0:
            raise ValueError("worker_id must be non-negative")

        # Cache key
        cache_key = f"{model_type}_worker_{worker_id}"

        # Thread-safe singleton check
        with cls._lock:
            if cache_key not in cls._instances:
                logger.info(f"Loading {model_type} model for worker {worker_id}")

                # Get model path
                seg_path, det_path = cls._get_model_paths()
                model_path = seg_path if model_type == "segment" else det_path

                # Load model
                model = YOLO(model_path)

                # Assign device
                if torch and torch.cuda.is_available():
                    gpu_count = torch.cuda.device_count()
                    gpu_id = worker_id % gpu_count
                    device = f"cuda:{gpu_id}"
                    logger.info(f"Assigning model to {device}")
                else:
                    device = "cpu"
                    logger.warning(f"GPU not available, using CPU for worker {worker_id}")

                model = model.to(device)

                # Optimize model
                model.fuse()

                # Cache
                cls._instances[cache_key] = model

            return cls._instances[cache_key]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached models and free GPU memory."""
        with cls._lock:
            cls._instances.clear()

            if torch and torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("GPU memory cache cleared")

    @staticmethod
    def _get_model_paths() -> tuple[str, str]:
        """Get paths to segment and detect models.

        Returns:
            (segment_path, detect_path)

        Note:
            Paths should be configured via environment variables in production.
            Default paths assume models are mounted at /models/ in Docker.
        """
        return ("/checkpoints/segment.pt", "/checkpoints/detect.pt")
