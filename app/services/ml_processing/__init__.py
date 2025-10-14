"""
ML Processing Services.

This package contains machine learning infrastructure and services
for YOLO model management, inference, and caching.
"""

from app.services.ml_processing.model_cache import ModelCache

__all__ = ["ModelCache"]
