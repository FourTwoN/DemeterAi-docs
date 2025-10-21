"""Celery Tasks Package - Asynchronous Task Processing.

This package contains all Celery task definitions for DemeterAI v2.0.
Tasks are organized by domain and routed to specialized worker pools:

Task Modules:
    - ml_tasks: ML pipeline tasks (YOLO, SAHI, estimation)
        - ml_parent_task: Orchestrates child tasks via chord pattern
        - ml_child_task: Processes single image through ML pipeline
        - ml_aggregation_callback: Aggregates results from all children

Worker Topology:
    - GPU Queue (pool=solo): ML inference tasks
    - CPU Queue (pool=prefork): Aggregation, preprocessing
    - I/O Queue (pool=gevent): S3 uploads, database writes

Task Discovery:
    Celery autodiscovers tasks from this package via app.celery_app configuration.
    All task modules must be imported here for autodiscovery to work.

Example:
    >>> from app.tasks.ml_tasks import ml_parent_task
    >>> result = ml_parent_task.delay(session_id=123, image_ids=[1, 2, 3])
"""

# Import all task modules for Celery autodiscovery
from app.tasks.ml_tasks import (
    ml_aggregation_callback,
    ml_child_task,
    ml_parent_task,
)

__all__ = [
    "ml_parent_task",
    "ml_child_task",
    "ml_aggregation_callback",
]
