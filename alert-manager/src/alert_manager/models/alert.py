"""
Alert model and related tables
"""
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String,
    Integer,
    Text,
    JSON,
    ARRAY,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from monitoring_system.models.base import Base, TimestampMixin


class AlertSeverity(str, enum.Enum):
    """Alert severity enumeration"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(Base, TimestampMixin):
    """Alert model"""

    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "idx_alerts_service_unresolved",
            "service_id",
            "resolved_at",
            postgresql_where="resolved_at IS NULL",
        ),
        Index("idx_alerts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_logs: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Notification tracking
    notified_user_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=list, nullable=False)
    telegram_message_ids: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Resolution tracking
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    service: Mapped["Service"] = relationship("Service", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, service_id={self.service_id}, severity={self.severity})>"

    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved"""
        return self.resolved_at is not None

    @property
    def is_critical(self) -> bool:
        """Check if alert is critical"""
        return self.severity == AlertSeverity.CRITICAL.value


class MutedService(Base, TimestampMixin):
    """Muted services (per user)"""

    __tablename__ = "muted_services"
    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="uq_muted_user_service"),
        Index(
            "idx_muted_services_active",
            "user_id",
            "service_id",
            "muted_until",
            postgresql_where="muted_until > NOW()",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    muted_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    muted_by_command: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="muted_services")
    service: Mapped["Service"] = relationship("Service", back_populates="muted_by")

    def __repr__(self) -> str:
        return f"<MutedService(user_id={self.user_id}, service_id={self.service_id}, until={self.muted_until})>"

    @property
    def is_active(self) -> bool:
        """Check if mute is still active"""
        return self.muted_until > datetime.utcnow()


class PendingAlertBatch(Base, TimestampMixin):
    """Pending alert batches for aggregation"""

    __tablename__ = "pending_alert_batches"
    __table_args__ = (Index("idx_pending_batches_expires", "expires_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alert_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<PendingAlertBatch(id={self.id}, batch_key={self.batch_key}, count={len(self.alert_ids)})>"

    @property
    def is_expired(self) -> bool:
        """Check if batch is expired"""
        return self.expires_at <= datetime.utcnow()

    @property
    def alert_count(self) -> int:
        """Get number of alerts in batch"""
        return len(self.alert_ids)


class AlertArchiveConfig(Base, TimestampMixin):
    """Alert archiving configuration per service"""

    __tablename__ = "alert_archive_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    archive_after_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    auto_archive_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<AlertArchiveConfig(service_id={self.service_id}, archive_after={self.archive_after_days})>"


class SystemConfig(Base):
    """System configuration key-value store"""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="NOW()", onupdate="NOW()", nullable=False
    )

    def __repr__(self) -> str:
        return f"<SystemConfig(key={self.key})>"


# Import to resolve forward references
from monitoring_system.models.service import Service
from monitoring_system.models.user import User
from sqlalchemy import Boolean
