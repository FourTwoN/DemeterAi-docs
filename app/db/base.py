"""SQLAlchemy declarative base for all database models.

This module defines the declarative base class that all SQLAlchemy models
inherit from. It provides the foundation for the ORM and is used by Alembic
for autogenerate migrations.

Usage:
    from app.db.base import Base

    class MyModel(Base):
        __tablename__ = "my_table"
        id = Column(Integer, primary_key=True)
"""

from sqlalchemy.orm import declarative_base

# Declarative base for all models
Base = declarative_base()

# Import all models here to ensure they are registered with Base.metadata
# This is required for Alembic autogenerate to detect model changes.
#
# When models are created (DB001-DB035), import them here:
# Example:
# from app.models.warehouse import Warehouse
# from app.models.storage_area import StorageArea
# from app.models.storage_location import StorageLocation
# from app.models.storage_bin import StorageBin
# ... (import all models)
#
# Note: Currently no models exist (Sprint 01 cards DB001-DB035)
