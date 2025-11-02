"""
Health checker with retry logic for monitoring service endpoints
"""
import time
import asyncio
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import httpx
from monitoring_system.config import settings
from monitoring_system.config.logging import get_logger
from monitoring_system.models.service import Service
from monitoring_system.repositories.service_repository import ServiceRepository
from monitoring_system.core.database import get_session
from monitoring_system.utils.retry import async_retry

log = get_logger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check"""

    success: bool
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    retry_logs: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.retry_logs is None:
            self.retry_logs = []


class HealthChecker:
    """Health checker for monitoring service endpoints"""

    def __init__(self):
        self.log = log

    async def check_service(self, service: Service) -> HealthCheckResult:
        """
        Check service health with retry logic

        Args:
            service: Service to check

        Returns:
            Health check result
        """
        retry_logs = []

        for attempt in range(service.max_retries):
            try:
                result = await self._perform_health_check(service)

                if result.success:
                    # Success - store result and check for recovery
                    await self._store_health_check(service.id, result)

                    if retry_logs:
                        self.log.info(
                            "health_check_succeeded_after_retry",
                            service=service.name,
                            attempt=attempt + 1,
                            response_time_ms=result.response_time_ms,
                        )

                    return result

                # Failed - log and retry
                retry_log = {
                    "attempt": attempt + 1,
                    "error": result.error_message or f"Status code: {result.status_code}",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                retry_logs.append(retry_log)

                self.log.warning(
                    "health_check_failed_attempt",
                    service=service.name,
                    attempt=attempt + 1,
                    max_retries=service.max_retries,
                    error=retry_log["error"],
                )

            except Exception as e:
                retry_log = {
                    "attempt": attempt + 1,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                retry_logs.append(retry_log)

                self.log.error(
                    "health_check_exception",
                    service=service.name,
                    attempt=attempt + 1,
                    error=str(e),
                )

            # Wait before retry (except on last attempt)
            if attempt < service.max_retries - 1:
                await asyncio.sleep(service.retry_delay_seconds)

        # All retries failed
        failed_result = HealthCheckResult(
            success=False,
            retry_count=service.max_retries,
            retry_logs=retry_logs,
            error_message=retry_logs[-1]["error"] if retry_logs else "Unknown error",
        )

        await self._store_health_check(service.id, failed_result)

        self.log.error(
            "health_check_failed_all_retries",
            service=service.name,
            max_retries=service.max_retries,
            error=failed_result.error_message,
        )

        return failed_result

    async def _perform_health_check(self, service: Service) -> HealthCheckResult:
        """
        Perform a single health check attempt

        Args:
            service: Service to check

        Returns:
            Health check result
        """
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=service.timeout_seconds) as client:
                response = await client.get(service.endpoint_url)
                response_time_ms = int((time.time() - start_time) * 1000)

                if response.status_code == service.expected_status_code:
                    return HealthCheckResult(
                        success=True,
                        response_time_ms=response_time_ms,
                        status_code=response.status_code,
                    )
                else:
                    return HealthCheckResult(
                        success=False,
                        response_time_ms=response_time_ms,
                        status_code=response.status_code,
                        error_message=f"Unexpected status code: {response.status_code} (expected {service.expected_status_code})",
                    )

        except httpx.TimeoutException as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                success=False,
                response_time_ms=response_time_ms,
                error_message=f"Timeout after {service.timeout_seconds}s",
            )
        except httpx.ConnectError as e:
            return HealthCheckResult(success=False, error_message=f"Connection error: {str(e)}")
        except Exception as e:
            return HealthCheckResult(success=False, error_message=f"Error: {str(e)}")

    async def _store_health_check(self, service_id: int, result: HealthCheckResult) -> None:
        """
        Store health check result in database

        Args:
            service_id: Service ID
            result: Health check result
        """
        try:
            async with get_session() as session:
                repo = ServiceRepository(session)
                await repo.create_health_check(
                    service_id=service_id,
                    is_healthy=result.success,
                    response_time_ms=result.response_time_ms,
                    status_code=result.status_code,
                    error_message=result.error_message,
                )
                await session.commit()
        except Exception as e:
            self.log.error("failed_to_store_health_check", service_id=service_id, error=str(e))

    async def check_all_services(self) -> None:
        """Check all active health check services"""
        try:
            async with get_session() as session:
                repo = ServiceRepository(session)
                services = await repo.get_services_by_type("health_check", settings.environment)

            self.log.info("checking_health_services", count=len(services))

            # Check all services concurrently
            tasks = [self.check_service(service) for service in services]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log summary
            successful = sum(1 for r in results if isinstance(r, HealthCheckResult) and r.success)
            failed = len(results) - successful

            self.log.info(
                "health_check_summary", total=len(results), successful=successful, failed=failed
            )

        except Exception as e:
            self.log.error("health_check_error", error=str(e), exc_info=True)
