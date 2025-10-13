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
# Location Hierarchy Models (Sprint 01 - Database Models)
from app.models.warehouse import Warehouse  # DB001 - COMPLETE  # noqa: F401

# Future imports (Sprint 01 cards DB002-DB035):
# from app.models.storage_area import StorageArea          # DB002
# from app.models.storage_location import StorageLocation  # DB003
# from app.models.storage_bin import StorageBin            # DB004
# ... (import additional models as they are created)
