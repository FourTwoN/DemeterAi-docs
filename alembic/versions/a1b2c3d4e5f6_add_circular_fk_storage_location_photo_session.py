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
down_revision: str | None = '9f8e7d6c5b4a'  # Changed from sof6kow8eu3r to depend on all tables being created first
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
  """Apply migration: Add circular FK constraint."""
  # Create the circular foreign key constraint
  # Wrapped in conditional check since this depends on photo_processing_sessions table existing
  # which may be created in the other branch
  op.execute("""
    DO $$
    BEGIN
        -- Check if both tables exist and constraint doesn't already exist
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'photo_processing_sessions'
        ) AND EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'storage_locations'
        ) AND NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_storage_location_photo_session'
        ) THEN
            ALTER TABLE storage_locations ADD CONSTRAINT fk_storage_location_photo_session
                FOREIGN KEY(photo_session_id) REFERENCES photo_processing_sessions (id) ON DELETE SET NULL;
        END IF;
    END $$;
  """)


def downgrade() -> None:
  """Revert migration: Remove circular FK constraint."""
  op.drop_constraint('fk_storage_location_photo_session', 'storage_locations',
                     type_='foreignkey')
