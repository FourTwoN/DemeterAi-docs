"""YOLO v11 Segmentation Service.

This service provides container segmentation for greenhouse photos using
YOLO v11 segmentation model. It identifies three container types:
- plugs: Small trays with individual cells (charolas/bandejas)
- boxes: Medium containers (cajas)
- segments: Large container sections (remapped from "claro-cajon")

The service uses the Model Singleton pattern (ML001) for efficient model
caching and GPU memory management.

Performance:
    CPU: <1s for 4000x3000px images
    GPU: ~200-300ms for same images (3-5x speedup)

Architecture:
    ML Service Layer (Application Layer)
    └── Uses: ModelCache (Infrastructure Layer)
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    import numpy as np  # type: ignore[import-not-found]
except ImportError:
    np = None

from app.services.ml_processing.model_cache import ModelCache

if TYPE_CHECKING:
    from ultralytics.engine.results import Results  # type: ignore[import-not-found]
else:
    Results = Any

logger = logging.getLogger(__name__)


@dataclass
class SegmentResult:
    """Result from container segmentation.

    Represents a single detected container with its spatial properties.
    All coordinates are normalized to 0-1 range for resolution independence.

    Attributes:
        container_type: One of "plug", "box", "segment"
        confidence: Detection confidence score (0.0-1.0)
        bbox: Normalized bounding box (x1, y1, x2, y2) in 0-1 range
        polygon: List of normalized (x, y) polygon vertices in 0-1 range
        mask: Optional binary mask array (H, W) in original image resolution
        area_pixels: Approximate area in pixels (calculated from bbox)
    """

    container_type: str
    confidence: float
    bbox: tuple[float, float, float, float]
    polygon: list[tuple[float, float]]
    mask: "np.ndarray | None" = None
    area_pixels: int = 0

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate container type
        valid_types = {"plug", "box", "segment"}
        if self.container_type not in valid_types:
            raise ValueError(
                f"Invalid container_type: {self.container_type}. " f"Must be one of {valid_types}"
            )

        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")

        # Validate bbox
        if len(self.bbox) != 4:
            raise ValueError(f"bbox must have 4 elements, got {len(self.bbox)}")

        x1, y1, x2, y2 = self.bbox
        if not (0.0 <= x1 <= 1.0 and 0.0 <= y1 <= 1.0 and 0.0 <= x2 <= 1.0 and 0.0 <= y2 <= 1.0):
            raise ValueError(f"bbox coordinates must be in [0.0, 1.0]: {self.bbox}")

        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"Invalid bbox: x2 must be > x1 and y2 must be > y1. Got {self.bbox}")


class SegmentationService:
    """YOLO v11 container segmentation service.

    Identifies containers in greenhouse photos using instance segmentation.
    Provides polygon masks for precise container boundaries, which are used
    for downstream processing:
    - plugs → SAHI slicing for small plant detection
    - boxes → Direct YOLO detection
    - segments → Mixed strategy based on size

    The service uses lazy model loading via ModelCache singleton to:
    1. Share models across service instances (memory efficiency)
    2. Assign models to specific GPU workers (GPU scaling)
    3. Reuse warmed-up models (inference speed)

    Thread Safety:
        This service is thread-safe. Model loading is synchronized via
        ModelCache._lock. Multiple service instances can coexist.

    Example:
        >>> service = SegmentationService()
        >>> results = await service.segment_image(
        ...     "photo.jpg",
        ...     worker_id=0,
        ...     conf_threshold=0.30
        ... )
        >>> # Results: [SegmentResult(container_type="plug", confidence=0.92, ...),
        >>> #           SegmentResult(container_type="box", confidence=0.87, ...)]
    """

    # Container type remapping (YOLO class → standardized type)
    CONTAINER_TYPE_MAPPING = {
        "claro-cajon": "segment",  # Large containers
        "caja": "box",  # Medium containers
        "charola": "plug",  # Small trays
        "bandeja": "plug",  # Alternative name for trays
    }

    def __init__(self) -> None:
        """Initialize service with lazy model loading.

        The model is NOT loaded here. It's loaded on first segment_image()
        call via ModelCache singleton.
        """
        self._model: Any = None  # Lazy load via singleton (YOLO model)
        self._worker_id: int | None = None

    async def segment_image(
        self,
        image_path: str | Path,
        worker_id: int = 0,
        conf_threshold: float = 0.30,
        imgsz: int = 1024,
        iou_threshold: float = 0.50,
    ) -> list[SegmentResult]:
        """Segment containers in greenhouse photo.

        Runs YOLO v11 segmentation model on image and returns detected
        containers with polygon masks and bounding boxes.

        Args:
            image_path: Path to greenhouse photo (JPG, PNG, etc.)
            worker_id: GPU worker ID (0, 1, 2...). Used for multi-GPU scaling.
            conf_threshold: Minimum confidence score (0.0-1.0). Default 0.30.
            imgsz: Inference image size in pixels. Default 1024 for small objects.
                   Must be multiple of 32 (YOLO requirement).
            iou_threshold: NMS IOU threshold for overlapping detections.
                          Default 0.50.

        Returns:
            List of SegmentResult objects, sorted by confidence (highest first).
            Empty list if no containers detected above conf_threshold.

        Raises:
            FileNotFoundError: If image_path doesn't exist.
            ValueError: If worker_id < 0 or conf_threshold not in [0, 1].
            RuntimeError: If YOLO inference fails.

        Performance:
            CPU: ~800ms for 4000x3000px image
            GPU: ~200ms for same image (3-5x speedup)

        Example:
            >>> service = SegmentationService()
            >>> results = await service.segment_image(
            ...     "/photos/greenhouse_001.jpg",
            ...     worker_id=0,
            ...     conf_threshold=0.35
            ... )
            >>> # Returns list of 12 SegmentResult objects
        """
        # Validate inputs
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if worker_id < 0:
            raise ValueError(f"worker_id must be >= 0, got {worker_id}")

        if not 0.0 <= conf_threshold <= 1.0:
            raise ValueError(f"conf_threshold must be in [0.0, 1.0], got {conf_threshold}")

        # Get model from singleton (lazy load)
        if self._model is None or self._worker_id != worker_id:
            logger.info(
                f"Loading segmentation model for worker {worker_id} " f"(lazy initialization)"
            )
            self._model = ModelCache.get_model("segment", worker_id)
            self._worker_id = worker_id
            logger.info("Segmentation model loaded successfully")

        # Run YOLO inference
        try:
            logger.debug(
                f"Running segmentation on {image_path.name} "
                f"(conf≥{conf_threshold}, imgsz={imgsz})"
            )

            results = self._model.predict(
                source=str(image_path),
                imgsz=imgsz,
                conf=conf_threshold,
                iou=iou_threshold,
                verbose=False,  # Suppress YOLO console output
                device=None,  # Use model's assigned device (from ModelCache)
            )

            # Parse YOLO results into SegmentResult objects
            segments = self._parse_results(results[0])  # First image

            logger.info(
                f"Segmented {len(segments)} containers from {image_path.name} "
                f"(conf≥{conf_threshold}): "
                f"{self._summarize_detections(segments)}"
            )

            return segments

        except Exception as e:
            logger.error(f"Segmentation failed for {image_path.name}: {e}", exc_info=True)
            raise RuntimeError(f"Segmentation failed: {e}") from e

    def _parse_results(self, result: "Results") -> list[SegmentResult]:
        """Parse YOLO Results object into SegmentResult objects.

        Extracts polygon masks, bounding boxes, confidence scores, and
        class labels from YOLO output. Remaps YOLO class names to
        standardized container types.

        Args:
            result: YOLO Results object from model.predict()

        Returns:
            List of SegmentResult objects, sorted by confidence descending.
        """
        segments: list[SegmentResult] = []

        # Check if any detections found
        if result.masks is None or len(result.masks) == 0:
            logger.debug("No containers detected in image")
            return segments

        # Get original image dimensions
        img_height, img_width = result.masks.orig_shape

        # Extract detections
        for box, mask_coords, cls, conf in zip(
            result.boxes.xyxyn,  # Normalized bboxes (x1, y1, x2, y2)
            result.masks.xy,  # Polygon coordinates (N, 2)
            result.boxes.cls,  # Class IDs
            result.boxes.conf,
            strict=False,  # Confidence scores
        ):
            # Get YOLO class name
            class_id = int(cls.item())
            yolo_class = result.names[class_id]

            # Remap to standardized container type
            container_type = self._remap_container_type(yolo_class)

            # Extract normalized bbox coordinates
            x1, y1, x2, y2 = (float(coord) for coord in box.tolist())

            # Convert polygon coordinates to normalized tuples
            # mask_coords is numpy array of shape (N, 2) with absolute pixels
            polygon = [(float(x) / img_width, float(y) / img_height) for x, y in mask_coords]

            # Calculate approximate area from bbox (in pixels)
            width_px = (x2 - x1) * img_width
            height_px = (y2 - y1) * img_height
            area_pixels = int(width_px * height_px)

            # Create SegmentResult
            segments.append(
                SegmentResult(
                    container_type=container_type,
                    confidence=float(conf.item()),
                    bbox=(x1, y1, x2, y2),
                    polygon=polygon,
                    area_pixels=area_pixels,
                )
            )

        # Sort by confidence (highest first)
        segments.sort(key=lambda s: s.confidence, reverse=True)

        return segments

    def _remap_container_type(self, yolo_class: str) -> str:
        """Remap YOLO class name to standardized container type.

        Handles variations in class naming from different model versions
        and training data sources.

        Args:
            yolo_class: YOLO model output class name (e.g., "claro-cajon")

        Returns:
            Standardized container type: "plug", "box", or "segment"

        Raises:
            ValueError: If yolo_class not recognized (should never happen
                       if model trained correctly)
        """
        # Normalize to lowercase
        yolo_class_lower = yolo_class.lower()

        # Lookup in mapping
        container_type = self.CONTAINER_TYPE_MAPPING.get(yolo_class_lower)

        if container_type is None:
            # Fallback: If class not in mapping, assume it's already standardized
            # (e.g., model already outputs "plug", "box", "segment")
            if yolo_class_lower in {"plug", "box", "segment"}:
                return yolo_class_lower

            # Unknown class - log warning and return as-is
            logger.warning(
                f"Unknown YOLO class '{yolo_class}'. Returning as-is. "
                f"Check model training data or update CONTAINER_TYPE_MAPPING."
            )
            return yolo_class_lower

        return container_type

    @staticmethod
    def _summarize_detections(segments: list[SegmentResult]) -> str:
        """Create summary string of detections by type.

        Args:
            segments: List of SegmentResult objects

        Returns:
            Summary string like "3 plugs, 2 boxes, 1 segment"
        """
        if not segments:
            return "none"

        # Count by type
        counts: dict[str, int] = {}
        for seg in segments:
            counts[seg.container_type] = counts.get(seg.container_type, 0) + 1

        # Format as string
        parts = [
            f"{count} {ctype}{'s' if count > 1 else ''}" for ctype, count in sorted(counts.items())
        ]

        return ", ".join(parts)
