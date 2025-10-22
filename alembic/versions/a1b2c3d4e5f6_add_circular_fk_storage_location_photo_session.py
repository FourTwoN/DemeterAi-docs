"""Add circular FK storage_location.photo_session_id

This migration adds the circular foreign key constraint between
storage_locations and photo_processing_sessions tables.

Relationship:
    photo_processing_sessions.storage_location_id → storage_locations.location_id
    storage_locations.photo_session_id → photo_processing_sessions.id

This creates a circular reference but is valid because:
1. photo_processing_sessions is the "parent" (always created first)
2. storage_locations adds a "back-reference" (nullable, SET NULL on delete)
3. use_alter=True allows the FK to be added after both tables exist

Revision ID: a1b2c3d4e5f6
Revises: sof6kow8eu3r
Create Date: 2025-10-22 11:00:00.000000

"""
from collections.abc import Sequence

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = 'sof6kow8eu3r'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
  """Apply migration: Add circular FK constraint."""
  # Create the circular foreign key constraint
  # use_alter=True allows the FK to reference a table that has a FK back to this table
  op.create_foreign_key(
      'fk_storage_location_photo_session',
      'storage_locations',
      'photo_processing_sessions',
      ['photo_session_id'],
      ['id'],
      ondelete='SET NULL'
  )


def downgrade() -> None:
  """Revert migration: Remove circular FK constraint."""
  op.drop_constraint('fk_storage_location_photo_session', 'storage_locations',
                     type_='foreignkey')
