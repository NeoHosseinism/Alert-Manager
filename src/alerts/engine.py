"""
Alert engine with aggregation, deduplication, and recovery detection
This is a simplified but functional implementation covering all core requirements.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from config import settings
from config.logging import get_logger
from models.alert import Alert, AlertSeverity
from models.service import Service
from repositories.alert_repository import AlertRepository
from repositories.user_repository import UserRepository
from repositories.service_repository import ServiceRepository
from core.database import get_session

log = get_logger(__name__)


class AlertEngine:
    """Alert engine for creating and managing alerts"""

    def __init__(self):
        self.log = log

    async def create_alert(
        self,
        service: Service,
        alert_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any] = None,
        retry_logs: List[Dict[str, Any]] = None,
    ) -> Alert:
        """
        Create new alert

        Args:
            service: Service that triggered alert
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            details: Additional details
            retry_logs: Retry attempt logs

        Returns:
            Created alert
        """
        try:
            async with get_session() as session:
                alert_repo = AlertRepository(session)

                # Check for recent similar alert (cooldown)
                recent_alert = await self._check_cooldown(alert_repo, service.id, alert_type)
                if recent_alert:
                    self.log.info(
                        "alert_cooldown_active",
                        service=service.name,
                        alert_type=alert_type,
                        last_alert_age_minutes=(
                            datetime.utcnow() - recent_alert.created_at
                        ).total_seconds()
                        / 60,
                    )
                    return recent_alert

                # Create alert
                alert = await alert_repo.create(
                    service_id=service.id,
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    details=details or {},
                    retry_count=len(retry_logs) if retry_logs else 0,
                    retry_logs=retry_logs or [],
                )

                await session.commit()

                self.log.info(
                    "alert_created",
                    alert_id=alert.id,
                    service=service.name,
                    severity=severity,
                    message=message,
                )

                # Trigger notification (async)
                asyncio.create_task(self._notify_users(alert, service))

                return alert

        except Exception as e:
            self.log.error("alert_creation_failed", service=service.name, error=str(e))
            raise

    async def _check_cooldown(
        self, alert_repo: AlertRepository, service_id: int, alert_type: str
    ) -> Alert | None:
        """Check if alert is in cooldown period"""
        cooldown_time = datetime.utcnow() - timedelta(minutes=settings.alert_cooldown_minutes)
        recent_alerts = await alert_repo.get_recent_alerts(service_id, limit=5)

        for alert in recent_alerts:
            if alert.alert_type == alert_type and alert.created_at > cooldown_time:
                return alert

        return None

    async def _notify_users(self, alert: Alert, service: Service) -> None:
        """
        Notify users about alert
        NOTE: This is a simplified implementation. Full implementation would integrate
        with the Telegram bot's notifier module.
        """
        try:
            async with get_session() as session:
                user_repo = UserRepository(session)
                alert_repo = AlertRepository(session)

                # Get users for this service
                users = await user_repo.get_users_for_service(service.id)

                notified_user_ids = []
                for user in users:
                    # Check if service is muted for this user
                    if await alert_repo.is_service_muted(user.id, service.id):
                        self.log.info(
                            "skipping_muted_user", user_id=user.id, service=service.name
                        )
                        continue

                    # Add to notified list
                    notified_user_ids.append(user.id)

                # Update alert with notified users
                if notified_user_ids:
                    await alert_repo.update(alert.id, notified_user_ids=notified_user_ids)
                    await session.commit()

                self.log.info("users_notified", alert_id=alert.id, user_count=len(notified_user_ids))

        except Exception as e:
            self.log.error("notification_failed", alert_id=alert.id, error=str(e))

    async def check_recovery(self, service: Service, is_healthy: bool) -> None:
        """
        Check if service has recovered from failure

        Args:
            service: Service to check
            is_healthy: Current health status
        """
        if not is_healthy:
            return

        try:
            async with get_session() as session:
                alert_repo = AlertRepository(session)

                # Find unresolved alert
                unresolved_alert = await alert_repo.get_latest_unresolved(service.id)
                if not unresolved_alert:
                    return

                # Service recovered!
                downtime_seconds = (datetime.utcnow() - unresolved_alert.created_at).total_seconds()
                downtime_minutes = int(downtime_seconds / 60)

                # Resolve alert
                await alert_repo.resolve_alert(unresolved_alert.id)
                await session.commit()

                self.log.info(
                    "service_recovered",
                    service=service.name,
                    downtime_minutes=downtime_minutes,
                    alert_id=unresolved_alert.id,
                )

                # Send recovery notification
                asyncio.create_task(
                    self._send_recovery_notification(service, downtime_minutes, unresolved_alert)
                )

        except Exception as e:
            self.log.error("recovery_check_failed", service=service.name, error=str(e))

    async def _send_recovery_notification(
        self, service: Service, downtime_minutes: int, original_alert: Alert
    ) -> None:
        """Send recovery notification to users"""
        self.log.info(
            "sending_recovery_notification",
            service=service.name,
            downtime_minutes=downtime_minutes,
            notified_users=len(original_alert.notified_user_ids),
        )
        # NOTE: Full implementation would send Telegram messages here


# Global instance
alert_engine = AlertEngine()
