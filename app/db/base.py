"""SQLAlchemy declarative base for all database models.

This module defines the declarative base class that all SQLAlchemy models
inherit from. It provides the foundation for the ORM and is used by Alembic
for autogenerate migrations.

IMPORTANT: This module ONLY defines the Base class. Model imports are handled
in alembic/env.py to avoid circular dependencies.

Usage:
    from app.db.base import Base

    class MyModel(Base):
        __tablename__ = "my_table"
        id = Column(Integer, primary_key=True)
"""

from sqlalchemy.orm import declarative_base

# Declarative base for all models
Base = declarative_base()

# NOTE: Model imports have been moved to alembic/env.py to avoid circular dependencies.
# DO NOT import models here. The metadata will be populated when models are imported
# by alembic/env.py during migrations.
