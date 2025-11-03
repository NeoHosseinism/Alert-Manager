"""
Service model and related tables
"""
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Integer, Text, Boolean, DECIMAL, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class ServiceType(str, enum.Enum):
    """Service type enumeration"""

    HEALTH_CHECK = "health_check"
    API_CREDIT = "api_credit"


class Environment(str, enum.Enum):
    """Environment enumeration"""

    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"


class Service(Base, TimestampMixin):
    """Service model"""

    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("name", "environment", name="uq_service_name_env"),
        Index("idx_services_active_env", "is_active", "environment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # For health checks
    endpoint_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # For API credits
    api_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credit_threshold: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2), nullable=True)
    credit_check_interval_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)

    # API Tracking Configuration
    # JSON structure: {
    #   "methods": ["key_management", "credits"],  # Which tracking methods to use
    #   "key_management_path": "/api/v1/key",     # Path for detailed usage API
    #   "credits_path": "/api/v1/credits"          # Path for simple credits API
    # }
    api_tracking_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Common settings
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_delay_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    environment: Mapped[str] = mapped_column(String(20), default="prod", nullable=False)
    service_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    permissions: Mapped[List["UserServicePermission"]] = relationship(
        "UserServicePermission", back_populates="service", cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert", back_populates="service", cascade="all, delete-orphan"
    )
    health_checks: Mapped[List["HealthCheck"]] = relationship(
        "HealthCheck", back_populates="service", cascade="all, delete-orphan"
    )
    muted_by: Mapped[List["MutedService"]] = relationship(
        "MutedService", back_populates="service", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name}, type={self.service_type})>"

    @property
    def is_health_check(self) -> bool:
        """Check if service is a health check"""
        return self.service_type == ServiceType.HEALTH_CHECK.value

    @property
    def is_api_credit(self) -> bool:
        """Check if service is an API credit monitor"""
        return self.service_type == ServiceType.API_CREDIT.value


class HealthCheck(Base):
    """Health check results"""

    __tablename__ = "health_checks"
    __table_args__ = (Index("idx_health_checks_service_time", "service_id", "checked_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_healthy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checked_at: Mapped["datetime"] = mapped_column(
        nullable=False, server_default="NOW()", index=True
    )

    # Relationship
    service: Mapped["Service"] = relationship("Service", back_populates="health_checks")

    def __repr__(self) -> str:
        return f"<HealthCheck(id={self.id}, service_id={self.service_id}, healthy={self.is_healthy})>"


# Import UserServicePermission to avoid circular import
from models.user import UserServicePermission
from models.alert import Alert, MutedService
