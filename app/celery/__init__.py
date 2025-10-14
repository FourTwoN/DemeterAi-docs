"""
Celery Task Base Classes.

This package contains base task classes for Celery workers,
including model singleton integration for ML tasks.
"""

from app.celery.base_tasks import ModelSingletonTask

__all__ = ["ModelSingletonTask"]
