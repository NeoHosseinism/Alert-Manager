"""
Service repository for service data access
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.service import Service, HealthCheck
from models.user import UserServicePermission
from repositories.base_repository import BaseRepository


class ServiceRepository(BaseRepository[Service]):
    """Repository for Service model"""

    def __init__(self, session: AsyncSession):
        super().__init__(Service, session)

    async def get_by_name(self, name: str, environment: Optional[str] = None) -> Optional[Service]:
        """
        Get service by name and optional environment

        Args:
            name: Service name
            environment: Environment (optional)

        Returns:
            Service or None
        """
        query = select(Service).where(Service.name == name)
        if environment:
            query = query.where(Service.environment == environment)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_services(self, environment: Optional[str] = None) -> List[Service]:
        """
        Get all active services

        Args:
            environment: Filter by environment (optional)

        Returns:
            List of active services
        """
        query = select(Service).where(Service.is_active == True)
        if environment:
            query = query.where(Service.environment == environment)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_services_by_type(
        self, service_type: str, environment: Optional[str] = None
    ) -> List[Service]:
        """
        Get services by type

        Args:
            service_type: Service type (health_check, api_credit)
            environment: Filter by environment (optional)

        Returns:
            List of services
        """
        query = select(Service).where(Service.service_type == service_type, Service.is_active == True)
        if environment:
            query = query.where(Service.environment == environment)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_services(self, user_id: int) -> List[Service]:
        """
        Get services accessible to a user

        Args:
            user_id: User ID

        Returns:
            List of services
        """
        result = await self.session.execute(
            select(Service)
            .join(UserServicePermission)
            .where(
                UserServicePermission.user_id == user_id,
                Service.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_latest_health_check(self, service_id: int) -> Optional[HealthCheck]:
        """
        Get latest health check for a service

        Args:
            service_id: Service ID

        Returns:
            Latest health check or None
        """
        result = await self.session.execute(
            select(HealthCheck)
            .where(HealthCheck.service_id == service_id)
            .order_by(HealthCheck.checked_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_health_check(
        self,
        service_id: int,
        is_healthy: bool,
        response_time_ms: Optional[int] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> HealthCheck:
        """
        Create a health check record

        Args:
            service_id: Service ID
            is_healthy: Whether service is healthy
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            error_message: Error message if failed

        Returns:
            Created health check
        """
        health_check = HealthCheck(
            service_id=service_id,
            is_healthy=is_healthy,
            response_time_ms=response_time_ms,
            status_code=status_code,
            error_message=error_message,
            checked_at=datetime.utcnow(),
        )
        self.session.add(health_check)
        await self.session.flush()
        await self.session.refresh(health_check)
        return health_check
