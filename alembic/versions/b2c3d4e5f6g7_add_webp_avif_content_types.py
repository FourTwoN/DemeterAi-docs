"""add webp and avif content types

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add image/webp and image/avif to content_type_enum.

    This migration adds support for modern image formats (WebP and AVIF)
    to the content_type_enum used by s3_images table. These formats are
    used for ML-generated visualizations with better compression than JPEG.

    Uses ALTER TYPE ADD VALUE which is:
    - Idempotent (IF NOT EXISTS clause)
    - Non-blocking (no table rewrite)
    - Safe for production
    """
    # Add image/webp to content_type_enum (idempotent)
    op.execute("""
        DO $$
        BEGIN
            -- Add image/webp if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'content_type_enum'
                AND e.enumlabel = 'image/webp'
            ) THEN
                ALTER TYPE content_type_enum ADD VALUE 'image/webp';
            END IF;
        END $$;
    """)

    # Add image/avif to content_type_enum (idempotent)
    op.execute("""
        DO $$
        BEGIN
            -- Add image/avif if not exists
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'content_type_enum'
                AND e.enumlabel = 'image/avif'
            ) THEN
                ALTER TYPE content_type_enum ADD VALUE 'image/avif';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove image/webp and image/avif from content_type_enum.

    WARNING: This downgrade is DESTRUCTIVE!
    - Cannot remove enum values in PostgreSQL (requires recreating enum)
    - This will FAIL if any s3_images records use image/webp or image/avif
    - Only safe if no records use these content types

    To properly downgrade:
    1. Ensure no s3_images use image/webp or image/avif
    2. Manually recreate enum without these values
    3. Re-create column with new enum

    For production: DO NOT DOWNGRADE. Keep enum values for compatibility.
    """
    # PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the enum which requires:
    # 1. Add new enum type without webp/avif
    # 2. Alter column to use new enum
    # 3. Drop old enum
    # This is dangerous and not recommended

    # Instead, we'll just log a warning
    op.execute("""
        DO $$
        BEGIN
            RAISE WARNING 'Downgrade not implemented: PostgreSQL does not support removing enum values. To remove image/webp and image/avif, manually recreate content_type_enum.';
        END $$;
    """)
