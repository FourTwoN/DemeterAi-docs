"""create s3_images table

Revision ID: 440n457t9cnp
Revises: 6kp8m3q9n5rt
Create Date: 2025-10-14 14:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '440n457t9cnp'
down_revision: Union[str, None] = '6kp8m3q9n5rt'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Create s3_images table with UUID primary key and 3 enum types."""
  # 1. Create ENUM types (idempotent - checks if exists first)
  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE content_type_enum AS ENUM ('image/jpeg', 'image/png');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE upload_source_enum AS ENUM ('web', 'mobile', 'api');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  op.execute("""
        DO $$
        BEGIN
            CREATE TYPE processing_status_enum AS ENUM ('uploaded', 'processing', 'ready', 'failed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

  # 2. Create s3_images table (enums already created)
  op.create_table(
      's3_images',
      sa.Column(
          'image_id',
          postgresql.UUID(as_uuid=True),
          nullable=False,
          comment='UUID primary key (API-generated, not database default)'
      ),
      sa.Column(
          's3_bucket',
          sa.String(length=255),
          nullable=False,
          comment='S3 bucket name (e.g., "demeter-photos")'
      ),
      sa.Column(
          's3_key_original',
          sa.String(length=512),
          nullable=False,
          comment='S3 key for original image (unique, indexed)'
      ),
      sa.Column(
          's3_key_thumbnail',
          sa.String(length=512),
          nullable=True,
          comment='S3 key for thumbnail image (nullable)'
      ),
      sa.Column(
          'content_type',
          postgresql.ENUM('image/jpeg', 'image/png', name='content_type_enum',
                          create_type=False),
          nullable=False,
          comment='Image MIME type (image/jpeg, image/png)'
      ),
      sa.Column(
          'file_size_bytes',
          sa.BigInteger(),
          nullable=False,
          comment='File size in bytes (BigInteger for large files > 4GB)'
      ),
      sa.Column(
          'width_px',
          sa.Integer(),
          nullable=False,
          comment='Image width in pixels'
      ),
      sa.Column(
          'height_px',
          sa.Integer(),
          nullable=False,
          comment='Image height in pixels'
      ),
      sa.Column(
          'exif_metadata',
          postgresql.JSONB(astext_type=sa.Text()),
          nullable=True,
          comment='EXIF metadata (camera, ISO, shutter speed, f-stop, etc.)'
      ),
      sa.Column(
          'gps_coordinates',
          postgresql.JSONB(astext_type=sa.Text()),
          nullable=True,
          comment='GPS coordinates {lat, lng, altitude, accuracy} for location matching'
      ),
      sa.Column(
          'upload_source',
          postgresql.ENUM('web', 'mobile', 'api', name='upload_source_enum',
                          create_type=False),
          nullable=False,
          server_default='web',
          comment='Upload source (web, mobile, api)'
      ),
      sa.Column(
          'uploaded_by_user_id',
          sa.Integer(),
          nullable=True,
          comment='User who uploaded the image (nullable, SET NULL on delete)'
      ),
      sa.Column(
          'status',
          postgresql.ENUM('uploaded', 'processing', 'ready', 'failed',
                          name='processing_status_enum', create_type=False),
          nullable=False,
          server_default='uploaded',
          comment='Processing status (uploaded, processing, ready, failed)'
      ),
      sa.Column(
          'error_details',
          sa.Text(),
          nullable=True,
          comment='Error message if status = failed (nullable)'
      ),
      sa.Column(
          'processing_status_updated_at',
          sa.DateTime(timezone=True),
          nullable=True,
          comment='Timestamp of last status change (nullable)'
      ),
      sa.Column(
          'created_at',
          sa.DateTime(timezone=True),
          server_default=sa.text('NOW()'),
          nullable=False,
          comment='Record creation timestamp'
      ),
      sa.Column(
          'updated_at',
          sa.DateTime(timezone=True),
          nullable=True,
          comment='Last update timestamp'
      ),
      sa.PrimaryKeyConstraint('image_id', name=op.f('pk_s3_images')),
      sa.UniqueConstraint('s3_key_original',
                          name=op.f('uq_s3_images_s3_key_original')),
      sa.ForeignKeyConstraint(
          ['uploaded_by_user_id'],
          ['users.id'],
          name=op.f('fk_s3_images_uploaded_by_user_id_users'),
          ondelete='SET NULL'
      ),
      comment='S3 Images - Uploaded image metadata with UUID primary key'
  )

  # 3. Create indexes
  op.create_index(
      op.f('ix_s3_images_status'),
      's3_images',
      ['status'],
      unique=False
  )

  op.create_index(
      'ix_s3_images_created_at_desc',
      's3_images',
      [sa.text('created_at DESC')],
      unique=False
  )

  op.create_index(
      op.f('ix_s3_images_uploaded_by_user_id'),
      's3_images',
      ['uploaded_by_user_id'],
      unique=False
  )

  # 4. Create GIN index for JSONB GPS coordinates (spatial queries)
  op.execute("""
             CREATE INDEX ix_s3_images_gps_coordinates_gin
                 ON s3_images
                 USING GIN (gps_coordinates);
             """)


def downgrade() -> None:
  """Drop s3_images table and enum types."""
  # 1. Drop GIN index
  op.execute('DROP INDEX ix_s3_images_gps_coordinates_gin;')

  # 2. Drop B-tree indexes
  op.drop_index(op.f('ix_s3_images_uploaded_by_user_id'),
                table_name='s3_images')
  op.drop_index('ix_s3_images_created_at_desc', table_name='s3_images')
  op.drop_index(op.f('ix_s3_images_status'), table_name='s3_images')

  # 3. Drop table (enums auto-dropped by SQLAlchemy)
  op.drop_table('s3_images')
