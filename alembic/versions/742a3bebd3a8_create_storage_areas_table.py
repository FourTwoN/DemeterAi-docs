"""create storage_areas table

This migration creates the storage_areas table with PostGIS geometry support,
which is level 2 of the 4-tier geospatial location hierarchy.

Key features:
- position_enum (N, S, E, W, C - cardinal directions)
- PostGIS POLYGON for precise boundary definition (SRID 4326)
- Self-referential FK (parent_area_id) for hierarchical areas
- GENERATED column for area_m2 (auto-calculated from geometry)
- Database trigger for centroid auto-update
- Database trigger for spatial containment validation (area MUST be within warehouse)
- GIST indexes for spatial queries (<30ms performance target)

Architecture:
    Location Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N)
    Layer: Database / Migrations
    Dependencies: PostGIS 3.3+ extension (enabled in 6f1b94ebef45), warehouses table (2f68e3f132f5)

See:
    - Database ERD: ../../database/database.mmd
    - Task specification: ../../backlog/03_kanban/01_ready/DB002-storage-areas-model.md
    - Model: ../../app/models/storage_area.py

Revision ID: 742a3bebd3a8
Revises: 2f68e3f132f5
Create Date: 2025-10-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = '742a3bebd3a8'
down_revision: Union[str, None] = '2f68e3f132f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: Create storage_areas table with PostGIS geometry.

    Steps:
        1. Create position_enum type (idempotent)
        2. Create storage_areas table with PostGIS columns
        3. Add GENERATED column for area_m2
        4. Create trigger function for centroid auto-update
        5. Create trigger on geojson_coordinates changes
        6. Create trigger function for spatial containment validation
        7. Create trigger for containment check
        8. Create GIST spatial indexes
        9. Create standard B-tree indexes
    """
    # Step 1: Create ENUM type (idempotent - checks if exists first)
    op.execute("""
        DO $$
        BEGIN
            CREATE TYPE position_enum AS ENUM ('N', 'S', 'E', 'W', 'C');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # Step 2: Create storage_areas table (enum already created)
    op.create_table(
        'storage_areas',
        sa.Column('storage_area_id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key (auto-increment)'),
        sa.Column('warehouse_id', sa.Integer(), nullable=False, comment='Parent warehouse (CASCADE delete)'),
        sa.Column('parent_area_id', sa.Integer(), nullable=True, comment='Parent storage area for hierarchical subdivision (NULLABLE)'),
        sa.Column('code', sa.String(length=50), nullable=False, comment='Unique area code (format: WAREHOUSE-AREA, uppercase, 2-50 chars)'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Human-readable area name'),
        sa.Column('position', postgresql.ENUM('N', 'S', 'E', 'W', 'C', name='position_enum', create_type=False), nullable=True, comment='Cardinal direction: N, S, E, W, C (optional)'),
        sa.Column('geojson_coordinates', Geometry('POLYGON', srid=4326, spatial_index=False), nullable=False, comment='Storage area boundary polygon (WGS84 coordinates)'),
        sa.Column('centroid', Geometry('POINT', srid=4326, spatial_index=False), nullable=True, comment='Auto-calculated center point (database trigger)'),
        # area_m2 will be added as GENERATED column below
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Active status (soft delete)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('storage_area_id', name='pk_storage_areas'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.warehouse_id'], name='fk_storage_areas_warehouse_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_area_id'], ['storage_areas.storage_area_id'], name='fk_storage_areas_parent_area_id', ondelete='CASCADE'),
        sa.UniqueConstraint('code', name='uq_storage_areas_code'),
        sa.CheckConstraint('LENGTH(code) >= 2 AND LENGTH(code) <= 50', name='ck_storage_area_code_length'),
        comment='Storage Areas - Level 2 of 4-tier geospatial location hierarchy'
    )

    # Step 3: Add GENERATED column for area_m2 (PostgreSQL 12+)
    # This column is auto-calculated from geometry using ST_Area with geography cast
    # geography cast ensures accurate area calculation in square meters (not degrees)
    op.execute("""
        ALTER TABLE storage_areas
        ADD COLUMN area_m2 NUMERIC(10,2)
        GENERATED ALWAYS AS (
            ST_Area(geojson_coordinates::geography)
        ) STORED
    """)

    # Step 4: Create trigger function for centroid auto-update
    # This function calculates the centroid whenever geojson_coordinates changes
    # Uses ST_Centroid to find geometric center of polygon
    op.execute("""
        CREATE OR REPLACE FUNCTION update_storage_area_centroid()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Auto-calculate centroid from polygon geometry
            NEW.centroid = ST_Centroid(NEW.geojson_coordinates);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Step 5: Create trigger to auto-update centroid on INSERT or UPDATE
    # Trigger fires BEFORE INSERT OR UPDATE of geojson_coordinates
    # This ensures centroid is always synchronized with polygon boundary
    op.execute("""
        CREATE TRIGGER trg_storage_area_centroid
        BEFORE INSERT OR UPDATE OF geojson_coordinates ON storage_areas
        FOR EACH ROW
        EXECUTE FUNCTION update_storage_area_centroid();
    """)

    # Step 6: Create trigger function for spatial containment validation
    # This function ensures storage area geometry is within parent warehouse boundary
    # CRITICAL: Prevents creating areas outside warehouse boundaries
    op.execute("""
        CREATE OR REPLACE FUNCTION check_storage_area_within_warehouse()
        RETURNS TRIGGER AS $$
        DECLARE
            warehouse_geom geometry;
        BEGIN
            -- Fetch parent warehouse geometry
            SELECT geojson_coordinates INTO warehouse_geom
            FROM warehouses
            WHERE warehouse_id = NEW.warehouse_id;

            -- Check if warehouse exists
            IF warehouse_geom IS NULL THEN
                RAISE EXCEPTION 'Warehouse with ID % does not exist', NEW.warehouse_id;
            END IF;

            -- Check if storage area is within warehouse boundary
            IF NOT ST_Within(NEW.geojson_coordinates, warehouse_geom) THEN
                RAISE EXCEPTION 'Storage area geometry must be within warehouse boundary (warehouse_id: %)', NEW.warehouse_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Step 7: Create trigger for spatial containment check
    # Trigger fires BEFORE INSERT OR UPDATE of geojson_coordinates or warehouse_id
    # This ensures storage areas are always contained within their parent warehouse
    op.execute("""
        CREATE TRIGGER trg_storage_area_containment
        BEFORE INSERT OR UPDATE OF geojson_coordinates, warehouse_id ON storage_areas
        FOR EACH ROW
        EXECUTE FUNCTION check_storage_area_within_warehouse();
    """)

    # Step 8: Create GIST spatial indexes for PostGIS geometry columns
    # GIST indexes are critical for spatial query performance
    # Target: <30ms for ST_Contains queries on 100+ areas
    op.execute("CREATE INDEX idx_storage_areas_geom ON storage_areas USING GIST(geojson_coordinates);")
    op.execute("CREATE INDEX idx_storage_areas_centroid ON storage_areas USING GIST(centroid);")

    # Step 9: Create standard B-tree indexes for common queries
    op.create_index('idx_storage_areas_code', 'storage_areas', ['code'], unique=True)
    op.create_index('idx_storage_areas_warehouse_id', 'storage_areas', ['warehouse_id'])
    op.create_index('idx_storage_areas_parent_area_id', 'storage_areas', ['parent_area_id'])
    op.create_index('idx_storage_areas_position', 'storage_areas', ['position'])
    op.create_index('idx_storage_areas_active', 'storage_areas', ['active'])


def downgrade() -> None:
    """Rollback migration: Drop storage_areas table and related objects.

    Steps (reverse order of upgrade):
        1. Drop B-tree indexes
        2. Drop GIST spatial indexes
        3. Drop containment trigger
        4. Drop containment trigger function
        5. Drop centroid trigger
        6. Drop centroid trigger function
        7. Drop storage_areas table (enum auto-dropped by SQLAlchemy)
    """
    # Step 1: Drop B-tree indexes
    op.drop_index('idx_storage_areas_active', table_name='storage_areas')
    op.drop_index('idx_storage_areas_position', table_name='storage_areas')
    op.drop_index('idx_storage_areas_parent_area_id', table_name='storage_areas')
    op.drop_index('idx_storage_areas_warehouse_id', table_name='storage_areas')
    op.drop_index('idx_storage_areas_code', table_name='storage_areas')

    # Step 2: Drop GIST spatial indexes
    op.execute("DROP INDEX IF EXISTS idx_storage_areas_centroid;")
    op.execute("DROP INDEX IF EXISTS idx_storage_areas_geom;")

    # Step 3: Drop containment trigger
    op.execute("DROP TRIGGER IF EXISTS trg_storage_area_containment ON storage_areas;")

    # Step 4: Drop containment trigger function
    op.execute("DROP FUNCTION IF EXISTS check_storage_area_within_warehouse();")

    # Step 5: Drop centroid trigger
    op.execute("DROP TRIGGER IF EXISTS trg_storage_area_centroid ON storage_areas;")

    # Step 6: Drop centroid trigger function
    op.execute("DROP FUNCTION IF EXISTS update_storage_area_centroid();")

    # Step 7: Drop storage_areas table (CASCADE removes dependent objects, enum auto-dropped)
    op.drop_table('storage_areas')
