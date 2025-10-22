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

from datetime import datetime
from pathlib import Path
from typing import Any

from celery import chord

from app.celery_app import app
from app.core.exceptions import (
    CircuitBreakerException,
    ValidationException,
)
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.repositories.photo_processing_session_repository import (
    PhotoProcessingSessionRepository,
)
from app.services.ml_processing.band_estimation_service import BandEstimationService
from app.services.ml_processing.pipeline_coordinator import (
    MLPipelineCoordinator,
    PipelineResult,
)
from app.services.ml_processing.sahi_detection_service import SAHIDetectionService
from app.services.ml_processing.segmentation_service import SegmentationService
from app.services.photo.photo_processing_session_service import (
    PhotoProcessingSessionService,
)

logger = get_logger(__name__)

# Circuit Breaker Configuration (CEL008)
CIRCUIT_BREAKER_THRESHOLD = 5  # Open circuit after 5 consecutive failures
CIRCUIT_BREAKER_TIMEOUT = 300  # 5 minutes cooldown before retry
circuit_breaker_state: dict[str, dict[str, Any]] = {
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

    if circuit_breaker_state["state"] == "closed":
        # Normal operation
        return

    if circuit_breaker_state["state"] == "open":
        # Check if cooldown period has passed
        if circuit_breaker_state["last_failure_time"] is not None:
            elapsed = (
                datetime.utcnow() - circuit_breaker_state["last_failure_time"]
            ).total_seconds()
            if elapsed >= CIRCUIT_BREAKER_TIMEOUT:
                # Transition to half_open (test recovery)
                circuit_breaker_state["state"] = "half_open"
                logger.info("Circuit breaker transitioning to HALF_OPEN (testing recovery)")
                return

        # Circuit still open
        raise CircuitBreakerException(
            reason=f"Circuit breaker OPEN due to {circuit_breaker_state['failures']} failures. "
            f"Retry after cooldown period ({CIRCUIT_BREAKER_TIMEOUT}s)."
        )

    if circuit_breaker_state["state"] == "half_open":
        # Allow request to test recovery
        logger.info("Circuit breaker HALF_OPEN: Allowing test request")
        return


def record_circuit_breaker_success() -> None:
    """Record successful task execution (reset circuit breaker)."""
    global circuit_breaker_state

    if circuit_breaker_state["state"] == "half_open":
        # Recovery successful, close circuit
        circuit_breaker_state["state"] = "closed"
        circuit_breaker_state["failures"] = 0
        circuit_breaker_state["last_failure_time"] = None
        logger.info("Circuit breaker CLOSED (recovery successful)")
    elif circuit_breaker_state["state"] == "closed":
        # Reset failure counter on success
        circuit_breaker_state["failures"] = 0


def record_circuit_breaker_failure() -> None:
    """Record task failure (increment circuit breaker counter)."""
    global circuit_breaker_state

    circuit_breaker_state["failures"] += 1
    circuit_breaker_state["last_failure_time"] = datetime.utcnow()

    if circuit_breaker_state["failures"] >= CIRCUIT_BREAKER_THRESHOLD:
        # Open circuit
        circuit_breaker_state["state"] = "open"
        logger.error(
            f"Circuit breaker OPENED after {circuit_breaker_state['failures']} failures. "
            f"Cooldown: {CIRCUIT_BREAKER_TIMEOUT}s"
        )
    else:
        logger.warning(
            f"Circuit breaker failure recorded: {circuit_breaker_state['failures']}/{CIRCUIT_BREAKER_THRESHOLD}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# CEL005: ML Parent Task (Chord Orchestration)
# ═══════════════════════════════════════════════════════════════════════════


@app.task(bind=True, queue="cpu_queue", max_retries=2)
def ml_parent_task(
    self,
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
        session_id: PhotoProcessingSession database ID
        image_data: List of image metadata dicts with keys:
            - image_id (int): S3Image record ID
            - image_path (str): Local/S3 path to image file
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


@app.task(bind=True, queue="gpu_queue", max_retries=3)
def ml_child_task(
    self,
    session_id: int,
    image_id: int,
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
        session_id: PhotoProcessingSession database ID
        image_id: S3Image record ID
        image_path: Path to image file (local or S3)
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
        # Validate image exists
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

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

        result: PipelineResult = asyncio.run(
            coordinator.process_complete_pipeline(
                session_id=session_id,
                image_path=image_path,
                worker_id=0,  # GPU worker 0
                conf_threshold_segment=0.30,
                conf_threshold_detect=0.25,
            )
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


@app.task(queue="cpu_queue")
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
        # NOTE: total_segments not currently used but tracked for future analytics

        # Aggregate all detections/estimations for bulk insert (future enhancement)
        all_detections = []
        all_estimations = []
        for r in valid_results:
            all_detections.extend(r.get("detections", []))
            all_estimations.extend(r.get("estimations", []))

        logger.info(
            f"ML aggregation callback: Aggregated {num_valid}/{num_total} images for session {session_id}",
            extra={
                "session_id": session_id,
                "total_detected": total_detected,
                "total_estimated": total_estimated,
                "avg_confidence": avg_confidence,
                "num_valid": num_valid,
                "num_total": num_total,
            },
        )

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
            total_empty_containers=0,  # NOTE: Empty container detection via segment analysis (future enhancement)
            avg_confidence=avg_confidence,
            category_counts={},  # NOTE: Category aggregation from detections (future enhancement)
            processed_image_id=None,  # NOTE: Visualization image generation (future enhancement, uses SAHI overlay)
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
    import asyncio

    async def _update():
        async for session in get_db_session():
            repo = PhotoProcessingSessionRepository(session)
            service = PhotoProcessingSessionService(repo)
            await service.mark_session_processing(session_id, celery_task_id)
            await session.commit()

    asyncio.run(_update())


def _mark_session_completed(
    session_id: int,
    total_detected: int,
    total_estimated: int,
    total_empty_containers: int,
    avg_confidence: float,
    category_counts: dict,
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
    import asyncio

    async def _update():
        async for session in get_db_session():
            repo = PhotoProcessingSessionRepository(session)
            service = PhotoProcessingSessionService(repo)
            await service.mark_session_completed(
                session_id=session_id,
                total_detected=total_detected,
                total_estimated=total_estimated,
                total_empty_containers=total_empty_containers,
                avg_confidence=avg_confidence,
                category_counts=category_counts,
                processed_image_id=processed_image_id,
            )
            await session.commit()

    asyncio.run(_update())


def _mark_session_failed(session_id: int, error_message: str) -> None:
    """Mark session as FAILED with error (called on errors).

    Args:
        session_id: PhotoProcessingSession database ID
        error_message: Error description
    """
    import asyncio

    async def _update():
        async for session in get_db_session():
            repo = PhotoProcessingSessionRepository(session)
            service = PhotoProcessingSessionService(repo)
            await service.mark_session_failed(session_id, error_message)
            await session.commit()

    asyncio.run(_update())
