"""
Custom exceptions for the monitoring system
"""


class MonitoringSystemException(Exception):
    """Base exception for monitoring system"""

    pass


class DatabaseException(MonitoringSystemException):
    """Database-related exceptions"""

    pass


class HealthCheckException(MonitoringSystemException):
    """Health check failures"""

    pass


class CreditCheckException(MonitoringSystemException):
    """Credit check failures"""

    pass


class AlertException(MonitoringSystemException):
    """Alert processing exceptions"""

    pass


class TelegramException(MonitoringSystemException):
    """Telegram bot exceptions"""

    pass


class AuthenticationException(TelegramException):
    """User authentication failures"""

    pass


class PermissionException(TelegramException):
    """Permission/authorization failures"""

    pass


class EncryptionException(MonitoringSystemException):
    """Encryption/decryption failures"""

    pass


class ValidationException(MonitoringSystemException):
    """Validation failures"""

    pass


class ReportException(MonitoringSystemException):
    """Report generation exceptions"""

    pass
