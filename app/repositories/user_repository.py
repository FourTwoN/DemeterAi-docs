"""User repository for authentication and authorization data access.

Provides CRUD operations for user entities.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import AsyncRepository


class UserRepository(AsyncRepository[User]):
    """Repository for user database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(User, session)
