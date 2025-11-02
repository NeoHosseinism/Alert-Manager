"""
User repository for user data access
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from monitoring_system.models.user import User, UserServicePermission
from monitoring_system.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Get user by phone number

        Args:
            phone_number: Phone number

        Returns:
            User or None
        """
        result = await self.session.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram user ID

        Args:
            telegram_id: Telegram user ID

        Returns:
            User or None
        """
        result = await self.session.execute(
            select(User).where(User.telegram_user_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self) -> List[User]:
        """
        Get all active users

        Returns:
            List of active users
        """
        result = await self.session.execute(select(User).where(User.is_active == True))
        return list(result.scalars().all())

    async def get_users_by_role(self, role: str) -> List[User]:
        """
        Get users by role

        Args:
            role: User role

        Returns:
            List of users with the role
        """
        result = await self.session.execute(
            select(User).where(User.role == role, User.is_active == True)
        )
        return list(result.scalars().all())

    async def get_users_for_service(self, service_id: int) -> List[User]:
        """
        Get all users with permissions for a service

        Args:
            service_id: Service ID

        Returns:
            List of users
        """
        result = await self.session.execute(
            select(User)
            .join(UserServicePermission)
            .where(
                UserServicePermission.service_id == service_id,
                UserServicePermission.can_receive_alerts == True,
                User.is_active == True,
            )
        )
        return list(result.scalars().all())
