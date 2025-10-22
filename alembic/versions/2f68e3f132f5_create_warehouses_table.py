"""create warehouses table

This migration creates the warehouses table with PostGIS geometry support,
which is the root level of the 4-tier geospatial location hierarchy.

Key features:
- warehouse_type_enum (greenhouse, shadehouse, open_field, tunnel)
- PostGIS POLYGON for precise boundary definition (SRID 4326)
- GENERATED column for area_m2 (auto-calculated from geometry)
- Database trigger for centroid auto-update
- GIST indexes for spatial queries (<50ms performance target)

Architecture:
    Location Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N)
    Layer: Database / Migrations
    Dependencies: PostGIS 3.3+ extension (enabled in 6f1b94ebef45)

See:
    - Database ERD: ../../database/database.mmd (lines 8-19)
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB001-warehouses-model.md
    - Model: ../../app/models/warehouse.py

Revision ID: 2f68e3f132f5
Revises: 6f1b94ebef45
Create Date: 2025-10-13 15:36:55.434382

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2f68e3f132f5'
down_revision: Union[str, None] = '6f1b94ebef45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Apply migration: Create warehouses table with PostGIS geometry.

  Steps:
      1. Create ENUM type (idempotent)
      2. Create warehouses table with PostGIS columns
      3. Add GENERATED column for area_m2
      4. Create trigger function for centroid auto-update
      5. Create trigger on geojson_coordinates changes
      6. Create GIST spatial indexes
      7. Create standard B-tree indexes
  """
  # Step 0: Create ENUM type (idempotent - checks if exists first)
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE warehouse_type_enum AS ENUM ('greenhouse', 'shadehouse', 'open_field', 'tunnel');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # Step 1: Create warehouses table (enum already created)
  op.create_table(
      'warehouses',
      sa.Column('warehouse_id', sa.Integer(), autoincrement=True,
                nullable=False, comment='Primary key (auto-increment)'),
      sa.Column('code', sa.String(length=50), nullable=False,
                comment='Unique warehouse code (uppercase alphanumeric, 2-20 chars)'),
      sa.Column('name', sa.String(length=200), nullable=False,
                comment='Human-readable warehouse name'),
      sa.Column('warehouse_type',
                postgresql.ENUM('greenhouse', 'shadehouse', 'open_field',
                                'tunnel', name='warehouse_type_enum',
                                create_type=False), nullable=False,
                comment='Facility type: greenhouse, shadehouse, open_field, tunnel'),
      sa.Column('geojson_coordinates',
                Geometry('POLYGON', srid=4326, spatial_index=False),
                nullable=False,
                comment='Warehouse boundary polygon (WGS84 coordinates)'),
      sa.Column('centroid', Geometry('POINT', srid=4326, spatial_index=False),
                nullable=True,
                comment='Auto-calculated center point (database trigger)'),
      # area_m2 will be added as GENERATED column below
      sa.Column('active', sa.Boolean(), nullable=False,
                server_default=sa.text('true'),
                comment='Active status (soft delete)'),
      sa.Column('created_at', sa.DateTime(timezone=True),
                server_default=sa.text('now()'), nullable=False,
                comment='Record creation timestamp'),
      sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                comment='Last update timestamp'),
      sa.PrimaryKeyConstraint('warehouse_id', name='pk_warehouses'),
      sa.UniqueConstraint('code', name='uq_warehouses_code'),
      sa.CheckConstraint('LENGTH(code) >= 2 AND LENGTH(code) <= 20',
                         name='ck_warehouse_code_length'),
      comment='Warehouses - Root level of 4-tier geospatial location hierarchy'
  )

  # Step 2: Add GENERATED column for area_m2 (PostgreSQL 12+)
  # This column is auto-calculated from geometry using ST_Area with geography cast
  # geography cast ensures accurate area calculation in square meters (not degrees)
  op.execute("""
             ALTER TABLE warehouses
                 ADD COLUMN area_m2 NUMERIC(10, 2)
                     GENERATED ALWAYS AS (
                         ST_Area(geojson_coordinates::geography)
                         ) STORED
             """)

  # Step 3: Create trigger function for centroid auto-update
  # This function calculates the centroid whenever geojson_coordinates changes
  # Uses ST_Centroid to find geometric center of polygon
  op.execute("""
             CREATE
             OR REPLACE FUNCTION update_warehouse_centroid()
        RETURNS TRIGGER AS $$
             BEGIN
            -- Auto-calculate centroid from polygon geometry
            NEW.centroid
             = ST_Centroid(NEW.geojson_coordinates);
             RETURN NEW;
             END;
        $$
             LANGUAGE plpgsql;
             """)

  # Step 4: Create trigger to auto-update centroid on INSERT or UPDATE
  # Trigger fires BEFORE INSERT OR UPDATE of geojson_coordinates
  # This ensures centroid is always synchronized with polygon boundary
  op.execute("""
             CREATE TRIGGER trg_warehouse_centroid
                 BEFORE INSERT OR
             UPDATE OF geojson_coordinates
             ON warehouses
                 FOR EACH ROW
                 EXECUTE FUNCTION update_warehouse_centroid();
             """)

  # Step 5: Create GIST spatial indexes for PostGIS geometry columns
  # GIST indexes are critical for spatial query performance
  # Target: <50ms for ST_DWithin queries on 100+ warehouses
  op.execute(
      "CREATE INDEX idx_warehouses_geom ON warehouses USING GIST(geojson_coordinates);")
  op.execute(
      "CREATE INDEX idx_warehouses_centroid ON warehouses USING GIST(centroid);")

  # Step 6: Create standard B-tree indexes for common queries
  op.create_index('idx_warehouses_code', 'warehouses', ['code'], unique=True)
  op.create_index('idx_warehouses_type', 'warehouses', ['warehouse_type'])
  op.create_index('idx_warehouses_active', 'warehouses', ['active'])


def downgrade() -> None:
  """Rollback migration: Drop warehouses table and related objects.

  Steps (reverse order of upgrade):
      1. Drop B-tree indexes
      2. Drop GIST spatial indexes
      3. Drop trigger
      4. Drop trigger function
      5. Drop warehouses table (enum auto-dropped by SQLAlchemy)
  """
  # Step 1: Drop B-tree indexes
  op.drop_index('idx_warehouses_active', table_name='warehouses')
  op.drop_index('idx_warehouses_type', table_name='warehouses')
  op.drop_index('idx_warehouses_code', table_name='warehouses')

  # Step 2: Drop GIST spatial indexes
  op.execute("DROP INDEX IF EXISTS idx_warehouses_centroid;")
  op.execute("DROP INDEX IF EXISTS idx_warehouses_geom;")

  # Step 3: Drop trigger
  op.execute("DROP TRIGGER IF EXISTS trg_warehouse_centroid ON warehouses;")

  # Step 4: Drop trigger function
  op.execute("DROP FUNCTION IF EXISTS update_warehouse_centroid();")

  # Step 5: Drop warehouses table (CASCADE removes dependent objects, enum auto-dropped)
  op.drop_table('warehouses')
