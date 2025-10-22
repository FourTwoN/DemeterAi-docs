"""create_storage_bin_types_table

Revision ID: 2wh7p3r9bm6t
Revises: 1wgcfiexamud
Create Date: 2025-10-14 10:40:00.000000

Creates the storage_bin_types reference/catalog table with:
- bin_category_enum type (5 values: plug, seedling_tray, box, segment, pot)
- Table with all fields (code, name, category, dimensions, grid flag)
- CHECK constraint: Grid types must have rows AND columns NOT NULL
- Indexes: code (UK), category
- SEED DATA: 7 common bin types (plug trays, seedling trays, boxes, segments, pots)

This is a SIMPLE reference table (no PostGIS, no triggers).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2wh7p3r9bm6t'
down_revision: Union[
  str, None] = 'sof6kow8eu3r'  # Fixed: bin_types must come before bins
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Create storage_bin_types table with seed data."""

  # 1. Create ENUM type (idempotent - checks if exists first)
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE bin_category_enum AS ENUM ('plug', 'seedling_tray', 'box', 'segment', 'pot');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # 2. Create storage_bin_types table (enum already created)
  op.create_table(
      'storage_bin_types',
      sa.Column('bin_type_id', sa.Integer(), autoincrement=True, nullable=False,
                comment='Primary key (auto-increment)'),
      sa.Column('code', sa.String(length=50), nullable=False,
                comment='Unique bin type code (uppercase, alphanumeric + underscores, 3-50 chars)'),
      sa.Column('name', sa.String(length=200), nullable=False,
                comment='Human-readable type name'),
      sa.Column('category',
                postgresql.ENUM('plug', 'seedling_tray', 'box', 'segment',
                                'pot', name='bin_category_enum',
                                create_type=False), nullable=False,
                comment='Category: plug, seedling_tray, box, segment, pot'),
      sa.Column('description', sa.Text(), nullable=True,
                comment='Optional detailed description'),
      sa.Column('rows', sa.Integer(), nullable=True,
                comment='Number of rows (nullable, required for grid types)'),
      sa.Column('columns', sa.Integer(), nullable=True,
                comment='Number of columns (nullable, required for grid types)'),
      sa.Column('capacity', sa.Integer(), nullable=True,
                comment='Total capacity (nullable, may differ from rows×columns)'),
      sa.Column('length_cm', sa.Numeric(precision=6, scale=2), nullable=True,
                comment='Container length in cm (nullable)'),
      sa.Column('width_cm', sa.Numeric(precision=6, scale=2), nullable=True,
                comment='Container width in cm (nullable)'),
      sa.Column('height_cm', sa.Numeric(precision=6, scale=2), nullable=True,
                comment='Container height in cm (nullable)'),
      sa.Column('is_grid', sa.Boolean(), server_default='false', nullable=False,
                comment='True for plug trays with grid structure (default FALSE)'),
      sa.Column('created_at', sa.DateTime(timezone=True),
                server_default=sa.text('now()'), nullable=False,
                comment='Record creation timestamp'),
      sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                comment='Last update timestamp'),
      sa.CheckConstraint("LENGTH(code) >= 3 AND LENGTH(code) <= 50",
                         name='ck_storage_bin_type_code_length'),
      sa.CheckConstraint(
          "(is_grid = false) OR (is_grid = true AND rows IS NOT NULL AND columns IS NOT NULL)",
          name='ck_storage_bin_type_grid_requires_rows_columns'),
      sa.PrimaryKeyConstraint('bin_type_id'),
      sa.UniqueConstraint('code'),
      comment='Storage Bin Types - Reference/catalog table defining container types'
  )

  # 3. Create indexes
  op.create_index('ix_storage_bin_types_code', 'storage_bin_types', ['code'],
                  unique=True)
  op.create_index('ix_storage_bin_types_category', 'storage_bin_types',
                  ['category'], unique=False)

  # 4. Insert seed data (7 common bin types)
  op.execute("""
             INSERT INTO storage_bin_types (code, name, category, rows, columns,
                                            capacity, is_grid, length_cm,
                                            width_cm, height_cm, description)
             VALUES

                 -- PLUG TRAYS (is_grid = TRUE, rows/columns NOT NULL)
                 ('PLUG_TRAY_288', '288-Cell Plug Tray', 'plug', 18, 16, 288,
                  TRUE, 54.0, 27.5, 5.5,
                  'Standard 288-cell plug tray (18 rows × 16 columns)'),
                 ('PLUG_TRAY_128', '128-Cell Plug Tray', 'plug', 8, 16, 128,
                  TRUE, 54.0, 27.5, 6.0,
                  'Standard 128-cell plug tray (8 rows × 16 columns)'),
                 ('PLUG_TRAY_72', '72-Cell Plug Tray', 'plug', 6, 12, 72, TRUE,
                  54.0, 27.5, 6.5,
                  'Standard 72-cell plug tray (6 rows × 12 columns)'),

                 -- SEEDLING TRAYS (is_grid = TRUE, rows/columns NOT NULL)
                 ('SEEDLING_TRAY_50', '50-Cell Seedling Tray', 'seedling_tray',
                  5, 10, 50, TRUE, 54.0, 27.5, 6.0,
                  'Standard 50-cell seedling tray (5 rows × 10 columns)'),

                 -- BOXES (is_grid = FALSE, rows/columns NULL)
                 ('BOX_STANDARD', 'Standard Transport Box', 'box', NULL, NULL,
                  100, FALSE, 60.0, 40.0, 30.0,
                  'Standard transport box for plant storage'),

                 -- SEGMENTS (is_grid = FALSE, rows/columns NULL, NO dimensions)
                 ('SEGMENT_STANDARD', 'Individual Segment', 'segment', NULL,
                  NULL, NULL, FALSE, NULL, NULL, NULL,
                  'Individual segment detected by ML (no fixed dimensions)'),

                 -- POTS (is_grid = FALSE, rows/columns NULL)
                 ('POT_10CM', '10cm Diameter Pot', 'pot', NULL, NULL, 1, FALSE,
                  10.0, 10.0, 10.0,
                  'Standard 10cm diameter pot for individual plants');
             """)


def downgrade() -> None:
  """Drop storage_bin_types table and enum."""

  # 1. Drop indexes
  op.drop_index('ix_storage_bin_types_category', table_name='storage_bin_types')
  op.drop_index('ix_storage_bin_types_code', table_name='storage_bin_types')

  # 2. Drop table (enum auto-dropped by SQLAlchemy)
  op.drop_table('storage_bin_types')
