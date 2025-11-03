"""
API credit monitoring with support for OpenRouter and extensible for other providers
"""
import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
from config import settings
from config.logging import get_logger
from models.service import Service
from repositories.service_repository import ServiceRepository
from core.database import get_session
from core.encryption import decrypt_api_key

log = get_logger(__name__)


@dataclass
class CreditCheckResult:
    """Result of a credit check"""

    success: bool = True
    remaining_credit: Optional[float] = None
    total_limit: Optional[float] = None
    usage: Optional[float] = None
    below_threshold: bool = False
    threshold: Optional[float] = None
    error: Optional[str] = None


class CreditMonitor:
    """API credit monitor"""

    def __init__(self):
        self.log = log

    async def check_service(self, service: Service) -> CreditCheckResult:
        """
        Check API credit for a service

        Args:
            service: Service to check

        Returns:
            Credit check result
        """
        try:
            if service.api_provider.lower() == "openrouter":
                result = await self._check_openrouter(service)
            else:
                # Extensible for future providers
                self.log.warning(
                    "unsupported_api_provider",
                    service=service.name,
                    provider=service.api_provider,
                )
                return CreditCheckResult(
                    success=False, error=f"Unsupported provider: {service.api_provider}"
                )

            if result.success:
                self.log.info(
                    "credit_check_completed",
                    service=service.name,
                    remaining=result.remaining_credit,
                    below_threshold=result.below_threshold,
                )
            else:
                self.log.error("credit_check_failed", service=service.name, error=result.error)

            return result

        except Exception as e:
            self.log.error("credit_check_exception", service=service.name, error=str(e))
            return CreditCheckResult(success=False, error=str(e))

    async def _check_openrouter(self, service: Service) -> CreditCheckResult:
        """
        Check OpenRouter API credits using /api/v1/key endpoint

        Args:
            service: Service configuration

        Returns:
            Credit check result
        """
        try:
            # Decrypt API key
            api_key = decrypt_api_key(service.api_key_encrypted)

            # Call OpenRouter API - using correct endpoint
            # Endpoint: https://openrouter.ai/api/v1/key
            # Returns: {"data": {"limit": X, "usage": Y, "limit_remaining": Z, ...}}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/key",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
                data = response.json()

            # Parse response - OpenRouter API v1/key format
            api_data = data.get("data", {})
            limit = float(api_data.get("limit", 0))
            usage = float(api_data.get("usage", 0))

            # Use limit_remaining if available, otherwise calculate
            if "limit_remaining" in api_data:
                remaining = float(api_data["limit_remaining"])
            else:
                remaining = limit - usage

            # Check threshold
            below_threshold = remaining < service.credit_threshold

            return CreditCheckResult(
                success=True,
                remaining_credit=remaining,
                total_limit=limit,
                usage=usage,
                below_threshold=below_threshold,
                threshold=service.credit_threshold,
            )

        except httpx.HTTPStatusError as e:
            return CreditCheckResult(success=False, error=f"HTTP error: {e.response.status_code}")
        except httpx.TimeoutException:
            return CreditCheckResult(success=False, error="Request timeout")
        except (KeyError, ValueError) as e:
            return CreditCheckResult(success=False, error=f"Invalid API response format: {e}")
        except Exception as e:
            return CreditCheckResult(success=False, error=str(e))

    async def check_all_services(self) -> None:
        """Check all active API credit services"""
        try:
            async with get_session() as session:
                repo = ServiceRepository(session)
                services = await repo.get_services_by_type("api_credit", settings.environment)

            self.log.info("checking_credit_services", count=len(services))

            # Check all services concurrently
            tasks = [self.check_service(service) for service in services]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Log summary
            successful = sum(1 for r in results if isinstance(r, CreditCheckResult) and r.success)
            below_threshold = sum(
                1
                for r in results
                if isinstance(r, CreditCheckResult) and r.success and r.below_threshold
            )

            self.log.info(
                "credit_check_summary",
                total=len(results),
                successful=successful,
                below_threshold=below_threshold,
            )

        except Exception as e:
            self.log.error("credit_monitor_error", error=str(e), exc_info=True)
