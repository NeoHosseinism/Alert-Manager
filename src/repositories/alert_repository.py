"""
Alert repository for alert data access
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.alert import Alert, MutedService, PendingAlertBatch
from repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    """Repository for Alert model"""

    def __init__(self, session: AsyncSession):
        super().__init__(Alert, session)

    async def get_latest_unresolved(self, service_id: int) -> Optional[Alert]:
        """
        Get latest unresolved alert for a service

        Args:
            service_id: Service ID

        Returns:
            Latest unresolved alert or None
        """
        result = await self.session.execute(
            select(Alert)
            .where(Alert.service_id == service_id, Alert.resolved_at.is_(None))
            .order_by(Alert.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_recent_alerts(
        self, service_id: Optional[int] = None, limit: int = 10
    ) -> List[Alert]:
        """
        Get recent alerts

        Args:
            service_id: Filter by service (optional)
            limit: Maximum number of alerts

        Returns:
            List of recent alerts
        """
        query = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
        if service_id:
            query = query.where(Alert.service_id == service_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_alerts(self, user_id: int, limit: int = 10) -> List[Alert]:
        """
        Get alerts for user's services

        Args:
            user_id: User ID
            limit: Maximum number of alerts

        Returns:
            List of alerts
        """
        result = await self.session.execute(
            select(Alert)
            .where(Alert.notified_user_ids.any(user_id))
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_alerts_by_timerange(
        self, service_id: int, start_date: datetime, end_date: datetime
    ) -> List[Alert]:
        """
        Get alerts within a time range

        Args:
            service_id: Service ID
            start_date: Start datetime
            end_date: End datetime

        Returns:
            List of alerts
        """
        result = await self.session.execute(
            select(Alert)
            .where(
                Alert.service_id == service_id,
                Alert.created_at >= start_date,
                Alert.created_at <= end_date,
            )
            .order_by(Alert.created_at.desc())
        )
        return list(result.scalars().all())

    async def resolve_alert(self, alert_id: int) -> Optional[Alert]:
        """
        Mark alert as resolved

        Args:
            alert_id: Alert ID

        Returns:
            Updated alert or None
        """
        return await self.update(alert_id, resolved_at=datetime.utcnow())

    async def is_service_muted(self, user_id: int, service_id: int) -> bool:
        """
        Check if service is muted for user

        Args:
            user_id: User ID
            service_id: Service ID

        Returns:
            True if muted, False otherwise
        """
        result = await self.session.execute(
            select(MutedService).where(
                MutedService.user_id == user_id,
                MutedService.service_id == service_id,
                MutedService.muted_until > datetime.utcnow(),
            )
        )
        return result.scalar_one_or_none() is not None

    async def mute_service(
        self, user_id: int, service_id: int, muted_until: datetime, command: str = "/mute"
    ) -> MutedService:
        """
        Mute service for user

        Args:
            user_id: User ID
            service_id: Service ID
            muted_until: Mute until datetime
            command: Command that triggered mute

        Returns:
            Created muted service record
        """
        # Delete existing mute if any
        await self.session.execute(
            select(MutedService).where(
                MutedService.user_id == user_id,
                MutedService.service_id == service_id,
            )
        )

        muted = MutedService(
            user_id=user_id,
            service_id=service_id,
            muted_until=muted_until,
            muted_by_command=command,
        )
        self.session.add(muted)
        await self.session.flush()
        await self.session.refresh(muted)
        return muted

    async def unmute_service(self, user_id: int, service_id: int) -> bool:
        """
        Unmute service for user

        Args:
            user_id: User ID
            service_id: Service ID

        Returns:
            True if unmuted, False if not found
        """
        from sqlalchemy import delete

        stmt = delete(MutedService).where(
            MutedService.user_id == user_id,
            MutedService.service_id == service_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def get_muted_services(self, user_id: int) -> List[MutedService]:
        """
        Get all muted services for user

        Args:
            user_id: User ID

        Returns:
            List of muted services
        """
        result = await self.session.execute(
            select(MutedService)
            .where(
                MutedService.user_id == user_id,
                MutedService.muted_until > datetime.utcnow(),
            )
            .order_by(MutedService.muted_until)
        )
        return list(result.scalars().all())
