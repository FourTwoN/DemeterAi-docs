"""make_original_image_id_nullable_in_photo_processing_sessions

Revision ID: cd8d2c2050ab
Revises: b5820a339233
Create Date: 2025-10-24 11:04:45.690388

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd8d2c2050ab'
down_revision: Union[str, None] = 'b5820a339233'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make original_image_id nullable in photo_processing_sessions table.

    This allows creating PhotoProcessingSession BEFORE uploading original image to S3.
    This ensures all S3 uploads (original, processed, thumbnails) use the same session.session_id UUID.

    Before: original_image_id UUID NOT NULL
    After:  original_image_id UUID NULL
    """
    # Make original_image_id nullable
    op.alter_column(
        'photo_processing_sessions',
        'original_image_id',
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    """Revert original_image_id to NOT NULL.

    WARNING: This will fail if any records have NULL original_image_id.
    Ensure all sessions have original_image_id set before downgrading.
    """
    # Make original_image_id NOT NULL again
    op.alter_column(
        'photo_processing_sessions',
        'original_image_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
