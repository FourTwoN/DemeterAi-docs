"""Product repository for plant species data access.

Provides CRUD operations for product entities.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base import AsyncRepository


class ProductRepository(AsyncRepository[Product]):
    """Repository for product database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Product, session)

    async def get(self, product_id: int) -> Product | None:
        """Get product by ID (overrides base to use product_id)."""
        stmt = select(self.model).where(self.model.product_id == product_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, product_id: int, obj_in: dict[str, Any]) -> Product:
        """Update product by ID (overrides base to use product_id)."""
        product = await self.get(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        for field, value in obj_in.items():
            setattr(product, field, value)

        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def delete(self, product_id: int) -> bool:
        """Delete product by ID (overrides base to use product_id)."""
        product = await self.get(product_id)
        if not product:
            return False

        await self.session.delete(product)
        await self.session.flush()
        return True
