"""Celery application configuration and initialization.

This module creates and configures the main Celery application instance
for DemeterAI v2.0 asynchronous task processing.

Architecture:
- Broker: Redis database 0 (task queue)
- Result Backend: Redis database 1 (task results storage)
- Serialization: JSON only (security - no code execution via pickle)
- Timezone: UTC (consistency across distributed workers)
- Task Discovery: Automatic from app.tasks module (when created)

Security Notes:
- NEVER use pickle serialization (arbitrary code execution risk)
- JSON-only serialization enforced
- Redis connection from Docker Compose network
"""

from celery import Celery
from kombu import Exchange, Queue


def create_celery_app() -> Celery:
    """Create and configure Celery application instance.

    Configuration follows 12-factor app principles:
    - Redis broker/backend URLs from docker-compose.yml
    - JSON serialization for security
    - UTC timezone for consistency
    - Task autodiscovery enabled
    - Connection retry enabled for resilience

    Returns:
        Configured Celery application instance

    Example:
        >>> from app.celery_app import app
        >>> @app.task
        ... def example_task():
        ...     return "Hello"
    """
    # Create Celery instance with Redis broker/backend
    # Broker (db 0): Task queue
    # Backend (db 1): Task result storage
    app = Celery(
        "demeterai",
        broker="redis://redis:6379/0",
        backend="redis://redis:6379/1",
    )

    # Configure Celery settings
    app.conf.update(
        # Security: JSON-only serialization (NO pickle - code execution risk)
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],  # Reject any non-JSON content
        # Timezone configuration
        timezone="UTC",
        enable_utc=True,
        # Task tracking
        task_track_started=True,  # Track when tasks start (not just completion)
        # Task autodiscovery (future: will scan app.tasks.* modules)
        # Note: app.tasks directory doesn't exist yet - will be created in CEL002+
        # CEL003: Worker Topology - Task Routing Configuration
        # Routes tasks to specialized worker pools based on workload type:
        # - ml_* tasks → gpu_queue (GPU-intensive ML inference)
        # - aggregate_* tasks → cpu_queue (CPU-bound aggregation)
        # - upload_* tasks → io_queue (I/O-bound S3/DB operations)
        task_routes={
            # GPU-intensive tasks (YOLO inference, ML processing)
            # CRITICAL: GPU workers MUST use pool=solo (ADR-005)
            "app.tasks.ml_*": {"queue": "gpu_queue"},
            # CPU-bound tasks (aggregation, image preprocessing)
            "app.tasks.aggregate_*": {"queue": "cpu_queue"},
            # I/O-bound tasks (S3 uploads, database writes, API calls)
            "app.tasks.upload_*": {"queue": "io_queue"},
            # Default queue for unspecified tasks
        },
        # Connection resilience
        broker_connection_retry_on_startup=True,  # Retry if Redis not available
        # Result expiration
        result_expires=3600,  # 1 hour TTL for task results (prevent Redis bloat)
        # Task execution limits
        task_time_limit=900,  # 15 minutes hard timeout
        task_soft_time_limit=840,  # 14 minutes soft timeout (raises exception)
        # CEL002: Redis Connection Pool Configuration
        # Broker connection pool (Redis db 0)
        broker_pool_limit=50,  # Max connections to broker (task queue)
        broker_connection_retry=True,  # Retry on connection failure
        broker_connection_max_retries=10,  # Max retry attempts before giving up
        # Result backend transport options (Redis db 1)
        result_backend_transport_options={
            "socket_connect_timeout": 5,  # 5 second connection timeout
            "socket_timeout": 5,  # 5 second socket timeout
            "retry_on_timeout": True,  # Retry on timeout
            "max_connections": 100,  # Max connections to result backend
            "health_check_interval": 30,  # Health check every 30 seconds
        },
        # Result backend retry configuration
        result_backend_retry_on_timeout=True,  # Retry result operations on timeout
        result_backend_transport_retry_on_timeout=True,  # Retry transport on timeout
        # Redis max connections (applies to both broker and backend)
        redis_max_connections=100,  # Global max Redis connections
        redis_socket_timeout=5,  # 5 second socket timeout for Redis operations
        redis_socket_connect_timeout=5,  # 5 second connect timeout
    )

    # Configure task queues for worker topology (CEL003: Worker Setup)
    # This enables routing tasks to specialized workers:
    # - gpu_queue: GPU workers (YOLO inference)
    # - cpu_queue: CPU workers (image preprocessing)
    # - io_queue: I/O workers (S3 uploads, database writes)
    # - default: General-purpose tasks
    app.conf.task_queues = (
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("gpu_queue", Exchange("gpu", type="direct"), routing_key="gpu"),
        Queue("cpu_queue", Exchange("cpu", type="direct"), routing_key="cpu"),
        Queue("io_queue", Exchange("io", type="direct"), routing_key="io"),
    )

    # Default queue for tasks without explicit routing
    app.conf.task_default_queue = "default"
    app.conf.task_default_exchange = "default"
    app.conf.task_default_routing_key = "default"

    return app


# Export singleton Celery app instance
# This is imported by:
# - Worker startup: celery -A app.celery_app worker
# - Task definitions: from app.celery_app import app
# - FastAPI integration: for checking task status
app = create_celery_app()


# CEL003: Worker Topology Configuration
# =====================================
# DemeterAI uses 3 specialized worker types for optimal resource utilization:
#
# 1. GPU Workers (pool=solo) - CRITICAL: MUST use solo to avoid CUDA context conflicts
# 2. CPU Workers (pool=prefork) - For CPU-intensive aggregation tasks
# 3. I/O Workers (pool=gevent) - For high-concurrency I/O operations
#
# Worker startup commands (production deployment):

# GPU Worker Configuration
# ------------------------
# Pool: solo (MANDATORY - prevents CUDA context conflicts in multiprocess environments)
# Concurrency: 1 (single process, GPU-exclusive)
# Queue: gpu_queue
# Use case: YOLO v11 inference, ML model processing
GPU_WORKER_CMD = (
    "celery -A app.celery_app worker "
    "--pool=solo "
    "--concurrency=1 "
    "--queues=gpu_queue "
    "--hostname=gpu@%h"
)

# CPU Worker Configuration
# ------------------------
# Pool: prefork (multi-process for CPU-bound tasks)
# Concurrency: 4 (adjust based on CPU cores)
# Queue: cpu_queue
# Use case: Aggregation, image preprocessing, statistical calculations
CPU_WORKER_CMD = (
    "celery -A app.celery_app worker "
    "--pool=prefork "
    "--concurrency=4 "
    "--queues=cpu_queue "
    "--hostname=cpu@%h"
)

# I/O Worker Configuration
# -------------------------
# Pool: gevent (async greenlets for I/O-bound tasks)
# Concurrency: 50 (high concurrency for I/O operations)
# Queue: io_queue
# Use case: S3 uploads, database writes, external API calls
IO_WORKER_CMD = (
    "celery -A app.celery_app worker "
    "--pool=gevent "
    "--concurrency=50 "
    "--queues=io_queue "
    "--hostname=io@%h"
)

# Worker Pool Types Reference
# ----------------------------
# solo: Single process (REQUIRED for GPU to prevent CUDA context conflicts)
# prefork: Multi-process (optimal for CPU-bound tasks)
# gevent: Greenlet-based async (optimal for I/O-bound tasks)
# threads: Multi-threaded (NOT recommended - GIL limitations)

# CRITICAL NOTES:
# ---------------
# 1. GPU workers MUST use pool=solo (ADR-005)
#    - CUDA cannot share GPU context across processes
#    - Using prefork/threads causes "CUDA context already in use" errors
# 2. Never run GPU workers with concurrency > 1
# 3. Adjust CPU worker concurrency based on available CPU cores
# 4. I/O worker concurrency can be high (50-200) due to async nature
