"""ML Celery Tasks - Complete ML Pipeline Orchestration.

This module implements the complete Celery task workflow for ML-based photo processing:
- CEL004: Chord pattern implementation (parent → children → callback)
- CEL005: ML parent task (spawns child tasks per image)
- CEL006: ML child tasks (YOLO + SAHI + estimation pipeline)
- CEL007: Callback aggregation (combines results, updates session)
- CEL008: Circuit breaker + retry logic with exponential backoff

Architecture:
    Layer: Task Layer (Async Queue Processing)
    Pattern: Celery chord (parent → [child1, child2, ...] → callback)
    Routing: gpu_queue (ML tasks), cpu_queue (aggregation)
    Retry: Exponential backoff (2s, 4s, 8s), max 3 retries

Task Flow:
    1. ml_parent_task(session_id, image_ids) [CPU queue]
       ├─> Spawns N child tasks (one per image)
       └─> Uses chord pattern: chord([children])(callback)

    2. ml_child_task(session_id, image_id, image_path) [GPU queue]
       ├─> Loads YOLO model
       ├─> Runs complete ML pipeline (segmentation → detection → estimation)
       ├─> Returns: {detections, estimations, avg_confidence, ...}
       └─> Retry: 3 times with exponential backoff

    3. ml_aggregation_callback(results, session_id) [CPU queue]
       ├─> Aggregates all child results
       ├─> Updates PhotoProcessingSession (status, counts, confidence)
       └─> Creates StockBatch record

Performance:
    - CPU: 5-10 minutes per 4000×3000px photo
    - GPU: 1-3 minutes per photo (3-5x speedup)
    - Queue routing prevents GPU starvation

Error Handling:
    - Partial failures: Chord callback receives partial results
    - Max retries: 3 attempts with 2s, 4s, 8s backoff
    - Circuit breaker: Fails fast after max retries
    - DLQ: Failed tasks logged for manual inspection

Example:
    >>> # Trigger ML processing for session
    >>> result = ml_parent_task.delay(session_id=123, image_ids=[1, 2, 3])
    >>> # Celery spawns 3 child tasks, aggregates results in callback
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from celery import Task, chord  # type: ignore[import-not-found]

from app.celery_app import app
from app.core.exceptions import (
    CircuitBreakerException,
    ValidationException,
)
from app.core.logging import get_logger
from app.services.ml_processing.band_estimation_service import BandEstimationService
from app.services.ml_processing.pipeline_coordinator import (
    MLPipelineCoordinator,
    PipelineResult,
)
from app.services.ml_processing.sahi_detection_service import SAHIDetectionService
from app.services.ml_processing.segmentation_service import SegmentationService

logger = get_logger(__name__)

# Circuit Breaker Configuration (CEL008)
CIRCUIT_BREAKER_THRESHOLD = 5  # Open circuit after 5 consecutive failures
CIRCUIT_BREAKER_TIMEOUT = 300  # 5 minutes cooldown before retry
circuit_breaker_state: dict[str, Any] = {
    "failures": 0,
    "last_failure_time": None,
    "state": "closed",  # closed, open, half_open
}


# ═══════════════════════════════════════════════════════════════════════════
# CEL008: Circuit Breaker Helper Functions
# ═══════════════════════════════════════════════════════════════════════════


def check_circuit_breaker() -> None:
    """Check circuit breaker state before executing task.

    Circuit Breaker States:
        - closed: Normal operation (failures < threshold)
        - open: Too many failures (reject all requests for timeout period)
        - half_open: Testing recovery (allow 1 request to test)

    Raises:
        CircuitBreakerException: If circuit is open (too many failures)

    Business Rules:
        - Circuit opens after 5 consecutive failures
        - Circuit stays open for 5 minutes (cooldown)
        - After cooldown, transitions to half_open (test recovery)
    """
    global circuit_breaker_state

    state = circuit_breaker_state["state"]

    if state == "closed":
        # Normal operation
        return

    if state == "open":
        # Check if cooldown period has passed
        last_failure = circuit_breaker_state["last_failure_time"]
        if last_failure is not None:
            elapsed = (datetime.utcnow() - last_failure).total_seconds()
            if elapsed >= CIRCUIT_BREAKER_TIMEOUT:
                # Transition to half_open (test recovery)
                circuit_breaker_state["state"] = "half_open"
                logger.info("Circuit breaker transitioning to HALF_OPEN (testing recovery)")
                return

        # Circuit still open
        failures = circuit_breaker_state["failures"]
        raise CircuitBreakerException(
            reason=f"Circuit breaker OPEN due to {failures} failures. "
            f"Retry after cooldown period ({CIRCUIT_BREAKER_TIMEOUT}s)."
        )

    if state == "half_open":
        # Allow request to test recovery
        logger.info("Circuit breaker HALF_OPEN: Allowing test request")
        return


def record_circuit_breaker_success() -> None:
    """Record successful task execution (reset circuit breaker)."""
    global circuit_breaker_state

    state = circuit_breaker_state["state"]

    if state == "half_open":
        # Recovery successful, close circuit
        circuit_breaker_state["state"] = "closed"
        circuit_breaker_state["failures"] = 0
        circuit_breaker_state["last_failure_time"] = None
        logger.info("Circuit breaker CLOSED (recovery successful)")
    elif state == "closed":
        # Reset failure counter on success
        circuit_breaker_state["failures"] = 0


def record_circuit_breaker_failure() -> None:
    """Record task failure (increment circuit breaker counter)."""
    global circuit_breaker_state

    failures = int(circuit_breaker_state["failures"]) + 1
    circuit_breaker_state["failures"] = failures
    circuit_breaker_state["last_failure_time"] = datetime.utcnow()

    if failures >= CIRCUIT_BREAKER_THRESHOLD:
        # Open circuit
        circuit_breaker_state["state"] = "open"
        logger.error(
            f"Circuit breaker OPENED after {failures} failures. "
            f"Cooldown: {CIRCUIT_BREAKER_TIMEOUT}s"
        )
    else:
        logger.warning(f"Circuit breaker failure recorded: {failures}/{CIRCUIT_BREAKER_THRESHOLD}")


# ═══════════════════════════════════════════════════════════════════════════
# Helper: Container Type Mapping
# ═══════════════════════════════════════════════════════════════════════════


def _map_container_type_to_bin_category(container_type: str) -> str:
    """Map ML container type to StorageBinType category (BinCategoryEnum).

    Converts ML segmentation container types (lowercase) to database enum values.
    This ensures consistency between ML pipeline output and database schema.

    Args:
        container_type: Container type from ML pipeline ("segment", "box", "plug", etc.)

    Returns:
        str: BinCategoryEnum value ("segment", "box", "plug", "seedling_tray", "pot")

    Mapping:
        - "segment" → "segment"
        - "box" → "box"
        - "cajon" → "box" (Spanish synonym)
        - "plug" → "plug"
        - "almacigo" → "seedling_tray" (Spanish synonym)
        - Unknown → "segment" (default fallback)

    Example:
        >>> _map_container_type_to_bin_category("segment")
        "segment"
        >>> _map_container_type_to_bin_category("cajon")
        "box"
        >>> _map_container_type_to_bin_category("unknown")
        "segment"
    """
    mapping = {
        "segment": "segment",
        "box": "box",
        "cajon": "box",
        "plug": "plug",
        "almacigo": "seedling_tray",
    }
    normalized = container_type.lower().strip()
    return mapping.get(normalized, "segment")


# ═══════════════════════════════════════════════════════════════════════════
# CEL005: ML Parent Task (Chord Orchestration)
# ═══════════════════════════════════════════════════════════════════════════


@app.task(bind=True, queue="cpu_queue", max_retries=2)  # type: ignore[misc]
def ml_parent_task(
    self: Task,
    session_id: int,
    image_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """ML parent task: Spawns child tasks using chord pattern (CEL004, CEL005).

    This task orchestrates ML processing for multiple images:
    1. Updates PhotoProcessingSession to PROCESSING status
    2. Creates child task for each image (parallel execution)
    3. Uses Celery chord: chord([child1, child2, ...])(callback)
    4. Callback aggregates results when all children complete

    Args:
        session_id: PhotoProcessingSession database ID (integer PK)
        image_data: List of image metadata dicts with keys:
            - image_id (str): S3Image UUID as string (for tracking)
            - image_path (str): Local path or S3 key to image file
            - storage_location_id (int): Where photo was taken

    Returns:
        dict with:
            - session_id (int): PhotoProcessingSession ID
            - num_images (int): Number of child tasks spawned
            - status (str): "processing"
            - celery_task_id (str): Parent task ID

    Raises:
        ResourceNotFoundException: If session not found
        ValidationException: If image_data is empty
        CircuitBreakerException: If circuit breaker is open

    Queue Routing:
        - This task: cpu_queue (orchestration is CPU-bound)
        - Child tasks: gpu_queue (YOLO inference is GPU-intensive)
        - Callback: cpu_queue (aggregation is CPU-bound)

    Example:
        >>> image_data = [
        ...     {"image_id": 1, "image_path": "/photos/001.jpg", "storage_location_id": 10},
        ...     {"image_id": 2, "image_path": "/photos/002.jpg", "storage_location_id": 10},
        ... ]
        >>> result = ml_parent_task.delay(session_id=123, image_data=image_data)
        >>> # Spawns 2 child tasks on GPU queue → callback on CPU queue
    """
    logger.info(
        f"ML parent task started for session {session_id} with {len(image_data)} images",
        extra={"session_id": session_id, "num_images": len(image_data), "task_id": self.request.id},
    )

    # CEL008: Check circuit breaker before processing
    try:
        check_circuit_breaker()
    except CircuitBreakerException as e:
        logger.error(
            f"Circuit breaker OPEN: Rejecting task for session {session_id}",
            extra={"session_id": session_id, "reason": str(e)},
        )
        # Mark session as failed
        _mark_session_failed(session_id, str(e))
        raise

    # Validation: image_data must not be empty
    if not image_data:
        error_msg = "image_data cannot be empty"
        logger.error(error_msg, extra={"session_id": session_id})
        _mark_session_failed(session_id, error_msg)
        raise ValidationException(field="image_data", message=error_msg)

    try:
        # Update session to PROCESSING status
        _mark_session_processing(session_id, celery_task_id=self.request.id)

        # CEL004: Create child task signatures (one per image)
        # Each child task runs on GPU queue for ML inference
        child_signatures = [
            ml_child_task.s(
                session_id=session_id,
                image_id=img["image_id"],
                image_path=img["image_path"],
                storage_location_id=img["storage_location_id"],
            )
            for img in image_data
        ]

        logger.info(
            f"Spawning {len(child_signatures)} child tasks for session {session_id}",
            extra={"session_id": session_id, "num_children": len(child_signatures)},
        )

        # CEL004: Chord pattern - children run in parallel → callback aggregates
        # chord([child1, child2, ...])(callback)
        callback = ml_aggregation_callback.s(session_id=session_id)
        chord(child_signatures)(callback)

        logger.info(
            f"Chord dispatched for session {session_id}: {len(child_signatures)} children → callback",
            extra={"session_id": session_id, "task_id": self.request.id},
        )

        return {
            "session_id": session_id,
            "num_images": len(image_data),
            "status": "processing",
            "celery_task_id": self.request.id,
        }

    except Exception as exc:
        logger.error(
            f"ML parent task failed for session {session_id}: {exc}",
            extra={"session_id": session_id, "error": str(exc)},
            exc_info=True,
        )
        _mark_session_failed(session_id, str(exc))
        record_circuit_breaker_failure()

        # Retry with exponential backoff (CEL008)
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


# ═══════════════════════════════════════════════════════════════════════════
# CEL006: ML Child Task (YOLO Pipeline Processing)
# ═══════════════════════════════════════════════════════════════════════════


@app.task(bind=True, queue="gpu_queue", max_retries=3)  # type: ignore[misc]
def ml_child_task(
    self: Task,
    session_id: int,
    image_id: str,  # S3Image UUID as string
    image_path: str,
    storage_location_id: int,
) -> dict[str, Any]:
    """ML child task: Process one image through complete ML pipeline (CEL006).

    This task runs on GPU worker (pool=solo) to prevent CUDA context conflicts.
    Executes complete ML pipeline:
    1. Segmentation (detect containers: plugs, boxes, segments)
    2. Detection (SAHI tiled detection for individual plants)
    3. Estimation (band-based estimation for undetected areas)

    Args:
        session_id: PhotoProcessingSession database ID (integer PK)
        image_id: S3Image UUID as string (for tracking/logging)
        image_path: Path to image file (local or S3 key)
        storage_location_id: Storage location where photo was taken

    Returns:
        dict with ML results:
            - image_id (int): S3Image ID
            - total_detected (int): Total plants detected
            - total_estimated (int): Total plants estimated
            - avg_confidence (float): Average detection confidence (0.0-1.0)
            - segments_processed (int): Number of containers processed
            - processing_time_seconds (float): Pipeline elapsed time
            - detections (list[dict]): Detection records for bulk insert
            - estimations (list[dict]): Estimation records for bulk insert

    Raises:
        FileNotFoundError: If image_path doesn't exist
        RuntimeError: If ML pipeline fails critically
        MaxRetriesExceededError: After 3 failed retries

    Queue Routing:
        - Queue: gpu_queue (YOLO inference requires GPU)
        - Pool: solo (MANDATORY - prevents CUDA context conflicts)
        - Concurrency: 1 (single process, GPU-exclusive)

    Retry Logic (CEL008):
        - Max retries: 3
        - Backoff: Exponential (2s, 4s, 8s)
        - Countdown: 2^retry_count seconds

    Example:
        >>> result = ml_child_task.delay(
        ...     session_id=123,
        ...     image_id=1,
        ...     image_path="/photos/greenhouse_001.jpg",
        ...     storage_location_id=10
        ... )
        >>> # Returns: {"total_detected": 842, "total_estimated": 158, ...}
    """
    logger.info(
        f"ML child task started for session {session_id}, image {image_id}",
        extra={
            "session_id": session_id,
            "image_id": image_id,
            "image_path": image_path,
            "task_id": self.request.id,
        },
    )

    try:
        # Priority order: PostgreSQL → /tmp local cache → S3 download
        # This enables Celery workers in separate containers to access images efficiently

        image_file = Path(image_path)
        is_local_file = image_file.exists() and image_file.is_absolute()

        # Determine the actual path to use for processing
        processing_path = image_path
        temp_file_created = False

        if not is_local_file:
            temp_path = f"/tmp/{image_id}.jpg"
            temp_file = Path(temp_path)

            # PRIORITY 1: Check PostgreSQL for cached binary data (fastest)
            logger.info(
                f"Checking PostgreSQL for cached image data: {image_id}",
                extra={"image_id": image_id},
            )

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            from app.core.config import settings
            from app.models.s3_image import S3Image

            # Create synchronous engine for Celery tasks
            sync_engine = create_engine(
                settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
            db_session = SyncSession()

            try:
                # Query for image_data from PostgreSQL
                s3_image = db_session.query(S3Image).filter(S3Image.image_id == image_id).first()

                if s3_image and s3_image.image_data:
                    # Found binary data in PostgreSQL - write to /tmp
                    logger.info(
                        f"Found image data in PostgreSQL ({len(s3_image.image_data)} bytes), writing to {temp_path}",
                        extra={"image_id": image_id, "size_bytes": len(s3_image.image_data)},
                    )

                    with open(temp_path, "wb") as f:
                        f.write(s3_image.image_data)

                    processing_path = temp_path
                    temp_file_created = True

                    logger.info(
                        "Successfully loaded image from PostgreSQL",
                        extra={"image_id": image_id, "temp_path": temp_path},
                    )

                # PRIORITY 2: Check /tmp local cache (retry optimization)
                elif temp_file.exists():
                    # File already exists in /tmp from previous run
                    logger.info(
                        f"Using cached file from /tmp: {temp_path}",
                        extra={"image_path": image_path, "temp_path": temp_path},
                    )
                    processing_path = temp_path

                # PRIORITY 3: Download from S3 (fallback)
                else:
                    logger.info(
                        f"Image not found in PostgreSQL or /tmp, downloading from S3: {image_path}",
                        extra={"s3_path": image_path, "temp_path": temp_path},
                    )

                    # Download image from S3 to temp file
                    import boto3

                    s3 = boto3.client("s3")
                    s3.download_file("demeter-photos-original", image_path, temp_path)
                    processing_path = temp_path
                    temp_file_created = True

                    logger.info(
                        f"Successfully downloaded image from S3 to {temp_path}",
                        extra={"s3_path": image_path, "temp_path": temp_path},
                    )

            finally:
                db_session.close()
                sync_engine.dispose()

        # Initialize ML services (dependency injection)
        # Services handle model loading/caching via ModelCache singleton
        segmentation_service = SegmentationService()
        sahi_service = SAHIDetectionService(worker_id=0)  # Worker 0 (GPU-exclusive)
        band_estimation_service = BandEstimationService()

        # Initialize pipeline coordinator
        coordinator = MLPipelineCoordinator(
            segmentation_service=segmentation_service,
            sahi_service=sahi_service,
            band_estimation_service=band_estimation_service,
        )

        # Run complete ML pipeline (blocking, async coordination handled internally)
        # This is CPU/GPU intensive (5-10 mins CPU, 1-3 mins GPU)
        import asyncio

        logger.info(
            f"Processing image: {processing_path}",
            extra={"processing_path": processing_path, "is_local": is_local_file},
        )

        result: PipelineResult = asyncio.run(
            coordinator.process_complete_pipeline(
                session_id=session_id,
                image_path=processing_path,
                worker_id=0,  # GPU worker 0
                conf_threshold_segment=0.30,
                conf_threshold_detect=0.25,
            )
        )

        # PROBLEM 4 FIX: DON'T delete temp file here!
        # Temp files are needed by _generate_visualization_image in callback
        # Cleanup happens in ml_aggregation_callback after visualization completes
        logger.info(
            f"Keeping temp file for visualization generation: {processing_path}",
            extra={"temp_path": processing_path, "temp_file_created": temp_file_created},
        )

        logger.info(
            f"ML child task completed for session {session_id}, image {image_id}: "
            f"{result.total_detected} detected, {result.total_estimated} estimated",
            extra={
                "session_id": session_id,
                "image_id": image_id,
                "total_detected": result.total_detected,
                "total_estimated": result.total_estimated,
                "processing_time": result.processing_time_seconds,
            },
        )

        # CEL008: Record success (reset circuit breaker)
        record_circuit_breaker_success()

        # Convert SegmentResult objects to dict format for JSON serialization
        segments_dict = [
            {
                "container_type": seg.container_type,
                "confidence": seg.confidence,
                "bbox": seg.bbox,  # (x1, y1, x2, y2) normalized
                "polygon": seg.polygon,  # List of (x, y) tuples normalized
                "area_pixels": seg.area_pixels,  # Fixed: was mask_area
            }
            for seg in result.segments
        ]

        # Return results for chord callback aggregation
        return {
            "image_id": image_id,
            "total_detected": result.total_detected,
            "total_estimated": result.total_estimated,
            "avg_confidence": result.avg_confidence,
            "segments_processed": result.segments_processed,
            "processing_time_seconds": result.processing_time_seconds,
            "detections": result.detections,
            "estimations": result.estimations,
            "segments": segments_dict,  # NEW: Include segments for StorageBin creation
        }

    except FileNotFoundError as e:
        logger.error(
            f"ML child task failed (image not found) for session {session_id}, image {image_id}: {e}",
            extra={"session_id": session_id, "image_id": image_id, "error": str(e)},
        )
        # Don't retry if file doesn't exist (permanent failure)
        record_circuit_breaker_failure()
        raise

    except Exception as exc:
        logger.error(
            f"ML child task failed for session {session_id}, image {image_id}: {exc}",
            extra={
                "session_id": session_id,
                "image_id": image_id,
                "error": str(exc),
                "retry_count": self.request.retries,
            },
            exc_info=True,
        )

        # CEL008: Record failure
        record_circuit_breaker_failure()

        # CEL008: Retry with exponential backoff
        countdown = 2**self.request.retries  # 2s, 4s, 8s
        logger.warning(
            f"Retrying ML child task for session {session_id}, image {image_id} "
            f"in {countdown}s (attempt {self.request.retries + 1}/{self.max_retries})",
            extra={"session_id": session_id, "image_id": image_id, "countdown": countdown},
        )

        raise self.retry(exc=exc, countdown=countdown) from exc


# ═══════════════════════════════════════════════════════════════════════════
# CEL007: Callback Aggregation
# ═══════════════════════════════════════════════════════════════════════════


@app.task(queue="cpu_queue")  # type: ignore[misc]
def ml_aggregation_callback(
    results: list[dict[str, Any]],
    session_id: int,
) -> dict[str, Any]:
    """Callback: Aggregate all child task results and update session (CEL007).

    This callback runs after ALL child tasks complete (or fail). It aggregates
    ML results from all images and updates the PhotoProcessingSession with
    final counts, confidence, and status.

    Chord Pattern:
        chord([child1, child2, child3])(callback)
        └─> callback receives: [result1, result2, result3]

    Args:
        results: List of child task results (one per image)
        session_id: PhotoProcessingSession database ID

    Returns:
        dict with aggregated results:
            - session_id (int): PhotoProcessingSession ID
            - num_images_processed (int): Number of successful child tasks
            - total_detected (int): Sum of all detections
            - total_estimated (int): Sum of all estimations
            - avg_confidence (float): Average confidence across all images
            - status (str): "completed" or "warning" (if partial failures)

    Business Rules:
        - Partial failures: If some children fail, callback still runs with partial results
        - Warning state: If < 100% images processed, status → "warning" (not "failed")
        - Completed state: If all images processed successfully, status → "completed"
        - Empty results: If all children fail, status → "failed"

    Queue Routing:
        - Queue: cpu_queue (aggregation is CPU-bound, not GPU)

    Example:
        >>> results = [
        ...     {"image_id": 1, "total_detected": 842, "total_estimated": 158, "avg_confidence": 0.87},
        ...     {"image_id": 2, "total_detected": 756, "total_estimated": 134, "avg_confidence": 0.82},
        ... ]
        >>> callback_result = ml_aggregation_callback(results, session_id=123)
        >>> # Updates session: total_detected=1598, total_estimated=292, avg_confidence=0.845
    """
    logger.info(
        f"ML aggregation callback started for session {session_id} with {len(results)} results",
        extra={"session_id": session_id, "num_results": len(results)},
    )

    try:
        # Filter out None results (failed child tasks)
        valid_results = [r for r in results if r is not None]
        num_valid = len(valid_results)
        num_total = len(results)

        if num_valid == 0:
            # All children failed
            logger.error(
                f"ML aggregation callback: ALL child tasks failed for session {session_id}",
                extra={"session_id": session_id, "num_failed": num_total},
            )
            _mark_session_failed(
                session_id, f"All {num_total} child tasks failed during ML processing"
            )
            return {
                "session_id": session_id,
                "num_images_processed": 0,
                "status": "failed",
                "error": "All child tasks failed",
            }

        # Aggregate results
        total_detected = sum(r.get("total_detected", 0) for r in valid_results)
        total_estimated = sum(r.get("total_estimated", 0) for r in valid_results)
        avg_confidence = (
            sum(r.get("avg_confidence", 0.0) for r in valid_results) / num_valid
            if num_valid > 0
            else 0.0
        )

        # Aggregate all detections/estimations/segments for bulk insert
        all_detections = []
        all_estimations = []
        all_segments = []
        for r in valid_results:
            all_detections.extend(r.get("detections", []))
            all_estimations.extend(r.get("estimations", []))
            all_segments.extend(r.get("segments", []))  # NEW: Aggregate segments

        logger.info(
            f"ML aggregation callback: Aggregated {num_valid}/{num_total} images for session {session_id}",
            extra={
                "session_id": session_id,
                "total_detected": total_detected,
                "total_estimated": total_estimated,
                "avg_confidence": avg_confidence,
                "num_valid": num_valid,
                "num_total": num_total,
                "num_detections": len(all_detections),
                "num_estimations": len(all_estimations),
                "num_segments": len(all_segments),  # NEW: Log segments count
            },
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # GET STORAGE_LOCATION_ID FROM PHOTO_PROCESSING_SESSION
        # ═══════════════════════════════════════════════════════════════════════════
        # Retrieve storage_location_id for StorageBin creation
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.core.config import settings
        from app.models.photo_processing_session import PhotoProcessingSession

        sync_engine = create_engine(
            settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
        db_session = SyncSession()

        try:
            session_record = (
                db_session.query(PhotoProcessingSession).filter_by(id=session_id).first()
            )
            storage_location_id = session_record.storage_location_id if session_record else None

            logger.info(
                f"ML aggregation callback: Retrieved storage_location_id={storage_location_id} for session {session_id}",
                extra={"session_id": session_id, "storage_location_id": storage_location_id},
            )
        finally:
            db_session.close()
            sync_engine.dispose()

        # ═══════════════════════════════════════════════════════════════════════════
        # PERSIST DETECTIONS, ESTIMATIONS, AND STORAGE BINS TO DATABASE
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(
            f"ML aggregation callback: Persisting {len(all_detections)} detections, "
            f"{len(all_estimations)} estimations, and {len(all_segments)} segments to database for session {session_id}"
        )

        try:
            _persist_ml_results(
                session_id=session_id,
                detections=all_detections,
                estimations=all_estimations,
                segments=all_segments,  # NEW: Pass segments
                storage_location_id=storage_location_id,  # NEW: Pass storage_location_id
            )
            logger.info(
                f"ML aggregation callback: Successfully persisted ML results for session {session_id}",
                extra={
                    "session_id": session_id,
                    "num_detections": len(all_detections),
                    "num_estimations": len(all_estimations),
                },
            )
        except Exception as e:
            # WARNING: Don't crash if persistence fails - mark session with warning
            logger.error(
                f"ML aggregation callback: Failed to persist ML results for session {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            # Continue processing but mark as warning status

        # ═══════════════════════════════════════════════════════════════════════════
        # GENERATE VISUALIZATION IMAGE AND UPLOAD TO S3
        # ═══════════════════════════════════════════════════════════════════════════
        processed_image_id = None

        try:
            logger.info(
                f"ML aggregation callback: Generating visualization for session {session_id}",
                extra={"session_id": session_id},
            )

            # Generate visualization image (returns temp file path or None)
            viz_path = _generate_visualization(
                session_id=session_id,
                detections=all_detections,
                estimations=all_estimations,
            )

            if viz_path and Path(viz_path).exists():
                logger.info(
                    f"ML aggregation callback: Visualization generated at {viz_path}, uploading to S3",
                    extra={"session_id": session_id, "viz_path": viz_path},
                )

                # Upload visualization to S3

                # Create synchronous DB session for S3 upload
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker

                from app.core.config import settings

                sync_engine = create_engine(
                    settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )
                SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
                db_session = SyncSession()

                try:
                    # Convert sync session to async-compatible (run S3ImageService in sync context)
                    # Create repo with sync session (wrap async methods with asyncio.run)
                    from uuid import uuid4

                    # Read visualization file
                    with open(viz_path, "rb") as f:
                        viz_bytes = f.read()

                    logger.info(
                        f"ML aggregation callback: Read visualization file ({len(viz_bytes)} bytes)",
                        extra={"session_id": session_id, "file_size": len(viz_bytes)},
                    )

                    # Upload to S3 using boto3 directly (avoid async complexity in Celery)
                    import boto3

                    s3_client = boto3.client("s3")

                    # PROBLEM 1 FIX: Get UUID session_id from database (session_id param is INTEGER id)
                    # Query PhotoProcessingSession to get UUID session_id
                    from app.models.photo_processing_session import (
                        PhotoProcessingSession as SessionModel,
                    )

                    session_record = db_session.query(SessionModel).filter_by(id=session_id).first()
                    if not session_record:
                        logger.error(
                            f"ML aggregation callback: Session {session_id} not found for UUID lookup",
                            extra={"session_id": session_id},
                        )
                        raise ValueError(f"Session {session_id} not found")

                    session_uuid = session_record.session_id  # This is the UUID!

                    # S3 key format: {UUID}/processed.avif
                    viz_s3_key = f"{session_uuid}/processed.avif"

                    logger.info(
                        f"ML aggregation callback: Uploading visualization to S3: {viz_s3_key}",
                        extra={
                            "session_id": session_id,
                            "session_uuid": str(session_uuid),
                            "s3_key": viz_s3_key,
                            "bucket": settings.S3_BUCKET_ORIGINAL,
                        },
                    )

                    # Upload processed visualization to original bucket (new folder structure)
                    s3_client.put_object(
                        Bucket=settings.S3_BUCKET_ORIGINAL,  # NEW: Changed from S3_BUCKET_VISUALIZATION
                        Key=viz_s3_key,
                        Body=viz_bytes,
                        ContentType="image/avif",
                    )

                    logger.info(
                        f"ML aggregation callback: Visualization uploaded to S3: {viz_s3_key}",
                        extra={"session_id": session_id, "s3_key": viz_s3_key},
                    )

                    # PROBLEM 5 FIX: Generate TWO thumbnails (original + processed)

                    # THUMBNAIL 1: Original image thumbnail
                    try:
                        from app.services.photo.s3_image_service import generate_thumbnail

                        # Read original image from /tmp (already downloaded via 3-tier cache)
                        original_temp_path = f"/tmp/session_{session_id}_original.jpg"
                        if Path(original_temp_path).exists():
                            with open(original_temp_path, "rb") as f:
                                original_bytes = f.read()

                            # Generate thumbnail from original
                            thumbnail_original_bytes = generate_thumbnail(
                                original_bytes, size=settings.S3_THUMBNAIL_SIZE
                            )

                            # S3 key format: {UUID}/thumbnail_original.jpg
                            thumbnail_original_s3_key = f"{session_uuid}/thumbnail_original.jpg"

                            logger.info(
                                f"ML aggregation callback: Uploading original thumbnail to S3: {thumbnail_original_s3_key}",
                                extra={
                                    "session_id": session_id,
                                    "s3_key": thumbnail_original_s3_key,
                                    "thumbnail_size": len(thumbnail_original_bytes),
                                },
                            )

                            # Upload original thumbnail to S3
                            s3_client.put_object(
                                Bucket=settings.S3_BUCKET_ORIGINAL,
                                Key=thumbnail_original_s3_key,
                                Body=thumbnail_original_bytes,
                                ContentType="image/jpeg",
                            )

                            logger.info(
                                f"ML aggregation callback: Original thumbnail uploaded to S3: {thumbnail_original_s3_key}",
                                extra={
                                    "session_id": session_id,
                                    "s3_key": thumbnail_original_s3_key,
                                },
                            )

                        else:
                            logger.warning(
                                "ML aggregation callback: Original image not found in /tmp, skipping original thumbnail",
                                extra={
                                    "session_id": session_id,
                                    "expected_path": original_temp_path,
                                },
                            )

                    except Exception as thumb_original_error:
                        # Log but don't fail (thumbnail is optional)
                        logger.warning(
                            f"ML aggregation callback: Failed to generate/upload original thumbnail: {thumb_original_error}",
                            extra={"session_id": session_id, "error": str(thumb_original_error)},
                        )

                    # THUMBNAIL 2: Processed visualization thumbnail
                    try:
                        from app.services.photo.s3_image_service import generate_thumbnail

                        # Generate thumbnail from visualization (processed image)
                        thumbnail_processed_bytes = generate_thumbnail(
                            viz_bytes, size=settings.S3_THUMBNAIL_SIZE
                        )

                        # S3 key format: {UUID}/thumbnail_processed.jpg
                        thumbnail_processed_s3_key = f"{session_uuid}/thumbnail_processed.jpg"

                        logger.info(
                            f"ML aggregation callback: Uploading processed thumbnail to S3: {thumbnail_processed_s3_key}",
                            extra={
                                "session_id": session_id,
                                "s3_key": thumbnail_processed_s3_key,
                                "thumbnail_size": len(thumbnail_processed_bytes),
                            },
                        )

                        # Upload processed thumbnail to original bucket
                        s3_client.put_object(
                            Bucket=settings.S3_BUCKET_ORIGINAL,
                            Key=thumbnail_processed_s3_key,
                            Body=thumbnail_processed_bytes,
                            ContentType="image/jpeg",
                        )

                        logger.info(
                            f"ML aggregation callback: Processed thumbnail uploaded to S3: {thumbnail_processed_s3_key}",
                            extra={"session_id": session_id, "s3_key": thumbnail_processed_s3_key},
                        )

                    except Exception as thumb_processed_error:
                        # Log but don't fail (thumbnail is optional)
                        logger.warning(
                            f"ML aggregation callback: Failed to generate/upload processed thumbnail: {thumb_processed_error}",
                            extra={"session_id": session_id, "error": str(thumb_processed_error)},
                        )

                    # Create S3Image record in database for processed image
                    from app.models.s3_image import ImageTypeEnum, ProcessingStatusEnum, S3Image

                    viz_image_id = uuid4()
                    s3_image = S3Image(
                        image_id=viz_image_id,
                        s3_bucket=settings.S3_BUCKET_ORIGINAL,  # NEW: Changed from S3_BUCKET_VISUALIZATION
                        s3_key_original=viz_s3_key,  # Keep for backward compatibility
                        s3_key_processed=viz_s3_key,  # NEW: Store in processed key column
                        image_type=ImageTypeEnum.PROCESSED,  # NEW: Mark as processed image
                        content_type="image/avif",
                        file_size_bytes=len(viz_bytes),
                        width_px=0,  # Unknown (not critical for viz)
                        height_px=0,
                        upload_source="api",
                        status=ProcessingStatusEnum.READY,
                    )
                    db_session.add(s3_image)
                    db_session.commit()

                    processed_image_id = viz_image_id

                    logger.info(
                        "ML aggregation callback: S3Image record created for visualization",
                        extra={
                            "session_id": session_id,
                            "image_id": str(viz_image_id),
                            "s3_key": viz_s3_key,
                        },
                    )

                finally:
                    db_session.close()
                    sync_engine.dispose()

                # Cleanup temp visualization file
                if Path(viz_path).exists():
                    os.remove(viz_path)
                    logger.info(
                        f"ML aggregation callback: Cleaned up temp visualization file: {viz_path}",
                        extra={"session_id": session_id},
                    )

            else:
                logger.warning(
                    f"ML aggregation callback: Visualization generation skipped or failed for session {session_id}",
                    extra={"session_id": session_id},
                )

        except Exception as e:
            # WARNING: Don't crash if visualization fails - mark session with warning
            logger.error(
                f"ML aggregation callback: Failed to generate/upload visualization for session {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
                exc_info=True,
            )
            # Continue processing without visualization

        # Determine final status
        if num_valid < num_total:
            # Partial success (some children failed)
            status = "warning"
            logger.warning(
                f"ML processing completed with warnings for session {session_id}: "
                f"{num_valid}/{num_total} images processed successfully",
                extra={"session_id": session_id, "num_valid": num_valid, "num_total": num_total},
            )
        else:
            # Full success
            status = "completed"
            logger.info(
                f"ML processing completed successfully for session {session_id}: "
                f"{num_valid}/{num_total} images processed",
                extra={"session_id": session_id},
            )

        # Update PhotoProcessingSession with final results
        _mark_session_completed(
            session_id=session_id,
            total_detected=total_detected,
            total_estimated=total_estimated,
            total_empty_containers=0,
            # NOTE: Empty container detection via segment analysis (future enhancement)
            avg_confidence=avg_confidence,
            category_counts={},
            # NOTE: Category aggregation from detections (future enhancement)
            processed_image_id=processed_image_id,
            # Visualization image uploaded to S3 (None if generation failed)
        )

        # CLEANUP: Delete binary data from PostgreSQL after ML processing completes
        # This saves database space while keeping S3 as the source of truth
        image_ids_to_cleanup = [r.get("image_id") for r in valid_results if r.get("image_id")]
        if image_ids_to_cleanup:
            _cleanup_image_binary_data(image_ids_to_cleanup)

        # PROBLEM 4 FIX: Cleanup temp files after visualization completes
        # Delete all /tmp/session_{session_id}_*.{jpg,avif,webp} files
        try:
            import glob

            temp_pattern = f"/tmp/session_{session_id}_*"
            temp_files = glob.glob(temp_pattern)

            for temp_file in temp_files:
                try:
                    if Path(temp_file).exists():
                        os.remove(temp_file)
                        logger.info(
                            f"Cleaned up temp file: {temp_file}",
                            extra={"session_id": session_id, "temp_file": temp_file},
                        )
                except Exception as cleanup_error:
                    # Log but don't fail (cleanup is optional)
                    logger.warning(
                        f"Failed to cleanup temp file: {temp_file}: {cleanup_error}",
                        extra={
                            "session_id": session_id,
                            "temp_file": temp_file,
                            "error": str(cleanup_error),
                        },
                    )

            # Also cleanup temp files from ml_child_task (/tmp/{image_id}.jpg)
            for r in valid_results:
                image_id = r.get("image_id")
                if image_id:
                    temp_path = f"/tmp/{image_id}.jpg"
                    try:
                        if Path(temp_path).exists():
                            os.remove(temp_path)
                            logger.info(
                                f"Cleaned up child task temp file: {temp_path}",
                                extra={"session_id": session_id, "image_id": image_id},
                            )
                    except Exception as cleanup_error:
                        logger.warning(
                            f"Failed to cleanup child task temp file: {temp_path}: {cleanup_error}",
                            extra={
                                "session_id": session_id,
                                "image_id": image_id,
                                "error": str(cleanup_error),
                            },
                        )

        except Exception as e:
            # Log but don't fail (cleanup is optional)
            logger.warning(
                f"Failed to cleanup temp files for session {session_id}: {e}",
                extra={"session_id": session_id, "error": str(e)},
            )

        return {
            "session_id": session_id,
            "num_images_processed": num_valid,
            "total_detected": total_detected,
            "total_estimated": total_estimated,
            "avg_confidence": avg_confidence,
            "status": status,
        }

    except Exception as exc:
        logger.error(
            f"ML aggregation callback failed for session {session_id}: {exc}",
            extra={"session_id": session_id, "error": str(exc)},
            exc_info=True,
        )
        _mark_session_failed(session_id, f"Callback aggregation failed: {exc}")
        raise


# ═══════════════════════════════════════════════════════════════════════════
# Helper Functions (Database Updates)
# ═══════════════════════════════════════════════════════════════════════════


def _mark_session_processing(session_id: int, celery_task_id: str) -> None:
    """Mark session as PROCESSING (called by parent task).

    Args:
        session_id: PhotoProcessingSession database ID
        celery_task_id: Parent Celery task ID for tracking
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings

    # Create synchronous engine for Celery tasks
    # Celery workers run in separate processes with prefork pool
    # Can't use async engine in synchronous context
    sync_engine = create_engine(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SyncSession()

    try:
        from app.models.photo_processing_session import PhotoProcessingSession as SessionModel

        db_session = session.query(SessionModel).filter_by(id=session_id).first()
        if db_session:
            db_session.status = "processing"
            db_session.celery_task_id = celery_task_id
            session.commit()
            logger.info(
                "Session marked as processing",
                extra={"session_id": db_session.session_id, "celery_task_id": celery_task_id},
            )
    except Exception as e:
        session.rollback()
        logger.error(
            f"Failed to mark session processing: {e}",
            extra={"session_id": session_id, "error": str(e)},
            exc_info=True,
        )
        raise
    finally:
        session.close()
        sync_engine.dispose()


def _mark_session_completed(
    session_id: int,
    total_detected: int,
    total_estimated: int,
    total_empty_containers: int,
    avg_confidence: float,
    category_counts: dict[str, Any],
    processed_image_id: Any,
) -> None:
    """Mark session as COMPLETED with ML results (called by callback).

    Args:
        session_id: PhotoProcessingSession database ID
        total_detected: Total detections across all images
        total_estimated: Total estimations across all images
        total_empty_containers: Empty container count
        avg_confidence: Average ML confidence (0.0-1.0)
        category_counts: Detection counts by category
        processed_image_id: S3 image ID for visualization
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings

    # Create synchronous engine for Celery tasks
    sync_engine = create_engine(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SyncSession()

    try:
        from app.models.photo_processing_session import PhotoProcessingSession as SessionModel

        db_session = session.query(SessionModel).filter_by(id=session_id).first()
        if db_session:
            db_session.status = "completed"
            db_session.total_detected = total_detected
            db_session.total_estimated = total_estimated
            db_session.total_empty_containers = total_empty_containers
            db_session.avg_confidence = avg_confidence
            db_session.category_counts = category_counts
            db_session.processed_image_id = processed_image_id
            db_session.processing_end_time = datetime.utcnow()
            session.commit()
            logger.info(
                "Session marked as completed",
                extra={
                    "session_id": db_session.session_id,
                    "total_detected": total_detected,
                    "total_estimated": total_estimated,
                    "avg_confidence": avg_confidence,
                },
            )
    except Exception as e:
        session.rollback()
        logger.error(
            f"Failed to mark session completed: {e}",
            extra={"session_id": session_id, "error": str(e)},
            exc_info=True,
        )
        raise
    finally:
        session.close()
        sync_engine.dispose()


def _mark_session_failed(session_id: int, error_message: str) -> None:
    """Mark session as FAILED with error (called on errors).

    Args:
        session_id: PhotoProcessingSession database ID
        error_message: Error description
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings

    # Create synchronous engine for Celery tasks
    sync_engine = create_engine(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SyncSession()

    try:
        from app.models.photo_processing_session import PhotoProcessingSession as SessionModel

        db_session = session.query(SessionModel).filter_by(id=session_id).first()
        if db_session:
            db_session.status = "failed"
            db_session.error_message = error_message
            db_session.processing_end_time = datetime.utcnow()
            session.commit()
            logger.warning(
                "Session marked as failed",
                extra={"session_id": db_session.session_id, "error_message": error_message},
            )
    except Exception as e:
        session.rollback()
        logger.error(
            f"Failed to mark session as failed: {e}",
            extra={"session_id": session_id, "error": str(e)},
            exc_info=True,
        )
        # Silently ignore - can't update database if connection is broken
    finally:
        session.close()
        sync_engine.dispose()


def _cleanup_image_binary_data(image_ids: list[str]) -> None:
    """Delete binary image data from PostgreSQL after ML processing completes.

    This cleanup function removes the cached binary data (image_data column) from
    s3_images table to save database space. The images remain accessible via S3.

    Args:
        image_ids: List of S3Image UUIDs (as strings) to cleanup

    Business Rules:
        - Only called after ML processing completes successfully
        - Binary data deleted, but metadata preserved
        - S3 remains the source of truth for images
        - Failed deletions are logged but don't block workflow

    Note:
        Uses synchronous SQLAlchemy (Celery context requires sync DB operations)
    """
    if not image_ids:
        return

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings
    from app.models.s3_image import S3Image

    logger.info(
        f"Cleaning up binary data for {len(image_ids)} images",
        extra={"num_images": len(image_ids)},
    )

    # Create synchronous engine for Celery tasks
    sync_engine = create_engine(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SyncSession()

    try:
        # Update all images in batch - set image_data to NULL
        from sqlalchemy import update

        stmt = update(S3Image).where(S3Image.image_id.in_(image_ids)).values(image_data=None)

        result = session.execute(stmt)
        session.commit()

        logger.info(
            f"Successfully cleaned up binary data for {result.rowcount} images",
            extra={"num_images": result.rowcount, "image_ids": image_ids[:5]},  # Log first 5 IDs
        )

    except Exception as e:
        session.rollback()
        logger.error(
            f"Failed to cleanup binary data: {e}",
            extra={"error": str(e), "num_images": len(image_ids)},
            exc_info=True,
        )
        # Don't raise - cleanup failure shouldn't block ML workflow
    finally:
        session.close()
        sync_engine.dispose()


def _generate_visualization(
    session_id: int,
    detections: list[dict[str, Any]],
    estimations: list[dict[str, Any]],
) -> str | None:
    """Generate visualization image with detection circles and estimation polygons.

    This function creates a visualization overlay on the original image showing:
    1. Detection circles (green, transparent)
    2. Estimation polygons (blue, transparent with gaussian blur)
    3. Text legend (detected count, estimated count, confidence)
    4. Compressed as AVIF format (50% size reduction)
    5. Saved to /tmp/processed/ for S3 upload

    Args:
        session_id: PhotoProcessingSession database ID
        detections: List of detection dicts with center_x_px, center_y_px, width_px, height_px, confidence
        estimations: List of estimation dicts with vegetation_polygon, estimated_count

    Returns:
        Path to generated visualization file in /tmp/processed/, or None if failed

    Raises:
        No exceptions - logs warnings and returns None on failure

    Business Flow (from Mermaid diagram lines 393-401):
        1. CALLBACK_LOAD_IMAGE: Load original image from session
        2. CALLBACK_GET_DETS: Already have detections in memory
        3. CALLBACK_GET_ESTS: Already have estimations in memory
        4. CALLBACK_DRAW_DETS: Draw transparent circles for detections
        5. CALLBACK_DRAW_ESTS: Draw transparent polygons for estimations
        6. CALLBACK_LEGEND: Add text legend (detected, estimated, confidence)
        7. CALLBACK_COMPRESS: Compress as AVIF format
        8. CALLBACK_SAVE_TEMP: Save to /tmp/processed/
    """
    import cv2
    import numpy as np
    from PIL import Image
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings
    from app.models.photo_processing_session import PhotoProcessingSession as SessionModel

    logger.info(
        f"[Session {session_id}] Starting visualization generation",
        extra={
            "session_id": session_id,
            "num_detections": len(detections),
            "num_estimations": len(estimations),
        },
    )

    try:
        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 1: Get original image path from PhotoProcessingSession
        # ═══════════════════════════════════════════════════════════════════════════
        sync_engine = create_engine(
            settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
        db_session = SyncSession()

        try:
            session_record = db_session.query(SessionModel).filter_by(id=session_id).first()
            if not session_record or not session_record.original_image:
                logger.warning(
                    f"[Session {session_id}] No original image found - skipping visualization",
                    extra={"session_id": session_id},
                )
                return None

            # Get S3 key from original_image relationship
            s3_key = session_record.original_image.s3_key_original
            s3_bucket = session_record.original_image.s3_bucket

            logger.info(
                f"[Session {session_id}] Found original image: {s3_key}",
                extra={"session_id": session_id, "s3_key": s3_key, "bucket": s3_bucket},
            )

        finally:
            db_session.close()
            sync_engine.dispose()

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 2: Get original image using 3-tier cache (PROBLEM 3 FIX)
        # Priority: PostgreSQL → /tmp → S3 (same pattern as ml_child_task lines 370-452)
        # ═══════════════════════════════════════════════════════════════════════════
        temp_original_path = f"/tmp/session_{session_id}_original.jpg"

        # PRIORITY 1: Check PostgreSQL for cached binary data (fastest)
        logger.info(
            f"[Session {session_id}] Checking PostgreSQL for cached image data",
            extra={"session_id": session_id, "image_id": str(session_record.original_image_id)},
        )

        from app.models.s3_image import S3Image

        s3_image = (
            db_session.query(S3Image)
            .filter(S3Image.image_id == session_record.original_image_id)
            .first()
        )

        if s3_image and s3_image.image_data:
            # Found binary data in PostgreSQL - write to /tmp
            logger.info(
                f"[Session {session_id}] Found image data in PostgreSQL ({len(s3_image.image_data)} bytes), writing to {temp_original_path}",
                extra={"session_id": session_id, "size_bytes": len(s3_image.image_data)},
            )

            with open(temp_original_path, "wb") as f:
                f.write(s3_image.image_data)

            logger.info(
                f"[Session {session_id}] Successfully loaded image from PostgreSQL cache",
                extra={"session_id": session_id, "temp_path": temp_original_path},
            )

        # PRIORITY 2: Check /tmp local cache (retry optimization)
        elif Path(temp_original_path).exists():
            # File already exists in /tmp from previous run
            logger.info(
                f"[Session {session_id}] Using cached file from /tmp: {temp_original_path}",
                extra={"session_id": session_id, "temp_path": temp_original_path},
            )

        # PRIORITY 3: Download from S3 (fallback)
        else:
            logger.info(
                f"[Session {session_id}] Image not found in PostgreSQL or /tmp, downloading from S3",
                extra={"session_id": session_id, "s3_key": s3_key, "temp_path": temp_original_path},
            )

            import boto3

            s3_client = boto3.client("s3")

            try:
                s3_client.download_file(s3_bucket, s3_key, temp_original_path)
                logger.info(
                    f"[Session {session_id}] Successfully downloaded image from S3 to {temp_original_path}",
                    extra={
                        "session_id": session_id,
                        "s3_key": s3_key,
                        "temp_path": temp_original_path,
                    },
                )
            except Exception as e:
                logger.warning(
                    f"[Session {session_id}] Failed to download original image from S3: {e}",
                    extra={"session_id": session_id, "s3_key": s3_key, "error": str(e)},
                )
                return None

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 3: Load image with OpenCV
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(
            f"[Session {session_id}] Loading image with OpenCV",
            extra={"session_id": session_id, "path": temp_original_path},
        )

        image = cv2.imread(temp_original_path)
        if image is None:
            logger.warning(
                f"[Session {session_id}] Failed to load image with OpenCV",
                extra={"session_id": session_id, "path": temp_original_path},
            )
            return None

        img_height, img_width = image.shape[:2]
        logger.info(
            f"[Session {session_id}] Image loaded: {img_width}x{img_height}",
            extra={"session_id": session_id, "width": img_width, "height": img_height},
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 4: Draw detection circles (cyan, simple, professional)
        # ═══════════════════════════════════════════════════════════════════════════
        if detections:
            logger.info(
                f"[Session {session_id}] Drawing {len(detections)} detection circles",
                extra={"session_id": session_id, "num_detections": len(detections)},
            )

            overlay = image.copy()
            color_cyan = (255, 255, 0)  # BGR format (cyan) - professional and visible

            for det in detections:
                center_x = int(det["center_x_px"])
                center_y = int(det["center_y_px"])
                width = int(det["width_px"])
                height = int(det["height_px"])

                # Calculate radius: 75% of the detection box size
                # Use min(width, height) to ensure circle fits within detection
                radius = int(min(width, height) * 0.75 / 2)

                # Draw filled circle on overlay (centered at detection center)
                cv2.circle(overlay, (center_x, center_y), radius, color_cyan, -1)

            # Blend overlay with original (alpha=0.3 for semi-transparency)
            image = cv2.addWeighted(image, 0.7, overlay, 0.3, 0)

            logger.info(
                f"[Session {session_id}] Detection circles drawn successfully",
                extra={"session_id": session_id},
            )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 5: Draw estimation polygons (blue, transparent with blur)
        # ═══════════════════════════════════════════════════════════════════════════
        if estimations:
            logger.info(
                f"[Session {session_id}] Drawing {len(estimations)} estimation polygons",
                extra={"session_id": session_id, "num_estimations": len(estimations)},
            )

            overlay = image.copy()
            color_blue = (255, 0, 0)  # BGR format (blue)

            for est in estimations:
                vegetation_polygon = est.get("vegetation_polygon", {})
                if not vegetation_polygon or "coordinates" not in vegetation_polygon:
                    continue

                # Extract coordinates from JSONB polygon
                coords = vegetation_polygon["coordinates"]
                if not coords:
                    continue

                # Convert to numpy array for cv2.fillPoly
                pts = np.array(coords, dtype=np.int32)
                pts = pts.reshape((-1, 1, 2))

                # Draw filled polygon on overlay
                cv2.fillPoly(overlay, [pts], color_blue)

            # Apply gaussian blur to overlay for softer appearance
            overlay_blurred = cv2.GaussianBlur(overlay, (9, 9), 0)

            # Blend blurred overlay with original (alpha=0.2 for estimations)
            image = cv2.addWeighted(image, 0.8, overlay_blurred, 0.2, 0)

            logger.info(
                f"[Session {session_id}] Estimation polygons drawn successfully",
                extra={"session_id": session_id},
            )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 6: Add text legend (top-left corner)
        # ═══════════════════════════════════════════════════════════════════════════
        total_detected = len(detections)
        total_estimated = sum(est.get("estimated_count", 0) for est in estimations)
        avg_confidence = (
            sum(det.get("confidence", 0.0) for det in detections) / len(detections)
            if detections
            else 0.0
        )

        logger.info(
            f"[Session {session_id}] Adding legend: {total_detected} detected, {total_estimated} estimated, {avg_confidence:.0%} confidence",
            extra={
                "session_id": session_id,
                "total_detected": total_detected,
                "total_estimated": total_estimated,
                "avg_confidence": avg_confidence,
            },
        )

        # Text parameters
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        font_thickness = 2
        color_white = (255, 255, 255)
        color_black = (0, 0, 0)

        # Draw background rectangle for text (black with transparency)
        cv2.rectangle(image, (5, 5), (400, 100), color_black, -1)

        # Draw text lines
        cv2.putText(
            image,
            f"Detected: {total_detected}",
            (10, 30),
            font,
            font_scale,
            color_white,
            font_thickness,
        )
        cv2.putText(
            image,
            f"Estimated: {total_estimated}",
            (10, 60),
            font,
            font_scale,
            color_white,
            font_thickness,
        )
        cv2.putText(
            image,
            f"Confidence: {avg_confidence:.0%}",
            (10, 90),
            font,
            font_scale,
            color_white,
            font_thickness,
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 7: Save to temp path and compress as AVIF
        # ═══════════════════════════════════════════════════════════════════════════
        output_dir = Path("/tmp/processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"session_{session_id}_viz.avif"

        logger.info(
            f"[Session {session_id}] Compressing visualization as AVIF",
            extra={"session_id": session_id, "output_path": str(output_path)},
        )

        # Convert BGR to RGB for PIL
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(image_rgb)

        # Save as AVIF with compression (fallback to WebP if AVIF not supported)
        try:
            image_pil.save(str(output_path), "AVIF", quality=85, speed=4)
            logger.info(
                f"[Session {session_id}] Visualization saved as AVIF",
                extra={"session_id": session_id, "output_path": str(output_path)},
            )
        except Exception as e:
            # Fallback to WebP if AVIF not supported
            logger.warning(
                f"[Session {session_id}] AVIF not supported, falling back to WebP: {e}",
                extra={"session_id": session_id, "error": str(e)},
            )
            output_path = output_dir / f"session_{session_id}_viz.webp"
            image_pil.save(str(output_path), "WEBP", quality=85)
            logger.info(
                f"[Session {session_id}] Visualization saved as WebP",
                extra={"session_id": session_id, "output_path": str(output_path)},
            )

        # Cleanup temp original file
        if Path(temp_original_path).exists():
            os.remove(temp_original_path)

        logger.info(
            f"[Session {session_id}] Visualization generation completed successfully",
            extra={"session_id": session_id, "output_path": str(output_path)},
        )

        return str(output_path)

    except Exception as e:
        logger.error(
            f"[Session {session_id}] Visualization generation failed: {e}",
            extra={"session_id": session_id, "error": str(e)},
            exc_info=True,
        )
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Helper: Create StorageBins from ML Segments
# ═══════════════════════════════════════════════════════════════════════════


def _create_storage_bins(
    db_session: Any,
    session_id: int,
    storage_location_id: int,
    segments: list[dict[str, Any]],
) -> list[int]:
    """Create StorageBins from ML segmentation results.

    This function creates physical storage bins (containers) from ML segmentation
    output BEFORE creating stock batches. Each segment becomes a StorageBin with
    position_metadata containing the ML output.

    Args:
        db_session: Synchronous SQLAlchemy session
        session_id: PhotoProcessingSession ID
        storage_location_id: Parent storage location ID
        segments: List of segment dicts with container_type, bbox, polygon, confidence

    Returns:
        list[int]: List of created StorageBin IDs

    Raises:
        Exception: If StorageBinType lookup or StorageBin creation fails

    Business Logic:
        1. For each unique container_type, get or create StorageBinType
        2. For each segment, create a StorageBin with:
           - Unique code: ML-{session_id}-{container_type}-{index}-{timestamp}
           - position_metadata: Full ML output (bbox, polygon, confidence)
           - storage_bin_type_id: Mapped from container_type
        3. Return list of created bin IDs for StockBatch creation

    Example:
        >>> segments = [
        ...     {"container_type": "segment", "bbox": [0.1, 0.2, 0.3, 0.4], "confidence": 0.92, ...},
        ...     {"container_type": "box", "bbox": [0.5, 0.6, 0.7, 0.8], "confidence": 0.88, ...},
        ... ]
        >>> bin_ids = _create_storage_bins(db_session, 123, 1, segments)
        >>> # Returns: [1, 2] (two new StorageBin IDs)
    """
    from app.models.storage_bin import StorageBin
    from app.models.storage_bin_type import StorageBinType
    from app.models.storage_location import StorageLocation

    if not segments:
        logger.warning(
            f"[Session {session_id}] No segments provided, skipping StorageBin creation",
            extra={"session_id": session_id},
        )
        return []

    logger.info(
        f"[Session {session_id}] Creating {len(segments)} StorageBins from ML segments",
        extra={
            "session_id": session_id,
            "num_segments": len(segments),
            "storage_location_id": storage_location_id,
        },
    )

    # Validate storage_location exists
    storage_location = (
        db_session.query(StorageLocation).filter_by(location_id=storage_location_id).first()
    )
    if not storage_location:
        raise ValueError(f"StorageLocation {storage_location_id} not found")

    # Get parent codes for StorageBin.code construction
    # Format: WAREHOUSE-AREA-LOCATION-BIN (4 parts)
    location_code = storage_location.code  # e.g., "INV01-NORTH-A1"

    created_bin_ids: list[int] = []
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    for idx, segment in enumerate(segments, start=1):
        container_type = segment.get("container_type", "segment")
        confidence = segment.get("confidence", 0.0)
        bbox = segment.get("bbox", [])
        polygon = segment.get("polygon", [])
        area_pixels = segment.get("area_pixels", 0)  # Fixed: was mask_area

        # Map container_type to BinCategoryEnum
        bin_category = _map_container_type_to_bin_category(container_type)

        # Get or create StorageBinType
        bin_type = db_session.query(StorageBinType).filter_by(category=bin_category).first()

        if not bin_type:
            # Create default StorageBinType if not exists
            bin_type_code = f"ML_{bin_category.upper()}_DEFAULT"
            bin_type = StorageBinType(
                code=bin_type_code,
                name=f"ML-Detected {bin_category.capitalize()}",
                category=bin_category,
                is_grid=False,
                description=f"Auto-generated bin type for ML-detected {bin_category} containers",
            )
            db_session.add(bin_type)
            db_session.flush()
            db_session.refresh(bin_type)

            logger.info(
                f"[Session {session_id}] Created new StorageBinType: {bin_type_code} (category={bin_category})",
                extra={
                    "session_id": session_id,
                    "bin_type_id": bin_type.bin_type_id,
                    "category": bin_category,
                },
            )

        # Create unique StorageBin code
        # Format: WAREHOUSE-AREA-LOCATION-BIN (e.g., "INV01-NORTH-A1-ML-SEG001-20251024143000")
        bin_code = f"{location_code}-ML-{container_type.upper()}{idx:03d}-{timestamp}"

        # Create position_metadata JSONB
        position_metadata = {
            "segmentation_mask": polygon,  # Polygon vertices (normalized coordinates)
            "bbox": {
                "x1": bbox[0] if len(bbox) >= 4 else 0.0,
                "y1": bbox[1] if len(bbox) >= 4 else 0.0,
                "x2": bbox[2] if len(bbox) >= 4 else 0.0,
                "y2": bbox[3] if len(bbox) >= 4 else 0.0,
            },
            "confidence": confidence,
            "ml_model_version": "yolov11n-seg-v1.0.0",
            "detected_at": datetime.utcnow().isoformat(),
            "container_type": container_type,
            "area_pixels": area_pixels,  # Fixed: was mask_area
            "session_id": session_id,
        }

        # Create StorageBin
        storage_bin = StorageBin(
            storage_location_id=storage_location_id,
            storage_bin_type_id=bin_type.bin_type_id,
            code=bin_code,
            label=f"ML {container_type.capitalize()} #{idx}",
            description=f"ML-detected {container_type} from session {session_id} (confidence: {confidence:.3f})",
            position_metadata=position_metadata,
            status="active",
        )
        db_session.add(storage_bin)
        db_session.flush()
        db_session.refresh(storage_bin)

        created_bin_ids.append(storage_bin.bin_id)

        logger.debug(
            f"[Session {session_id}] Created StorageBin: bin_id={storage_bin.bin_id}, code={bin_code}, "
            f"type={container_type}, confidence={confidence:.3f}",
            extra={
                "session_id": session_id,
                "bin_id": storage_bin.bin_id,
                "bin_code": bin_code,
                "container_type": container_type,
                "confidence": confidence,
            },
        )

    logger.info(
        f"[Session {session_id}] Successfully created {len(created_bin_ids)} StorageBins",
        extra={
            "session_id": session_id,
            "num_bins_created": len(created_bin_ids),
            "bin_ids": created_bin_ids,
        },
    )

    return created_bin_ids


def _persist_ml_results(
    session_id: int,
    detections: list[dict[str, Any]],
    estimations: list[dict[str, Any]],
    segments: list[dict[str, Any]] | None = None,
    storage_location_id: int | None = None,
) -> None:
    """Persist detections and estimations to database (called by callback).

    This function creates StorageBins from ML segments, then creates a StockBatch
    and StockMovement, and bulk inserts all detections and estimations.

    Args:
        session_id: PhotoProcessingSession database ID
        detections: List of detection dicts from ML pipeline
        estimations: List of estimation dicts from ML pipeline
        segments: List of segment dicts with container_type, bbox, polygon (optional)
        storage_location_id: Storage location ID for StorageBin creation (optional)

    Raises:
        ValueError: If storage_location_id is NULL and cannot be retrieved
        Exception: If database operations fail

    Business Flow:
        0. Validate storage_location_id (from param or PhotoProcessingSession)
        0b. Create StorageBins from ML segments (if provided)
        1. Create StockBatch (using first created bin_id or default=1)
        2. Create StockMovement (movement_type=foto, source_type=ia)
        3. Get or create Classification (default: product_id=1)
        4. Transform detections to match Detection model schema
        5. Transform estimations to match Estimation model schema
        6. Bulk insert detections with FKs (session_id, stock_movement_id, classification_id)
        7. Bulk insert estimations with FKs (session_id, stock_movement_id, classification_id)
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings

    logger.info(
        f"Persisting ML results: {len(detections)} detections, {len(estimations)} estimations",
        extra={
            "session_id": session_id,
            "num_detections": len(detections),
            "num_estimations": len(estimations),
        },
    )

    # Create synchronous engine for Celery tasks
    sync_engine = create_engine(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"),
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    SyncSession = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    db_session = SyncSession()

    try:
        from app.models.classification import Classification
        from app.models.detection import Detection
        from app.models.estimation import Estimation
        from app.models.photo_processing_session import PhotoProcessingSession
        from app.models.stock_batch import StockBatch
        from app.models.stock_movement import StockMovement
        from app.models.storage_location_config import StorageLocationConfig

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 0: Validate storage_location_id and create StorageBins from segments
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(
            f"[Session {session_id}] Step 0: Validating storage_location_id and creating StorageBins",
            extra={"session_id": session_id, "storage_location_id": storage_location_id},
        )

        # If storage_location_id not provided, try to get from PhotoProcessingSession
        if storage_location_id is None:
            session_record = (
                db_session.query(PhotoProcessingSession).filter_by(id=session_id).first()
            )
            if session_record and session_record.storage_location_id:
                storage_location_id = session_record.storage_location_id
                logger.info(
                    f"[Session {session_id}] Retrieved storage_location_id from session: {storage_location_id}",
                    extra={"session_id": session_id, "storage_location_id": storage_location_id},
                )
            else:
                raise ValueError(
                    f"storage_location_id is NULL for session {session_id}. "
                    "Cannot create StorageBins without location context."
                )

        # Create StorageBins from ML segments
        created_bin_ids: list[int] = []
        if segments and len(segments) > 0:
            try:
                created_bin_ids = _create_storage_bins(
                    db_session=db_session,
                    session_id=session_id,
                    storage_location_id=storage_location_id,
                    segments=segments,
                )
                logger.info(
                    f"[Session {session_id}] Created {len(created_bin_ids)} StorageBins from segments",
                    extra={
                        "session_id": session_id,
                        "num_bins": len(created_bin_ids),
                        "bin_ids": created_bin_ids,
                    },
                )
            except Exception as e:
                logger.error(
                    f"[Session {session_id}] Failed to create StorageBins: {e}",
                    extra={"session_id": session_id, "error": str(e)},
                    exc_info=True,
                )
                raise ValueError(f"Cannot create StorageBins for session {session_id}: {str(e)}") from e
        else:
            logger.warning(
                f"[Session {session_id}] No segments provided, cannot create StorageBins. "
                "Using default bin_id=1 for StockBatch.",
                extra={"session_id": session_id},
            )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 0b: Look up StorageLocationConfig for product and packaging info
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(
            f"[Session {session_id}] Step 0b: Looking up StorageLocationConfig",
            extra={"session_id": session_id, "storage_location_id": storage_location_id},
        )

        # Try to get configuration for this storage location
        config = (
            db_session.query(StorageLocationConfig)
            .filter_by(storage_location_id=storage_location_id, active=True)
            .first()
        )

        # Determine product_id, product_state_id, and packaging_catalog_id
        if config:
            product_id = config.product_id
            product_state_id = config.expected_product_state_id
            packaging_catalog_id = config.packaging_catalog_id  # May be None
            logger.info(
                f"[Session {session_id}] Using StorageLocationConfig: product_id={product_id}, "
                f"product_state_id={product_state_id}, packaging_catalog_id={packaging_catalog_id}",
                extra={
                    "session_id": session_id,
                    "product_id": product_id,
                    "product_state_id": product_state_id,
                    "packaging_catalog_id": packaging_catalog_id,
                },
            )
        else:
            # Fallback: use first available product and a reasonable state (SEEDLING=3)
            product_id = 1  # We know ID 1 exists (Mammillaria)
            product_state_id = 3  # SEEDLING is more appropriate than SEED for ML detection
            packaging_catalog_id = None  # No packaging data available
            logger.warning(
                f"[Session {session_id}] No StorageLocationConfig found for storage_location_id={storage_location_id}, "
                f"using fallback values: product_id={product_id}, product_state_id={product_state_id}, "
                f"packaging_catalog_id={packaging_catalog_id}",
                extra={
                    "session_id": session_id,
                    "storage_location_id": storage_location_id,
                    "product_id": product_id,
                    "product_state_id": product_state_id,
                    "packaging_catalog_id": packaging_catalog_id,
                },
            )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 1: Create StockBatch for this processing session
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(
            f"[Session {session_id}] Step 1: Creating StockBatch for ML processing",
            extra={"session_id": session_id},
        )

        batch_code = f"ML-SESSION-{session_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Validate that StorageBins were created successfully
        if not created_bin_ids:
            raise ValueError(
                f"[Session {session_id}] No StorageBins created. "
                f"Cannot create StockBatch without valid storage bin. "
                f"Check that storage_location_id={storage_location_id} exists and segments are valid."
            )
        current_storage_bin_id = created_bin_ids[0]

        stock_batch = StockBatch(
            batch_code=batch_code,
            current_storage_bin_id=current_storage_bin_id,
            product_id=product_id,  # From config or fallback
            product_state_id=product_state_id,  # From config or fallback (SEEDLING=3)
            quantity_initial=len(detections)
            + sum(est.get("estimated_count", 0) for est in estimations),
            quantity_current=len(detections)
            + sum(est.get("estimated_count", 0) for est in estimations),
            quantity_empty_containers=0,
            has_packaging=bool(packaging_catalog_id),  # True if packaging_catalog_id is not None
            packaging_catalog_id=packaging_catalog_id,  # None if no packaging data
        )
        db_session.add(stock_batch)
        db_session.flush()  # Get batch_id
        db_session.refresh(stock_batch)

        logger.info(
            f"[Session {session_id}] Created StockBatch: batch_id={stock_batch.id}, batch_code={batch_code}, "
            f"current_storage_bin_id={current_storage_bin_id}, product_id={product_id}, "
            f"product_state_id={product_state_id}, has_packaging={stock_batch.has_packaging}",
            extra={
                "session_id": session_id,
                "batch_id": stock_batch.id,
                "batch_code": batch_code,
                "current_storage_bin_id": current_storage_bin_id,
                "product_id": product_id,
                "product_state_id": product_state_id,
                "packaging_catalog_id": packaging_catalog_id,
                "has_packaging": stock_batch.has_packaging,
            },
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 2: Create StockMovement for this ML processing
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(
            f"[Session {session_id}] Step 2: Creating StockMovement for ML processing",
            extra={"session_id": session_id},
        )

        total_quantity = len(detections) + sum(est.get("estimated_count", 0) for est in estimations)

        stock_movement = StockMovement(
            batch_id=stock_batch.id,
            movement_type="foto",
            source_type="ia",
            is_inbound=True,
            quantity=total_quantity,
            processing_session_id=session_id,
            user_id=1,  # Default ML user (TODO: Get from configuration)
            reason_description=f"ML photo processing session {session_id}",
        )
        db_session.add(stock_movement)
        db_session.flush()  # Get stock_movement_id
        db_session.refresh(stock_movement)

        logger.info(
            f"[Session {session_id}] Created StockMovement: id={stock_movement.id}, quantity={total_quantity}",
            extra={
                "session_id": session_id,
                "stock_movement_id": stock_movement.id,
                "quantity": total_quantity,
            },
        )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 3: Get or create Classification
        # ═══════════════════════════════════════════════════════════════════════════
        logger.info(
            f"[Session {session_id}] Step 3: Getting or creating Classification with product_id={product_id}, "
            f"packaging_catalog_id={packaging_catalog_id}",
            extra={
                "session_id": session_id,
                "product_id": product_id,
                "packaging_catalog_id": packaging_catalog_id,
            },
        )

        # Query for existing classification based on product_id and packaging_catalog_id
        # Handle both NULL and non-NULL packaging_catalog_id cases
        if packaging_catalog_id is not None:
            classification = (
                db_session.query(Classification)
                .filter(
                    Classification.product_id == product_id,
                    Classification.packaging_catalog_id == packaging_catalog_id,
                )
                .first()
            )
        else:
            classification = (
                db_session.query(Classification)
                .filter(
                    Classification.product_id == product_id,
                    Classification.packaging_catalog_id.is_(None),
                )
                .first()
            )

        if not classification:
            # Create new classification
            classification = Classification(
                product_id=product_id,
                packaging_catalog_id=packaging_catalog_id,  # Can be None
                product_conf=70,  # Default confidence for ML pipeline
                packaging_conf=70
                if packaging_catalog_id
                else None,  # No packaging_conf if no packaging
                model_version="yolov11n-seg-v1.0.0",
                name=f"ML Classification - Product {product_id}"
                + (f" - Packaging {packaging_catalog_id}" if packaging_catalog_id else ""),
                description=f"Auto-generated classification for ML pipeline (product_id={product_id}, packaging_catalog_id={packaging_catalog_id})",
            )
            db_session.add(classification)
            db_session.flush()
            db_session.refresh(classification)

            logger.info(
                f"[Session {session_id}] Created new Classification: classification_id={classification.classification_id}, "
                f"product_id={product_id}, packaging_catalog_id={packaging_catalog_id}",
                extra={
                    "session_id": session_id,
                    "classification_id": classification.classification_id,
                    "product_id": product_id,
                    "packaging_catalog_id": packaging_catalog_id,
                },
            )
        else:
            logger.info(
                f"[Session {session_id}] Using existing Classification: classification_id={classification.classification_id}, "
                f"product_id={product_id}, packaging_catalog_id={packaging_catalog_id}",
                extra={
                    "session_id": session_id,
                    "classification_id": classification.classification_id,
                    "product_id": product_id,
                    "packaging_catalog_id": packaging_catalog_id,
                },
            )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 4: Transform and bulk insert Detections
        # ═══════════════════════════════════════════════════════════════════════════
        if detections:
            logger.info(
                f"[Session {session_id}] Step 4: Bulk inserting {len(detections)} detections",
                extra={"session_id": session_id, "num_detections": len(detections)},
            )

            detection_records = []
            for det in detections:
                # Calculate bbox_coordinates from center + width/height
                center_x = float(det["center_x_px"])
                center_y = float(det["center_y_px"])
                width = int(det["width_px"])
                height = int(det["height_px"])

                x1 = center_x - (width / 2)
                y1 = center_y - (height / 2)
                x2 = center_x + (width / 2)
                y2 = center_y + (height / 2)

                detection_record = Detection(
                    session_id=session_id,
                    stock_movement_id=stock_movement.id,
                    classification_id=classification.classification_id,
                    center_x_px=center_x,
                    center_y_px=center_y,
                    width_px=width,
                    height_px=height,
                    bbox_coordinates={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    detection_confidence=float(det.get("confidence", 0.0)),
                    is_empty_container=False,
                    is_alive=True,
                )
                detection_records.append(detection_record)

            # Bulk insert detections
            db_session.bulk_save_objects(detection_records)
            logger.info(
                f"[Session {session_id}] Successfully bulk inserted {len(detection_records)} detections",
                extra={"session_id": session_id, "num_detections": len(detection_records)},
            )
        else:
            logger.info(
                f"[Session {session_id}] No detections to insert",
                extra={"session_id": session_id},
            )

        # ═══════════════════════════════════════════════════════════════════════════
        # STEP 5: Transform and bulk insert Estimations
        # ═══════════════════════════════════════════════════════════════════════════
        if estimations:
            logger.info(
                f"[Session {session_id}] Step 5: Bulk inserting {len(estimations)} estimations",
                extra={"session_id": session_id, "num_estimations": len(estimations)},
            )

            estimation_records = []
            for est in estimations:
                # Create vegetation_polygon from band coordinates
                band_y_start = est.get("band_y_start", 0)
                band_y_end = est.get("band_y_end", 0)

                # Simplified polygon (full-width band)
                # TODO: In production, use actual vegetation mask polygon
                vegetation_polygon = {
                    "type": "Polygon",
                    "coordinates": [
                        [0, band_y_start],
                        [4000, band_y_start],  # Assume 4000px wide image
                        [4000, band_y_end],
                        [0, band_y_end],
                        [0, band_y_start],
                    ],
                }

                estimation_record = Estimation(
                    session_id=session_id,
                    stock_movement_id=stock_movement.id,
                    classification_id=classification.classification_id,
                    vegetation_polygon=vegetation_polygon,
                    detected_area_cm2=float(est.get("processed_area_px", 0.0))
                    / 100.0,  # Convert px to cm²
                    estimated_count=int(est.get("estimated_count", 0)),
                    calculation_method="band_estimation",
                    estimation_confidence=0.70,  # Default confidence for band estimation
                    used_density_parameters=False,  # Not using density params (using band method)
                )
                estimation_records.append(estimation_record)

            # Bulk insert estimations
            db_session.bulk_save_objects(estimation_records)
            logger.info(
                f"[Session {session_id}] Successfully bulk inserted {len(estimation_records)} estimations",
                extra={"session_id": session_id, "num_estimations": len(estimation_records)},
            )
        else:
            logger.info(
                f"[Session {session_id}] No estimations to insert",
                extra={"session_id": session_id},
            )

        # Commit transaction
        db_session.commit()
        logger.info(
            f"[Session {session_id}] Successfully committed all ML results to database",
            extra={
                "session_id": session_id,
                "stock_movement_id": stock_movement.id,
                "batch_id": stock_batch.id,
                "classification_id": classification.classification_id,
                "num_detections": len(detections),
                "num_estimations": len(estimations),
            },
        )

    except Exception as e:
        db_session.rollback()
        logger.error(
            f"Failed to persist ML results for session {session_id}: {e}",
            extra={"session_id": session_id, "error": str(e)},
            exc_info=True,
        )
        raise
    finally:
        db_session.close()
        sync_engine.dispose()
