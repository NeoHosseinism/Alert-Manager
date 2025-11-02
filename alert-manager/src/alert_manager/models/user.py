"""
User model and related tables
"""
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, BigInteger, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from monitoring_system.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """User role enumeration"""

    VIEWER = "viewer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(Base, TimestampMixin):
    """User model"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True
    )
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    permissions: Mapped[List["UserServicePermission"]] = relationship(
        "UserServicePermission", back_populates="user", cascade="all, delete-orphan"
    )
    muted_services: Mapped[List["MutedService"]] = relationship(
        "MutedService", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone={self.phone_number}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin or super admin"""
        return self.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]

    @property
    def is_super_admin(self) -> bool:
        """Check if user is super admin"""
        return self.role == UserRole.SUPER_ADMIN.value


class UserServicePermission(Base, TimestampMixin):
    """User service permissions (many-to-many)"""

    __tablename__ = "user_service_permissions"
    __table_args__ = (UniqueConstraint("user_id", "service_id", name="uq_user_service"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    can_receive_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_mute: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="permissions")
    service: Mapped["Service"] = relationship("Service", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<UserServicePermission(user_id={self.user_id}, service_id={self.service_id})>"
