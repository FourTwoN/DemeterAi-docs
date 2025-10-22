"""create products table

Revision ID: 5gh9j2n4k7lm
Revises: 1a2b3c4d5e6f
Create Date: 2025-10-14 15:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '5gh9j2n4k7lm'
down_revision: Union[str, None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Create products table (NO seed data - products created by users/ML)."""
  # Create table
  op.create_table(
      'products',
      sa.Column(
          'id',
          sa.Integer(),
          autoincrement=True,
          nullable=False,
          comment='Primary key (auto-increment)'
      ),
      sa.Column(
          'family_id',
          sa.Integer(),
          nullable=False,
          comment='Foreign key to product_families (CASCADE delete)'
      ),
      sa.Column(
          'sku',
          sa.String(length=20),
          nullable=False,
          comment='Unique Stock Keeping Unit (6-20 chars, alphanumeric+hyphen, uppercase)'
      ),
      sa.Column(
          'common_name',
          sa.String(length=200),
          nullable=False,
          comment="Human-readable product name (e.g., Echeveria 'Lola')"
      ),
      sa.Column(
          'scientific_name',
          sa.String(length=200),
          nullable=True,
          comment='Optional botanical/scientific name'
      ),
      sa.Column(
          'description',
          sa.Text(),
          nullable=True,
          comment='Optional detailed description'
      ),
      sa.Column(
          'custom_attributes',
          JSONB,
          nullable=True,
          server_default='{}',
          comment='Flexible metadata (color, variegation, growth_rate, etc.)'
      ),
      sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
      sa.ForeignKeyConstraint(
          ['family_id'],
          ['product_families.family_id'],
          name=op.f('fk_products_family_id_product_families'),
          ondelete='CASCADE'
      ),
      sa.UniqueConstraint('sku', name=op.f('uq_products_sku')),
      sa.CheckConstraint(
          'LENGTH(sku) >= 6 AND LENGTH(sku) <= 20',
          name='ck_product_sku_length'
      ),
      sa.CheckConstraint(
          "sku ~ '^[A-Z0-9-]+$'",
          name='ck_product_sku_format'
      ),
      comment='Products - LEAF taxonomy (Category → Family → Product). NO seed data.'
  )

  # Create indexes
  op.create_index(
      op.f('ix_products_family_id'),
      'products',
      ['family_id'],
      unique=False
  )
  op.create_index(
      op.f('ix_products_sku'),
      'products',
      ['sku'],
      unique=True
  )

  # Create GIN index on JSONB column for efficient queries
  op.execute("""
             CREATE INDEX ix_products_custom_attributes
                 ON products USING GIN (custom_attributes);
             """)

  # NO seed data: Products are created by users/ML pipeline (NOT preloaded)
  # This differs from ProductCategory (8 seed categories) and ProductFamily (18 seed families)


def downgrade() -> None:
  """Drop products table."""
  op.execute('DROP INDEX IF EXISTS ix_products_custom_attributes;')
  op.drop_index(op.f('ix_products_sku'), table_name='products')
  op.drop_index(op.f('ix_products_family_id'), table_name='products')
  op.drop_table('products')
