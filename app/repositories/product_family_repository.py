"""Product family repository for plant family taxonomy data access.

Provides CRUD operations for product family entities.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_family import ProductFamily
from app.repositories.base import AsyncRepository


class ProductFamilyRepository(AsyncRepository[ProductFamily]):
    """Repository for product family database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(ProductFamily, session)

    async def get(self, id: Any) -> ProductFamily | None:
        """Get product family by ID (custom PK column name)."""
        stmt = select(ProductFamily).where(ProductFamily.family_id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, id: Any, obj_in: dict[str, Any]) -> ProductFamily:
        """Update product family by ID (custom PK column name)."""
        family = await self.get(id)
        if not family:
            raise ValueError(f"ProductFamily {id} not found")

        for field, value in obj_in.items():
            setattr(family, field, value)

        await self.session.flush()
        await self.session.refresh(family)
        return family

    async def delete(self, id: Any) -> None:
        """Delete product family by ID (custom PK column name)."""
        family = await self.get(id)
        if family:
            await self.session.delete(family)
            await self.session.flush()
