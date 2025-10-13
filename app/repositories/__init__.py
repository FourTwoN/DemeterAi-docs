"""Data access layer repositories for DemeterAI v2.0.

This package contains the Repository Pattern implementation for all database
access. All repositories inherit from AsyncRepository[T] base class.

Exports:
    AsyncRepository: Generic base repository for all models

Architecture:
    Layer: Infrastructure (Repository Pattern)
    Purpose: Abstract database access from business logic
    Pattern: Generic repository with SQLAlchemy 2.0 async API

Usage:
    ```python
    from app.repositories import AsyncRepository
    from app.models.warehouse import Warehouse

    class WarehouseRepository(AsyncRepository[Warehouse]):
        def __init__(self, session: AsyncSession):
            super().__init__(Warehouse, session)
    ```
"""

from app.repositories.base import AsyncRepository

__all__ = ["AsyncRepository"]
