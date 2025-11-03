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
    """Result of a credit check with support for multiple tracking methods"""

    # Status
    success: bool = True
    error: Optional[str] = None
    below_threshold: bool = False
    threshold: Optional[float] = None

    # Method 1: Key Management API - Detailed Usage Tracking
    key_label: Optional[str] = None
    limit: Optional[float] = None
    limit_reset: Optional[str] = None
    limit_remaining: Optional[float] = None
    include_byok_in_limit: Optional[bool] = None

    # Usage stats (all time, daily, weekly, monthly)
    usage: Optional[float] = None
    usage_daily: Optional[float] = None
    usage_weekly: Optional[float] = None
    usage_monthly: Optional[float] = None

    # BYOK (Bring Your Own Key) usage stats
    byok_usage: Optional[float] = None
    byok_usage_daily: Optional[float] = None
    byok_usage_weekly: Optional[float] = None
    byok_usage_monthly: Optional[float] = None

    is_free_tier: Optional[bool] = None

    # Method 2: Credits API - Simple Balance Tracking
    total_credits: Optional[float] = None
    total_usage: Optional[float] = None

    # Computed fields
    @property
    def remaining_credit(self) -> Optional[float]:
        """Get remaining credit from available data sources"""
        # Priority: limit_remaining > total_credits - total_usage > limit - usage
        if self.limit_remaining is not None:
            return self.limit_remaining
        if self.total_credits is not None and self.total_usage is not None:
            return self.total_credits - self.total_usage
        if self.limit is not None and self.usage is not None:
            return self.limit - self.usage
        return None

    @property
    def total_limit(self) -> Optional[float]:
        """Get total limit from available data sources"""
        return self.total_credits or self.limit


class CreditMonitor:
    """API credit monitor"""

    def __init__(self):
        self.log = log

    async def check_service(self, service: Service) -> CreditCheckResult:
        """
        Check API credit for a service using configured tracking methods

        Args:
            service: Service to check

        Returns:
            Credit check result with data from all configured methods
        """
        try:
            # Validate configuration
            if not service.endpoint_url:
                return CreditCheckResult(success=False, error="No endpoint URL configured")

            if not service.api_key_encrypted:
                return CreditCheckResult(success=False, error="No API key configured")

            # Get tracking configuration
            tracking_config = service.api_tracking_config or {}
            methods = tracking_config.get("methods", [])

            if not methods:
                self.log.warning("no_tracking_methods", service=service.name)
                return CreditCheckResult(success=False, error="No tracking methods configured")

            # Check all configured methods
            results = []
            errors = []

            if "key_management" in methods:
                result = await self._check_key_management_api(service, tracking_config)
                if result.success:
                    results.append(result)
                else:
                    errors.append(f"Key management: {result.error}")

            if "credits" in methods:
                result = await self._check_credits_api(service, tracking_config)
                if result.success:
                    results.append(result)
                else:
                    errors.append(f"Credits: {result.error}")

            # Merge results
            if not results:
                error_msg = "; ".join(errors) if errors else "All tracking methods failed"
                return CreditCheckResult(success=False, error=error_msg)

            merged_result = self._merge_results(results, service.credit_threshold)

            if merged_result.success:
                self.log.info(
                    "credit_check_completed",
                    service=service.name,
                    remaining=merged_result.remaining_credit,
                    below_threshold=merged_result.below_threshold,
                    methods=methods,
                )
            else:
                self.log.error("credit_check_failed", service=service.name, error=merged_result.error)

            return merged_result

        except Exception as e:
            self.log.error("credit_check_exception", service=service.name, error=str(e))
            return CreditCheckResult(success=False, error=str(e))

    async def _check_key_management_api(
        self, service: Service, tracking_config: dict
    ) -> CreditCheckResult:
        """
        Check API using key management endpoint for detailed usage tracking

        Expected API response format:
        {
          "data": {
            "label": "string",
            "limit": float | null,
            "limit_reset": "string" | null,
            "limit_remaining": float | null,
            "include_byok_in_limit": bool,
            "usage": float,
            "usage_daily": float,
            "usage_weekly": float,
            "usage_monthly": float,
            "byok_usage": float,
            "byok_usage_daily": float,
            "byok_usage_weekly": float,
            "byok_usage_monthly": float,
            "is_free_tier": bool
          }
        }

        Args:
            service: Service configuration
            tracking_config: Tracking configuration dict

        Returns:
            Credit check result with detailed usage data
        """
        try:
            # Decrypt API key
            api_key = decrypt_api_key(service.api_key_encrypted)

            # Build URL
            path = tracking_config.get("key_management_path", "/api/v1/key")
            url = service.endpoint_url.rstrip("/") + path

            # Make request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
                data = response.json()

            # Parse response
            api_data = data.get("data", {})

            return CreditCheckResult(
                success=True,
                key_label=api_data.get("label"),
                limit=float(api_data["limit"]) if api_data.get("limit") is not None else None,
                limit_reset=api_data.get("limit_reset"),
                limit_remaining=(
                    float(api_data["limit_remaining"])
                    if api_data.get("limit_remaining") is not None
                    else None
                ),
                include_byok_in_limit=api_data.get("include_byok_in_limit"),
                usage=float(api_data.get("usage", 0)),
                usage_daily=float(api_data.get("usage_daily", 0)),
                usage_weekly=float(api_data.get("usage_weekly", 0)),
                usage_monthly=float(api_data.get("usage_monthly", 0)),
                byok_usage=float(api_data.get("byok_usage", 0)),
                byok_usage_daily=float(api_data.get("byok_usage_daily", 0)),
                byok_usage_weekly=float(api_data.get("byok_usage_weekly", 0)),
                byok_usage_monthly=float(api_data.get("byok_usage_monthly", 0)),
                is_free_tier=api_data.get("is_free_tier"),
            )

        except httpx.HTTPStatusError as e:
            return CreditCheckResult(success=False, error=f"HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            return CreditCheckResult(success=False, error="Request timeout")
        except (KeyError, ValueError, TypeError) as e:
            return CreditCheckResult(success=False, error=f"Invalid response format: {e}")
        except Exception as e:
            return CreditCheckResult(success=False, error=str(e))

    async def _check_credits_api(self, service: Service, tracking_config: dict) -> CreditCheckResult:
        """
        Check API using credits endpoint for simple balance tracking

        Expected API response format:
        {
          "data": {
            "total_credits": float,
            "total_usage": float
          }
        }

        Args:
            service: Service configuration
            tracking_config: Tracking configuration dict

        Returns:
            Credit check result with balance data
        """
        try:
            # Decrypt API key
            api_key = decrypt_api_key(service.api_key_encrypted)

            # Build URL
            path = tracking_config.get("credits_path", "/api/v1/credits")
            url = service.endpoint_url.rstrip("/") + path

            # Make request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                response.raise_for_status()
                data = response.json()

            # Parse response
            api_data = data.get("data", {})

            return CreditCheckResult(
                success=True,
                total_credits=float(api_data.get("total_credits", 0)),
                total_usage=float(api_data.get("total_usage", 0)),
            )

        except httpx.HTTPStatusError as e:
            return CreditCheckResult(success=False, error=f"HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            return CreditCheckResult(success=False, error="Request timeout")
        except (KeyError, ValueError, TypeError) as e:
            return CreditCheckResult(success=False, error=f"Invalid response format: {e}")
        except Exception as e:
            return CreditCheckResult(success=False, error=str(e))

    def _merge_results(
        self, results: list[CreditCheckResult], threshold: Optional[float]
    ) -> CreditCheckResult:
        """
        Merge results from multiple tracking methods

        Args:
            results: List of credit check results
            threshold: Credit threshold for alerting

        Returns:
            Merged credit check result
        """
        # Start with empty result
        merged = CreditCheckResult(success=True)

        # Merge all non-None fields from all results
        for result in results:
            for field in [
                "key_label",
                "limit",
                "limit_reset",
                "limit_remaining",
                "include_byok_in_limit",
                "usage",
                "usage_daily",
                "usage_weekly",
                "usage_monthly",
                "byok_usage",
                "byok_usage_daily",
                "byok_usage_weekly",
                "byok_usage_monthly",
                "is_free_tier",
                "total_credits",
                "total_usage",
            ]:
                value = getattr(result, field, None)
                if value is not None:
                    setattr(merged, field, value)

        # Set threshold
        merged.threshold = threshold

        # Check if below threshold
        if threshold and merged.remaining_credit is not None:
            merged.below_threshold = merged.remaining_credit < threshold

        return merged

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
