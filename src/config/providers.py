"""
Pre-defined API provider configurations for credit tracking

Supports both pre-configured providers (OpenRouter, etc.) and custom providers
with user-defined endpoint and metric mappings.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EndpointConfig:
    """Configuration for a single API endpoint"""

    name: str  # e.g., "key_management", "credits"
    path: str  # e.g., "/api/v1/key"
    method: str = "GET"  # HTTP method
    headers_template: Dict[str, str] = field(default_factory=dict)  # e.g., {"Authorization": "Bearer {api_key}"}
    request_body: Optional[Dict[str, Any]] = None  # Request body template (for POST)

    # Response field mappings: external_field_name -> internal_metric_name
    field_mappings: Dict[str, str] = field(default_factory=dict)

    # Path to data in response (e.g., ["data"] means response["data"])
    response_data_path: List[str] = field(default_factory=list)


@dataclass
class ProviderConfig:
    """Configuration for an API provider"""

    name: str  # Display name
    provider_id: str  # Unique identifier
    base_url: str  # Base URL (can be overridden per service)
    endpoints: List[EndpointConfig] = field(default_factory=list)
    description: str = ""


# Standard internal metric names used across all providers
STANDARD_METRICS = {
    # Balance metrics
    "remaining_credit": "Remaining credit/balance",
    "total_credit": "Total credit limit",
    "total_usage": "Total usage (all time)",

    # Time-based usage
    "usage_daily": "Usage today (current UTC day)",
    "usage_weekly": "Usage this week (current UTC week)",
    "usage_monthly": "Usage this month (current UTC month)",

    # BYOK (Bring Your Own Key) metrics
    "byok_usage": "BYOK usage (all time)",
    "byok_usage_daily": "BYOK usage today",
    "byok_usage_weekly": "BYOK usage this week",
    "byok_usage_monthly": "BYOK usage this month",

    # Metadata
    "key_label": "API key label/name",
    "limit_reset": "When the limit resets",
    "is_free_tier": "Whether on free tier",
    "include_byok_in_limit": "Whether BYOK counts toward limit",
}


# Pre-defined provider configurations
PROVIDERS: Dict[str, ProviderConfig] = {
    "openrouter": ProviderConfig(
        name="OpenRouter",
        provider_id="openrouter",
        base_url="https://openrouter.ai",
        description="OpenRouter AI API with dual-method tracking",
        endpoints=[
            EndpointConfig(
                name="credits",
                path="/api/v1/credits",
                method="GET",
                headers_template={"Authorization": "Bearer {api_key}"},
                response_data_path=["data"],
                field_mappings={
                    # Wallet-level metrics (entire account)
                    "total_credits": "wallet_total_credits",
                    "total_usage": "wallet_total_usage",
                }
            ),
            EndpointConfig(
                name="key_management",
                path="/api/v1/key",
                method="GET",
                headers_template={"Authorization": "Bearer {api_key}"},
                response_data_path=["data"],
                field_mappings={
                    # API Key-level metrics (this specific key only)
                    "label": "key_label",
                    "limit": "key_limit",
                    "limit_remaining": "key_remaining",
                    "limit_reset": "key_limit_reset",
                    "usage": "key_usage",
                    "usage_daily": "key_usage_daily",
                    "usage_weekly": "key_usage_weekly",
                    "usage_monthly": "key_usage_monthly",
                    "byok_usage": "key_byok_usage",
                    "byok_usage_daily": "key_byok_usage_daily",
                    "byok_usage_weekly": "key_byok_usage_weekly",
                    "byok_usage_monthly": "key_byok_usage_monthly",
                    "is_free_tier": "is_free_tier",
                    "include_byok_in_limit": "include_byok_in_limit",
                }
            ),
        ]
    ),

    # Add more pre-defined providers here in the future
    # "anthropic": ProviderConfig(...),
    # "openai": ProviderConfig(...),
}


def get_provider(provider_id: str) -> Optional[ProviderConfig]:
    """Get a pre-defined provider configuration"""
    return PROVIDERS.get(provider_id)


def list_providers() -> List[ProviderConfig]:
    """List all pre-defined providers"""
    return list(PROVIDERS.values())


def create_custom_provider(
    name: str,
    base_url: str,
    endpoints: List[EndpointConfig]
) -> ProviderConfig:
    """Create a custom provider configuration"""
    return ProviderConfig(
        name=name,
        provider_id="custom",
        base_url=base_url,
        endpoints=endpoints,
        description="Custom provider configuration"
    )
