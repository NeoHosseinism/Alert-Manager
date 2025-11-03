"""
Report model and related tables
"""
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Integer, Boolean, DateTime, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class ReportFrequency(str, enum.Enum):
    """Report frequency enumeration"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportSchedule(Base, TimestampMixin):
    """Report schedule model"""

    __tablename__ = "report_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)

    # Jalali calendar fields (for specific scheduling)
    jalali_day_of_week: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 0=Shanbeh, 6=Jomeh
    jalali_day_of_month: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1-31
    jalali_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-12

    # Target users
    target_user_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=list, nullable=False)

    # Scheduling info
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<ReportSchedule(id={self.id}, name={self.name}, frequency={self.frequency})>"

    @property
    def is_due(self) -> bool:
        """Check if report is due to run"""
        if not self.is_active:
            return False

        if self.next_run_at is None:
            return True

        return self.next_run_at <= datetime.utcnow()
