"""create product_families table

Revision ID: 1a2b3c4d5e6f
Revises: 0fc9cac096f2
Create Date: 2025-10-14 13:05:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, None] = '0fc9cac096f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Create product_families table with 18 seed families across 8 categories."""
  # Create table
  op.create_table(
      'product_families',
      sa.Column('family_id', sa.Integer(), autoincrement=True, nullable=False,
                comment='Primary key (auto-increment)'),
      sa.Column('category_id', sa.Integer(), nullable=False,
                comment='Foreign key to product_categories (CASCADE delete)'),
      sa.Column('name', sa.String(length=200), nullable=False,
                comment='Human-readable family name (e.g., Echeveria, Aloe)'),
      sa.Column('scientific_name', sa.String(length=200), nullable=True,
                comment='Optional botanical/scientific name'),
      sa.Column('description', sa.Text(), nullable=True,
                comment='Optional detailed description'),
      sa.PrimaryKeyConstraint('family_id', name=op.f('pk_product_families')),
      sa.ForeignKeyConstraint(['category_id'], ['product_categories.id'],
                              name=op.f(
                                  'fk_product_families_category_id_product_categories'),
                              ondelete='CASCADE'),
      comment='Product Families - LEVEL 2 taxonomy (Category → Family → Product)'
  )

  # Create indexes
  op.create_index(op.f('ix_product_families_category_id'), 'product_families',
                  ['category_id'], unique=False)

  # Insert 18 seed families across 8 categories
  # First, get category IDs
  op.execute("""
             -- CACTUS category (4 families)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Echeveria',
                    'Echeveria',
                    'Small rosette-forming succulents native to Mexico and Central America'
             FROM product_categories
             WHERE code = 'CACTUS'
             UNION ALL
             SELECT id,
                    'Mammillaria',
                    'Mammillaria',
                    'Globular cacti with prominent tubercles and colorful flowers'
             FROM product_categories
             WHERE code = 'CACTUS'
             UNION ALL
             SELECT id,
                    'Opuntia',
                    'Opuntia',
                    'Pad-forming cacti (prickly pear) with flat stem segments'
             FROM product_categories
             WHERE code = 'CACTUS'
             UNION ALL
             SELECT id,
                    'Echinocactus',
                    'Echinocactus',
                    'Large barrel-shaped cacti native to Mexico and southwestern United States'
             FROM product_categories
             WHERE code = 'CACTUS';
             """)

  op.execute("""
             -- SUCCULENT category (4 families)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Aloe',
                    'Aloe',
                    'Succulent plants with thick fleshy leaves arranged in rosettes'
             FROM product_categories
             WHERE code = 'SUCCULENT'
             UNION ALL
             SELECT id,
                    'Haworthia',
                    'Haworthia',
                    'Small succulent plants with distinctive striped or warty leaves'
             FROM product_categories
             WHERE code = 'SUCCULENT'
             UNION ALL
             SELECT id,
                    'Crassula',
                    'Crassula',
                    'Diverse genus of succulents including jade plants'
             FROM product_categories
             WHERE code = 'SUCCULENT'
             UNION ALL
             SELECT id,
                    'Sedum',
                    'Sedum',
                    'Ground-covering succulents with star-shaped flowers'
             FROM product_categories
             WHERE code = 'SUCCULENT';
             """)

  op.execute("""
             -- BROMELIAD category (3 families)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Tillandsia',
                    'Tillandsia',
                    'Air plants that absorb water and nutrients through their leaves'
             FROM product_categories
             WHERE code = 'BROMELIAD'
             UNION ALL
             SELECT id,
                    'Guzmania',
                    'Guzmania',
                    'Colorful bromeliads with bright flower bracts'
             FROM product_categories
             WHERE code = 'BROMELIAD'
             UNION ALL
             SELECT id,
                    'Aechmea',
                    'Aechmea',
                    'Bromeliads with spiky foliage and long-lasting flower spikes'
             FROM product_categories
             WHERE code = 'BROMELIAD';
             """)

  op.execute("""
             -- CARNIVOROUS category (2 families)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Nepenthes',
                    'Nepenthes',
                    'Tropical pitcher plants with hanging traps'
             FROM product_categories
             WHERE code = 'CARNIVOROUS'
             UNION ALL
             SELECT id,
                    'Dionaea',
                    'Dionaea',
                    'Venus flytrap - iconic snap-trap carnivorous plant'
             FROM product_categories
             WHERE code = 'CARNIVOROUS';
             """)

  op.execute("""
             -- ORCHID category (2 families)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Phalaenopsis',
                    'Phalaenopsis',
                    'Moth orchids with long-lasting elegant flowers'
             FROM product_categories
             WHERE code = 'ORCHID'
             UNION ALL
             SELECT id,
                    'Cattleya',
                    'Cattleya',
                    'Large showy orchids with fragrant flowers'
             FROM product_categories
             WHERE code = 'ORCHID';
             """)

  op.execute("""
             -- FERN category (1 family)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Nephrolepis',
                    'Nephrolepis',
                    'Boston ferns and relatives with feathery fronds'
             FROM product_categories
             WHERE code = 'FERN';
             """)

  op.execute("""
             -- TROPICAL category (1 family)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Monstera',
                    'Monstera',
                    'Large tropical plants with distinctive split leaves'
             FROM product_categories
             WHERE code = 'TROPICAL';
             """)

  op.execute("""
             -- HERB category (1 family)
             INSERT INTO product_families (category_id, name, scientific_name, description)
             SELECT id,
                    'Mentha',
                    'Mentha',
                    'Mint family - aromatic herbs used in cooking and medicine'
             FROM product_categories
             WHERE code = 'HERB';
             """)


def downgrade() -> None:
  """Drop product_families table."""
  op.drop_index(op.f('ix_product_families_category_id'),
                table_name='product_families')
  op.drop_table('product_families')
