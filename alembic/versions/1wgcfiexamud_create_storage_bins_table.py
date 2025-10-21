"""create storage_bins table

This migration creates the storage_bins table, which is level 4 (LEAF LEVEL)
of the 4-tier geospatial location hierarchy. This is the SIMPLEST MODEL YET
with NO PostGIS complexity!

Key features:
- NO PostGIS geometry (bins inherit location from parent StorageLocation)
- JSONB position_metadata for ML segmentation output (mask, bbox, confidence)
- Status enum: active, maintenance, retired (retired is terminal state)
- Code validation: WAREHOUSE-AREA-LOCATION-BIN pattern (4 parts)
- CASCADE delete from storage_location (intentional - bins deleted with parent)
- RESTRICT delete from storage_bin_type (safety - cannot delete type if bins exist)
- NO GIST indexes (no spatial queries)
- ONLY B-tree indexes + GIN index on JSONB (for confidence, container_type queries)

Architecture:
    Location Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N) [LEAF]
    Layer: Database / Migrations
    Dependencies: storage_locations (sof6kow8eu3r), storage_bin_types (pending DB005)

See:
    - Database ERD: ../../database/database.mmd (lines 48-58)
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB004-storage-bins-model.md
    - Model: ../../app/models/storage_bin.py

Revision ID: 1wgcfiexamud
Revises: sof6kow8eu3r
Create Date: 2025-10-13 17:45:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = '1wgcfiexamud'
down_revision: str | None = '2wh7p3r9bm6t'  # Fixed: bins come after bin_types
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration: Create storage_bins table with JSONB position_metadata.

    Steps:
        1. Create storage_bin_status_enum type (idempotent)
        2. Create storage_bins table with FKs and JSONB
        3. Create B-tree indexes (code, storage_location_id, storage_bin_type_id, status)
        4. Create GIN index on position_metadata (JSONB queries)
    """
    # Step 1: Create ENUM type (idempotent - checks if exists first)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE storage_bin_status_enum AS ENUM ('active', 'maintenance', 'retired');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # Step 2: Create storage_bins table
    # NO PostGIS geometry columns - simplest model yet!
    op.create_table(
        'storage_bins',
        sa.Column('bin_id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key (auto-increment)'),
        sa.Column('storage_location_id', sa.Integer(), nullable=False, comment='Parent storage location (CASCADE delete)'),
        sa.Column('storage_bin_type_id', sa.Integer(), nullable=True, comment='Bin type definition (RESTRICT delete, optional)'),
        sa.Column('code', sa.String(length=100), nullable=False, comment='Unique bin code (format: WAREHOUSE-AREA-LOCATION-BIN, 4 parts, 2-100 chars)'),
        sa.Column('label', sa.String(length=100), nullable=True, comment='Human-readable bin name (optional)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional detailed description'),
        sa.Column('position_metadata', JSONB(), nullable=True, comment='ML segmentation output: mask, bbox, confidence, ml_model_version, container_type'),
        sa.Column('status', postgresql.ENUM('active', 'maintenance', 'retired', name='storage_bin_status_enum', create_type=False), nullable=False, server_default='active', comment='Status enum: active, maintenance, retired (terminal state)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('bin_id', name='pk_storage_bins'),
        sa.ForeignKeyConstraint(['storage_location_id'], ['storage_locations.location_id'], name='fk_storage_bins_storage_location_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['storage_bin_type_id'], ['storage_bin_types.bin_type_id'], name='fk_storage_bins_storage_bin_type_id', ondelete='RESTRICT'),
        sa.UniqueConstraint('code', name='uq_storage_bins_code'),
        sa.CheckConstraint('LENGTH(code) >= 2 AND LENGTH(code) <= 100', name='ck_storage_bin_code_length'),
        comment='Storage Bins - Level 4 (LEAF) of 4-tier geospatial location hierarchy (physical container)'
    )

    # Step 3: Create B-tree indexes for common queries
    # NO GIST indexes - no spatial queries needed (bins inherit location from parent)
    op.create_index('idx_storage_bins_code', 'storage_bins', ['code'], unique=True)
    op.create_index('idx_storage_bins_location_id', 'storage_bins', ['storage_location_id'])
    op.create_index('idx_storage_bins_type_id', 'storage_bins', ['storage_bin_type_id'])
    op.create_index('idx_storage_bins_status', 'storage_bins', ['status'])

    # Step 4: Create GIN index on position_metadata for JSONB queries
    # This enables efficient queries on:
    # - confidence (filter low confidence bins)
    # - container_type (segmento vs cajon vs box)
    # - ml_model_version (track which model version detected bin)
    # Example query: WHERE position_metadata->>'confidence'::float > 0.7
    op.execute("""
        CREATE INDEX idx_storage_bins_position_metadata
        ON storage_bins USING GIN(position_metadata)
    """)


def downgrade() -> None:
    """Rollback migration: Drop storage_bins table and enum type.

    Steps (reverse order of upgrade):
        1. Drop GIN index on position_metadata
        2. Drop B-tree indexes
        3. Drop storage_bins table
        4. Drop storage_bin_status_enum type
    """
    # Step 1: Drop GIN index on position_metadata
    op.execute("DROP INDEX IF EXISTS idx_storage_bins_position_metadata;")

    # Step 2: Drop B-tree indexes
    op.drop_index('idx_storage_bins_status', table_name='storage_bins')
    op.drop_index('idx_storage_bins_type_id', table_name='storage_bins')
    op.drop_index('idx_storage_bins_location_id', table_name='storage_bins')
    op.drop_index('idx_storage_bins_code', table_name='storage_bins')

    # Step 3: Drop storage_bins table (CASCADE removes dependent objects)
    op.drop_table('storage_bins')

    # Step 4: Drop storage_bin_status_enum type
    op.execute("DROP TYPE IF EXISTS storage_bin_status_enum;")
