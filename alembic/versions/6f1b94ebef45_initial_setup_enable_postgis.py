"""initial_setup_enable_postgis

Revision ID: 6f1b94ebef45
Revises:
Create Date: 2025-10-13 12:47:44.809576

This is the foundational migration for DemeterAI v2.0. It enables the
PostGIS extension which is required for geospatial functionality.

DemeterAI uses PostGIS for:
- 4-level geospatial hierarchy: warehouse → storage_area → storage_location → storage_bin
- GeoJSON coordinate storage (POLYGON, POINT geometries)
- Spatial queries and relationships

PostGIS extension provides:
- geometry and geography data types
- Spatial functions (ST_Contains, ST_Distance, ST_Intersects)
- Spatial indexes (GIST)

This migration must be applied BEFORE creating any models with geometry columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f1b94ebef45'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable PostGIS extension.

    Creates the PostGIS extension which adds spatial database capabilities
    to PostgreSQL. This is required for storing and querying geospatial data.

    The IF NOT EXISTS clause makes this migration idempotent - safe to run
    multiple times without errors.
    """
    # Enable PostGIS extension for spatial database features
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')

    # Optionally enable PostGIS topology (if needed for future features)
    # op.execute('CREATE EXTENSION IF NOT EXISTS postgis_topology')

    # Verify PostGIS is installed (this query will fail if extension not loaded)
    # The version check ensures PostGIS functions are available
    op.execute('SELECT PostGIS_Version()')


def downgrade() -> None:
    """Disable PostGIS extension.

    Removes the PostGIS extension from the database. This will CASCADE and
    drop all geometry columns and spatial indexes that depend on PostGIS.

    WARNING: This operation is destructive. All geospatial data will be lost.
    Only run this if you're certain you want to remove PostGIS.
    """
    # Drop PostGIS extension (CASCADE will drop dependent objects)
    op.execute('DROP EXTENSION IF EXISTS postgis CASCADE')

    # Note: In production, you may want to disable downgrade for this migration
    # to prevent accidental data loss. Uncomment the following to block downgrades:
    # raise Exception("Cannot downgrade initial PostGIS migration - would lose all geospatial data")
