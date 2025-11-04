"""
Flexible API credit monitoring with provider-agnostic configuration

Supports both pre-defined providers (OpenRouter, etc.) and custom providers
with configurable endpoints and field mappings.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

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
    """Result of a credit check with flexible metric storage"""

    # Status
    success: bool = True
    error: Optional[str] = None
    below_threshold: bool = False
    threshold: Optional[float] = None

    # Flexible metrics storage - populated via field mappings
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_credit(self) -> Optional[float]:
        """Get remaining credit from mapped metrics"""
        return self.metrics.get("remaining_credit")

    @property
    def total_credit(self) -> Optional[float]:
        """Get total credit from mapped metrics"""
        return self.metrics.get("total_credit")

    @property
    def total_usage(self) -> Optional[float]:
        """Get total usage from mapped metrics"""
        return self.metrics.get("total_usage")

    # Convenience accessors for common metrics
    @property
    def usage_daily(self) -> Optional[float]:
        return self.metrics.get("usage_daily")

    @property
    def usage_weekly(self) -> Optional[float]:
        return self.metrics.get("usage_weekly")

    @property
    def usage_monthly(self) -> Optional[float]:
        return self.metrics.get("usage_monthly")


class CreditMonitor:
    """Flexible API credit monitor with provider-agnostic configuration"""

    def __init__(self):
        self.log = log

    async def check_service(self, service: Service) -> CreditCheckResult:
        """
        Check API credit for a service using its configuration

        Args:
            service: Service with api_tracking_config

        Returns:
            Credit check result with mapped metrics
        """
        try:
            # Validate configuration
            if not service.endpoint_url:
                return CreditCheckResult(success=False, error="No endpoint URL configured")

            if not service.api_key_encrypted:
                return CreditCheckResult(success=False, error="No API key configured")

            # Get tracking configuration
            # If service has a provider_id, use the latest provider definition from code
            # This ensures users always get the latest field mappings without manual refresh
            tracking_config = None

            if service.api_provider:
                # Try to get provider from code (case-insensitive)
                from config.providers import get_provider, PROVIDERS

                # Try exact match first
                provider_config = get_provider(service.api_provider)

                # If not found, try case-insensitive match
                if not provider_config:
                    provider_id_lower = service.api_provider.lower()
                    for pid, pconfig in PROVIDERS.items():
                        if pid.lower() == provider_id_lower:
                            provider_config = pconfig
                            break

                if provider_config:
                    # Convert provider config to tracking config format
                    tracking_config = {
                        "provider_id": provider_config.provider_id,
                        "endpoints": []
                    }

                    for endpoint in provider_config.endpoints:
                        endpoint_dict = {
                            "name": endpoint.name,
                            "path": endpoint.path,
                            "method": endpoint.method,
                            "headers_template": endpoint.headers_template,
                            "response_data_path": endpoint.response_data_path,
                            "field_mappings": endpoint.field_mappings,
                        }
                        if endpoint.request_body:
                            endpoint_dict["request_body"] = endpoint.request_body
                        tracking_config["endpoints"].append(endpoint_dict)

                    self.log.debug(
                        "using_provider_from_code",
                        service=service.name,
                        provider_id=provider_config.provider_id
                    )

            # Fall back to stored configuration if no provider found
            if not tracking_config:
                tracking_config = service.api_tracking_config
                if not tracking_config:
                    return CreditCheckResult(success=False, error="No tracking configuration")

            endpoints = tracking_config.get("endpoints", [])
            if not endpoints:
                return CreditCheckResult(success=False, error="No endpoints configured")

            # Check all configured endpoints
            results = []
            errors = []

            for endpoint_config in endpoints:
                result = await self._check_endpoint(service, endpoint_config)
                if result.success:
                    results.append(result)
                else:
                    errors.append(f"{endpoint_config.get('name', 'unknown')}: {result.error}")

            # Merge results
            if not results:
                error_msg = "; ".join(errors) if errors else "All endpoints failed"
                return CreditCheckResult(success=False, error=error_msg)

            merged_result = self._merge_results(results, service.credit_threshold)

            if merged_result.success:
                self.log.info(
                    "credit_check_completed",
                    service=service.name,
                    remaining=merged_result.remaining_credit,
                    below_threshold=merged_result.below_threshold,
                    endpoint_count=len(endpoints),
                )
            else:
                self.log.error("credit_check_failed", service=service.name, error=merged_result.error)

            return merged_result

        except Exception as e:
            self.log.error("credit_check_exception", service=service.name, error=str(e))
            return CreditCheckResult(success=False, error=str(e))

    async def _check_endpoint(self, service: Service, endpoint_config: dict) -> CreditCheckResult:
        """
        Check a single API endpoint and apply field mappings

        Args:
            service: Service configuration
            endpoint_config: Endpoint configuration dict containing:
                - name: str
                - path: str
                - method: str (GET, POST, etc.)
                - headers_template: dict (optional)
                - request_body: dict (optional)
                - response_data_path: list[str] (optional)
                - field_mappings: dict mapping external -> internal names

        Returns:
            Credit check result with mapped metrics
        """
        try:
            # Decrypt API key
            api_key = decrypt_api_key(service.api_key_encrypted)

            # Build URL
            base_url = service.endpoint_url.rstrip("/")
            path = endpoint_config.get("path", "")
            url = f"{base_url}{path}"

            # Build headers
            headers_template = endpoint_config.get("headers_template", {})
            headers = {}
            for key, value_template in headers_template.items():
                # Replace {api_key} placeholder
                value = value_template.replace("{api_key}", api_key)
                headers[key] = value

            # Get request parameters
            method = endpoint_config.get("method", "GET").upper()
            request_body = endpoint_config.get("request_body")

            # Make request
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=request_body)
                else:
                    return CreditCheckResult(success=False, error=f"Unsupported method: {method}")

                response.raise_for_status()
                data = response.json()

            # Navigate to data location in response
            response_data_path = endpoint_config.get("response_data_path", [])
            current_data = data
            for path_segment in response_data_path:
                current_data = current_data.get(path_segment, {})

            # Apply field mappings
            field_mappings = endpoint_config.get("field_mappings", {})
            mapped_metrics = {}

            for external_field, internal_metric in field_mappings.items():
                if external_field in current_data:
                    value = current_data[external_field]
                    # Convert to appropriate type
                    if value is not None:
                        # Try to convert to float for numeric fields
                        try:
                            if isinstance(value, (int, float)):
                                mapped_metrics[internal_metric] = float(value)
                            elif isinstance(value, str):
                                # Keep as string (for label, etc.)
                                mapped_metrics[internal_metric] = value
                            elif isinstance(value, bool):
                                mapped_metrics[internal_metric] = value
                            else:
                                mapped_metrics[internal_metric] = value
                        except (ValueError, TypeError):
                            mapped_metrics[internal_metric] = value

            return CreditCheckResult(
                success=True,
                metrics=mapped_metrics
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
        self, results: List[CreditCheckResult], threshold: Optional[float]
    ) -> CreditCheckResult:
        """
        Merge results from multiple endpoints

        Args:
            results: List of credit check results from different endpoints
            threshold: Credit threshold for alerting

        Returns:
            Merged credit check result
        """
        # Merge all metrics from all results
        merged_metrics = {}

        for result in results:
            for metric_name, value in result.metrics.items():
                if value is not None:
                    # Last value wins (could implement more sophisticated merging)
                    merged_metrics[metric_name] = value

        # Create merged result
        merged = CreditCheckResult(
            success=True,
            metrics=merged_metrics,
            threshold=threshold
        )

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
