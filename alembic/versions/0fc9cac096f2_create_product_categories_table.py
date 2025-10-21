"""create product_categories table

Revision ID: 0fc9cac096f2
Revises: 4ab9c2d8e5fg
Create Date: 2025-10-14 11:07:27.121880

"""
from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fc9cac096f2'
down_revision: Union[str, None] = '4ab9c2d8e5fg'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create product_categories table with 8 seed categories."""
    # Create table
    op.create_table(
        'product_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='Primary key (auto-increment)'),
        sa.Column('code', sa.String(length=50), nullable=False, comment='Unique category code (uppercase, alphanumeric + underscores, 3-50 chars)'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='Human-readable category name'),
        sa.Column('description', sa.Text(), nullable=True, comment='Optional detailed description'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_product_categories')),
        sa.UniqueConstraint('code', name=op.f('uq_product_categories_code')),
        sa.CheckConstraint('LENGTH(code) >= 3 AND LENGTH(code) <= 50', name='ck_product_category_code_length'),
        comment='Product Categories - ROOT taxonomy table (Category → Family → Product)'
    )

    # Create indexes
    op.create_index(op.f('ix_product_categories_code'), 'product_categories', ['code'], unique=False)

    # Insert 8 seed categories
    op.execute("""
        INSERT INTO product_categories (code, name, description) VALUES
        ('CACTUS', 'Cactus', 'Cacti family (Cactaceae) - succulent plants with spines'),
        ('SUCCULENT', 'Succulent', 'Non-cactus succulents - thick fleshy leaves, drought-tolerant'),
        ('BROMELIAD', 'Bromeliad', 'Bromeliaceae family - epiphytic tropical plants'),
        ('CARNIVOROUS', 'Carnivorous Plant', 'Insectivorous plants (Venus flytrap, pitcher plants, etc.)'),
        ('ORCHID', 'Orchid', 'Orchidaceae family - epiphytic flowering plants'),
        ('FERN', 'Fern', 'Ferns and fern allies - non-flowering vascular plants'),
        ('TROPICAL', 'Tropical Plant', 'General tropical foliage plants (Monstera, Philodendron, etc.)'),
        ('HERB', 'Herb', 'Culinary and medicinal herbs (basil, mint, rosemary, etc.)');
    """)


def downgrade() -> None:
    """Drop product_categories table."""
    op.drop_index(op.f('ix_product_categories_code'), table_name='product_categories')
    op.drop_table('product_categories')
