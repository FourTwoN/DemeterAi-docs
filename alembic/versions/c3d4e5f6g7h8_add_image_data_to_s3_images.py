"""add image_data to s3_images

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-10-24 10:00:00.000000

Description:
    Adds image_data BYTEA column to s3_images table for caching image binary data
    in PostgreSQL. This enables Celery workers to access images without S3 download,
    improving ML processing performance in containerized environments.

Priority Order (after this migration):
    1. PostgreSQL image_data (fastest)
    2. /tmp local cache (retry optimization)
    3. S3 download (fallback)

Design Decisions:
    - BYTEA column: Binary data storage (nullable)
    - No size limit: Store all images regardless of size
    - Eager write: Binary data written during upload
    - Auto cleanup: Deleted after ML processing completes
    - Nullable: Existing records and S3-only mode still supported
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add image_data BYTEA column to s3_images table."""
    op.add_column(
        's3_images',
        sa.Column(
            'image_data',
            sa.LargeBinary(),  # PostgreSQL BYTEA type
            nullable=True,
            comment='Binary image data cached in PostgreSQL (deleted after ML processing)',
        )
    )


def downgrade() -> None:
    """Remove image_data column from s3_images table."""
    op.drop_column('s3_images', 'image_data')
