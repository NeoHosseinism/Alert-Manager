"""
Application settings with Pydantic v2
"""
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["dev", "stage", "prod"] = Field(default="prod")
    debug: bool = Field(default=False)

    # Database
    database_url: str = Field(..., description="PostgreSQL connection string")
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    database_pool_recycle: int = Field(default=3600, description="Recycle connections after N seconds")
    database_echo: bool = Field(default=False, description="Echo SQL queries")

    # Telegram Bots
    telegram_main_bot_token: str = Field(..., description="Main bot token for stage/prod")
    telegram_main_bot_username: str = Field(..., description="Main bot username")
    telegram_sandbox_bot_token: str = Field(..., description="Sandbox bot token for dev")
    telegram_sandbox_bot_username: str = Field(..., description="Sandbox bot username")

    # Encryption
    encryption_key: str = Field(..., description="Fernet key for API key encryption")

    # Monitoring Defaults
    default_health_check_interval: int = Field(default=300, description="Seconds")
    default_health_check_timeout: int = Field(default=10, description="Seconds")
    default_max_retries: int = Field(default=3)
    default_retry_delay: int = Field(default=30, description="Seconds")

    # Alert Settings
    alert_aggregation_window: int = Field(default=120, description="Seconds (2 minutes)")
    alert_cooldown_minutes: int = Field(default=30)
    alert_batch_flush_count: int = Field(default=10, description="Flush batch after N alerts")
    alert_critical_batch_count: int = Field(default=5, description="Flush critical alerts after N")

    # Credit Monitoring
    openrouter_api_url: str = Field(default="https://openrouter.ai/api/v1")
    default_credit_threshold: float = Field(default=20.00)
    default_credit_check_interval: int = Field(default=24, description="Hours")

    # Reporting
    report_chart_dpi: int = Field(default=150)
    report_chart_style: str = Field(default="seaborn-v0_8-whitegrid")
    report_font_family: str = Field(default="DejaVu Sans")
    report_time_hour: int = Field(default=9, description="Hour to send reports (0-23)")
    enable_daily_reports: bool = Field(default=True)
    enable_weekly_reports: bool = Field(default=True)
    enable_monthly_reports: bool = Field(default=True)

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")

    # Archiving
    default_archive_after_days: int = Field(default=365)

    # Scheduler
    scheduler_timezone: str = Field(default="UTC")
    scheduler_job_defaults: dict = Field(
        default={
            "coalesce": True,
            "max_instances": 3,
            "misfire_grace_time": 300,
        }
    )

    @property
    def is_dev(self) -> bool:
        """Check if running in development mode"""
        return self.environment == "dev"

    @property
    def is_stage(self) -> bool:
        """Check if running in staging mode"""
        return self.environment == "stage"

    @property
    def is_prod(self) -> bool:
        """Check if running in production mode"""
        return self.environment == "prod"

    @property
    def should_show_full_errors(self) -> bool:
        """Whether to show full error messages"""
        return self.environment == "dev"

    @property
    def active_bot_token(self) -> str:
        """Get the active bot token based on environment"""
        return self.telegram_sandbox_bot_token if self.is_dev else self.telegram_main_bot_token

    @property
    def active_bot_username(self) -> str:
        """Get the active bot username based on environment"""
        return (
            self.telegram_sandbox_bot_username
            if self.is_dev
            else self.telegram_main_bot_username
        )

    @field_validator("database_pool_size")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """Validate database pool size"""
        if v < 1:
            raise ValueError("Pool size must be at least 1")
        if v > 100:
            raise ValueError("Pool size should not exceed 100")
        return v

    @field_validator("alert_aggregation_window")
    @classmethod
    def validate_aggregation_window(cls, v: int) -> int:
        """Validate alert aggregation window"""
        if v < 30:
            raise ValueError("Aggregation window must be at least 30 seconds")
        if v > 600:
            raise ValueError("Aggregation window should not exceed 600 seconds")
        return v


# Create global settings instance
settings = Settings()
