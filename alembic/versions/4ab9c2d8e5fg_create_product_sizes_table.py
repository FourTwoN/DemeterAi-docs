"""create_product_sizes_table

Revision ID: 4ab9c2d8e5fg
Revises: 3xy8k1m9n4pq
Create Date: 2025-10-14 16:55:00.000000

Creates the product_sizes reference/catalog table with:
- Table with all fields (code, name, description, min_height_cm, max_height_cm, sort_order)
- CHECK constraint: Code length 3-50 characters
- Indexes: code (UK), sort_order
- SEED DATA: 7 size categories (XS → XXL, CUSTOM)

This is a SIMPLE reference table (no enums, no PostGIS, no triggers).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = '4ab9c2d8e5fg'
down_revision: Union[str, None] = '3xy8k1m9n4pq'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Create product_sizes table with seed data."""

  # Create product_sizes table
  op.create_table(
      'product_sizes',
      sa.Column('product_size_id', sa.Integer(), autoincrement=True,
                nullable=False, comment='Primary key (auto-increment)'),
      sa.Column('code', sa.String(length=50), nullable=False,
                comment='Unique size code (uppercase, alphanumeric + underscores, 3-50 chars)'),
      sa.Column('name', sa.String(length=200), nullable=False,
                comment='Human-readable size name'),
      sa.Column('description', sa.Text(), nullable=True,
                comment='Optional detailed description'),
      sa.Column('min_height_cm', sa.Numeric(precision=6, scale=2),
                nullable=True, comment='Minimum height in cm (nullable)'),
      sa.Column('max_height_cm', sa.Numeric(precision=6, scale=2),
                nullable=True, comment='Maximum height in cm (nullable)'),
      sa.Column('sort_order', sa.Integer(), server_default='99', nullable=False,
                comment='UI dropdown order (size progression)'),
      sa.Column('created_at', sa.DateTime(timezone=True),
                server_default=sa.text('now()'), nullable=False,
                comment='Record creation timestamp'),
      sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                comment='Last update timestamp'),
      sa.CheckConstraint("LENGTH(code) >= 1 AND LENGTH(code) <= 50",
                         name='ck_product_size_code_length'),
      # Changed from 3 to 1 to allow 'XS', 'S', 'M', 'L' codes
      sa.PrimaryKeyConstraint('product_size_id'),
      sa.UniqueConstraint('code'),
      comment='Product Sizes - Reference/catalog table defining product size categories'
  )

  # Create indexes
  op.create_index('ix_product_sizes_code', 'product_sizes', ['code'],
                  unique=True)
  op.create_index('ix_product_sizes_sort_order', 'product_sizes',
                  ['sort_order'], unique=False)

  # Insert seed data (7 size categories)
  op.execute("""
             INSERT INTO product_sizes (code, name, description, min_height_cm,
                                        max_height_cm, sort_order)
             VALUES

                 -- STANDARD SIZES (with height ranges)
                 ('XS', 'Extra Small (0-5cm)',
                  'Extra small plants, 0-5cm height', 0.00, 5.00, 10),
                 ('S', 'Small (5-10cm)', 'Small plants, 5-10cm height', 5.00,
                  10.00, 20),
                 ('M', 'Medium (10-20cm)', 'Medium plants, 10-20cm height',
                  10.00, 20.00, 30),
                 ('L', 'Large (20-40cm)', 'Large plants, 20-40cm height', 20.00,
                  40.00, 40),
                 ('XL', 'Extra Large (40-80cm)',
                  'Extra large plants, 40-80cm height', 40.00, 80.00, 50),
                 ('XXL', 'Extra Extra Large (80+cm)',
                  'Extra extra large plants, 80cm and above (no max)', 80.00,
                  NULL, 60),

                 -- SPECIAL SIZE (no height range)
                 ('CUSTOM', 'Custom Size (no fixed range)',
                  'Custom size with no fixed height range', NULL, NULL, 99);
             """)


def downgrade() -> None:
  """Drop product_sizes table."""

  # Drop indexes
  op.drop_index('ix_product_sizes_sort_order', table_name='product_sizes')
  op.drop_index('ix_product_sizes_code', table_name='product_sizes')

  # Drop table
  op.drop_table('product_sizes')
