"""Product category repository for product taxonomy data access.

Provides CRUD operations for product category entities.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_category import ProductCategory
from app.repositories.base import AsyncRepository


class ProductCategoryRepository(AsyncRepository[ProductCategory]):
    """Repository for product category database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(ProductCategory, session)

    async def get(self, id: Any) -> ProductCategory | None:
        """Get product category by ID."""
        stmt = select(ProductCategory).where(ProductCategory.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, id: Any, obj_in: dict[str, Any]) -> ProductCategory:
        """Update product category by ID (custom PK column name)."""
        category = await self.get(id)
        if not category:
            raise ValueError(f"ProductCategory {id} not found")

        for field, value in obj_in.items():
            setattr(category, field, value)

        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, id: Any) -> bool:
        """Delete product category by ID (custom PK column name)."""
        category = await self.get(id)
        if category:
            await self.session.delete(category)
            await self.session.flush()
            return True
        return False
