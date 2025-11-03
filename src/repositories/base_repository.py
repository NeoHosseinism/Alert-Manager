"""
Base repository with common CRUD operations
"""
from typing import Generic, TypeVar, Type, List, Optional, Any, Dict
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository for common database operations"""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository

        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get entity by ID

        Args:
            id: Entity ID

        Returns:
            Entity or None if not found
        """
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[ModelType]:
        """
        Get all entities

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of entities
        """
        query = select(self.model).offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """
        Create new entity

        Args:
            **kwargs: Entity attributes

        Returns:
            Created entity
        """
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Update entity by ID

        Args:
            id: Entity ID
            **kwargs: Attributes to update

        Returns:
            Updated entity or None if not found
        """
        stmt = update(self.model).where(self.model.id == id).values(**kwargs).returning(self.model)

        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        """
        Delete entity by ID

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def exists(self, **filters) -> bool:
        """
        Check if entity exists with given filters

        Args:
            **filters: Filter criteria

        Returns:
            True if exists, False otherwise
        """
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none() is not None

    async def count(self, **filters) -> int:
        """
        Count entities with given filters

        Args:
            **filters: Filter criteria

        Returns:
            Count of matching entities
        """
        from sqlalchemy import func

        query = select(func.count(self.model.id))
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalar_one()
