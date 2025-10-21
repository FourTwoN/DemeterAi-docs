"""create storage_locations table

This migration creates the storage_locations table with PostGIS POINT geometry,
which is level 3 of the 4-tier geospatial location hierarchy.

Key features:
- PostGIS POINT for single GPS coordinate (photo capture location)
- QR code for physical tracking via mobile app (unique, indexed)
- position_metadata JSONB for flexible camera/lighting data
- photo_session_id FK for circular reference (nullable, SET NULL on delete)
- GENERATED column for area_m2 (always 0 for POINT geometry)
- Database trigger for centroid auto-update (centroid = coordinates for POINT)
- Database trigger for spatial containment validation (POINT MUST be within StorageArea POLYGON)
- GIST indexes for spatial queries (<30ms performance target)

Architecture:
    Location Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N)
    Layer: Database / Migrations
    Dependencies: PostGIS 3.3+ (6f1b94ebef45), storage_areas (742a3bebd3a8)

See:
    - Database ERD: ../../database/database.mmd (lines 33-47)
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB003-storage-locations-model.md
    - Model: ../../app/models/storage_location.py

Revision ID: sof6kow8eu3r
Revises: 742a3bebd3a8
Create Date: 2025-10-13 17:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = 'sof6kow8eu3r'
down_revision: str | None = '742a3bebd3a8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration: Create storage_locations table with PostGIS POINT geometry.

    Steps:
        1. Create storage_locations table with PostGIS POINT columns
        2. Add GENERATED column for area_m2 (always 0 for POINT)
        3. Create trigger function for centroid auto-update (centroid = coordinates)
        4. Create trigger on coordinates changes
        5. Create trigger function for spatial containment validation (POINT within StorageArea POLYGON)
        6. Create trigger for containment check
        7. Create GIST spatial indexes
        8. Create standard B-tree indexes
    """
    # Step 1: Create storage_locations table
    op.create_table(
        'storage_locations',
        sa.Column('location_id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key (auto-increment)'),
        sa.Column('storage_area_id', sa.Integer(), nullable=False, comment='Parent storage area (CASCADE delete)'),
        sa.Column('photo_session_id', sa.Integer(), nullable=True, comment='Latest photo processing session for this location (nullable, SET NULL on delete)'),
        sa.Column('code', sa.String(length=50), nullable=False, comment='Unique location code (format: WAREHOUSE-AREA-LOCATION, uppercase, 2-50 chars)'),
        sa.Column('qr_code', sa.String(length=20), nullable=False, comment='Physical QR code label (alphanumeric + optional hyphen/underscore, 8-20 chars, uppercase)'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Human-readable location name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional detailed description'),
        sa.Column('coordinates', Geometry('POINT', srid=4326, spatial_index=False), nullable=False, comment='GPS coordinate where photo is taken (POINT geometry, WGS84)'),
        sa.Column('centroid', Geometry('POINT', srid=4326, spatial_index=False), nullable=True, comment='Auto-calculated center point (equals coordinates for POINT geometry)'),
        # area_m2 will be added as GENERATED column below
        sa.Column('position_metadata', JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment='Camera angle, height, lighting conditions (flexible JSONB structure)'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true'), comment='Active status (soft delete)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('location_id', name='pk_storage_locations'),
        sa.ForeignKeyConstraint(['storage_area_id'], ['storage_areas.storage_area_id'], name='fk_storage_locations_storage_area_id', ondelete='CASCADE'),
        # TODO: Uncomment when photo_processing_sessions table migration is created
        # sa.ForeignKeyConstraint(['photo_session_id'], ['photo_processing_sessions.session_id'], name='fk_storage_locations_photo_session_id', ondelete='SET NULL'),
        sa.UniqueConstraint('code', name='uq_storage_locations_code'),
        sa.UniqueConstraint('qr_code', name='uq_storage_locations_qr_code'),
        sa.CheckConstraint('LENGTH(code) >= 2 AND LENGTH(code) <= 50', name='ck_storage_location_code_length'),
        sa.CheckConstraint('LENGTH(qr_code) >= 8 AND LENGTH(qr_code) <= 20', name='ck_storage_location_qr_code_length'),
        comment='Storage Locations - Level 3 of 4-tier geospatial location hierarchy (photo unit)'
    )

    # Step 2: Add GENERATED column for area_m2 (always 0 for POINT geometry)
    # For POINT geometry, area is always 0 (no polygon to calculate area from)
    op.execute("""
        ALTER TABLE storage_locations
        ADD COLUMN area_m2 NUMERIC(10,2)
        GENERATED ALWAYS AS (0.0) STORED
    """)

    # Step 3: Create trigger function for centroid auto-update
    # For POINT geometry, centroid equals coordinates (no need to calculate)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_storage_location_centroid()
        RETURNS TRIGGER AS $$
        BEGIN
            -- For POINT geometry, centroid equals coordinates
            NEW.centroid = NEW.coordinates;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Step 4: Create trigger to auto-update centroid on INSERT or UPDATE
    # Trigger fires BEFORE INSERT OR UPDATE of coordinates
    # This ensures centroid is always synchronized with coordinates
    op.execute("""
        CREATE TRIGGER trg_storage_location_centroid
        BEFORE INSERT OR UPDATE OF coordinates ON storage_locations
        FOR EACH ROW
        EXECUTE FUNCTION update_storage_location_centroid();
    """)

    # Step 5: Create trigger function for spatial containment validation
    # This function ensures storage location POINT is within parent storage area POLYGON
    # CRITICAL: Prevents creating locations outside storage area boundaries
    op.execute("""
        CREATE OR REPLACE FUNCTION check_storage_location_within_area()
        RETURNS TRIGGER AS $$
        DECLARE
            area_geom geometry;
        BEGIN
            -- Fetch parent storage area geometry (POLYGON)
            SELECT geojson_coordinates INTO area_geom
            FROM storage_areas
            WHERE storage_area_id = NEW.storage_area_id;

            -- Check if storage area exists
            IF area_geom IS NULL THEN
                RAISE EXCEPTION 'StorageArea with ID % does not exist', NEW.storage_area_id;
            END IF;

            -- Check if location POINT is within area POLYGON
            IF NOT ST_Within(NEW.coordinates, area_geom) THEN
                RAISE EXCEPTION 'Storage location POINT must be within parent storage area POLYGON (storage_area_id: %)', NEW.storage_area_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Step 6: Create trigger for spatial containment check
    # Trigger fires BEFORE INSERT OR UPDATE of coordinates or storage_area_id
    # This ensures storage locations are always contained within their parent storage area
    op.execute("""
        CREATE TRIGGER trg_storage_location_containment
        BEFORE INSERT OR UPDATE OF coordinates, storage_area_id ON storage_locations
        FOR EACH ROW
        EXECUTE FUNCTION check_storage_location_within_area();
    """)

    # Step 7: Create GIST spatial indexes for PostGIS geometry columns
    # GIST indexes are critical for spatial query performance
    # Target: <30ms for ST_Contains queries on 100+ locations
    op.execute("CREATE INDEX idx_storage_locations_coords ON storage_locations USING GIST(coordinates);")
    op.execute("CREATE INDEX idx_storage_locations_centroid ON storage_locations USING GIST(centroid);")

    # Step 8: Create standard B-tree indexes for common queries
    op.create_index('idx_storage_locations_code', 'storage_locations', ['code'], unique=True)
    op.create_index('idx_storage_locations_qr_code', 'storage_locations', ['qr_code'], unique=True)
    op.create_index('idx_storage_locations_storage_area_id', 'storage_locations', ['storage_area_id'])
    op.create_index('idx_storage_locations_photo_session_id', 'storage_locations', ['photo_session_id'])
    op.create_index('idx_storage_locations_active', 'storage_locations', ['active'])


def downgrade() -> None:
    """Rollback migration: Drop storage_locations table and related objects.

    Steps (reverse order of upgrade):
        1. Drop B-tree indexes
        2. Drop GIST spatial indexes
        3. Drop containment trigger
        4. Drop containment trigger function
        5. Drop centroid trigger
        6. Drop centroid trigger function
        7. Drop storage_locations table
    """
    # Step 1: Drop B-tree indexes
    op.drop_index('idx_storage_locations_active', table_name='storage_locations')
    op.drop_index('idx_storage_locations_photo_session_id', table_name='storage_locations')
    op.drop_index('idx_storage_locations_storage_area_id', table_name='storage_locations')
    op.drop_index('idx_storage_locations_qr_code', table_name='storage_locations')
    op.drop_index('idx_storage_locations_code', table_name='storage_locations')

    # Step 2: Drop GIST spatial indexes
    op.execute("DROP INDEX IF EXISTS idx_storage_locations_centroid;")
    op.execute("DROP INDEX IF EXISTS idx_storage_locations_coords;")

    # Step 3: Drop containment trigger
    op.execute("DROP TRIGGER IF EXISTS trg_storage_location_containment ON storage_locations;")

    # Step 4: Drop containment trigger function
    op.execute("DROP FUNCTION IF EXISTS check_storage_location_within_area();")

    # Step 5: Drop centroid trigger
    op.execute("DROP TRIGGER IF EXISTS trg_storage_location_centroid ON storage_locations;")

    # Step 6: Drop centroid trigger function
    op.execute("DROP FUNCTION IF EXISTS update_storage_location_centroid();")

    # Step 7: Drop storage_locations table (CASCADE removes dependent objects)
    op.drop_table('storage_locations')
