"""s3_bucket_consolidation_add_image_type_and_processed_key

Revision ID: b5820a339233
Revises: c3d4e5f6g7h8
Create Date: 2025-10-24 10:17:32.946077

Migration for S3 bucket consolidation (Task S043):
- Add image_type ENUM (original, processed, thumbnail)
- Add s3_key_processed column for ML visualization images
- Set default image_type based on existing data

Architecture:
    Single bucket (demeter-photos-original) with folder structure:
    - {session_id}/original.{ext}
    - {session_id}/processed.{ext}
    - {session_id}/thumbnail.{ext}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5820a339233'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add image_type ENUM and s3_key_processed column to s3_images table.

    Steps:
    1. Create image_type_enum ENUM type
    2. Add s3_key_processed column (nullable)
    3. Add image_type column (nullable, default='original')
    4. Set image_type based on existing s3_bucket values
    """

    # Step 1: Create image_type_enum ENUM type
    image_type_enum = sa.Enum(
        'original',
        'processed',
        'thumbnail',
        name='image_type_enum'
    )
    image_type_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: Add s3_key_processed column (nullable)
    op.add_column(
        's3_images',
        sa.Column(
            's3_key_processed',
            sa.String(512),
            nullable=True,
            comment='S3 key for ML-processed visualization image (nullable)'
        )
    )

    # Step 3: Add image_type column (nullable, default='original')
    op.add_column(
        's3_images',
        sa.Column(
            'image_type',
            image_type_enum,
            nullable=True,
            comment='Image type (original, processed, thumbnail)'
        )
    )

    # Step 4: Set default image_type based on existing s3_bucket values
    # - Images in demeter-photos-original → 'original'
    # - Images in demeter-photos-viz → 'processed'
    op.execute(
        """
        UPDATE s3_images
        SET image_type = 'original'
        WHERE s3_bucket = 'demeter-photos-original'
        AND image_type IS NULL
        """
    )

    op.execute(
        """
        UPDATE s3_images
        SET image_type = 'processed'
        WHERE s3_bucket = 'demeter-photos-viz'
        AND image_type IS NULL
        """
    )

    # Step 5: For processed images, copy s3_key_original to s3_key_processed
    op.execute(
        """
        UPDATE s3_images
        SET s3_key_processed = s3_key_original
        WHERE image_type = 'processed'
        AND s3_key_processed IS NULL
        """
    )


def downgrade() -> None:
    """
    Remove image_type and s3_key_processed columns.

    Steps:
    1. Drop image_type column
    2. Drop s3_key_processed column
    3. Drop image_type_enum ENUM type
    """

    # Step 1: Drop image_type column
    op.drop_column('s3_images', 'image_type')

    # Step 2: Drop s3_key_processed column
    op.drop_column('s3_images', 's3_key_processed')

    # Step 3: Drop image_type_enum ENUM type
    image_type_enum = sa.Enum(
        'original',
        'processed',
        'thumbnail',
        name='image_type_enum'
    )
    image_type_enum.drop(op.get_bind(), checkfirst=True)
