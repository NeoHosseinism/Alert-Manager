# Provider-Based API Tracking System

## Overview

The alert-manager now supports **flexible API credit tracking** with:

1. **Pre-defined Providers** (OpenRouter, etc.) - Ready to use configurations
2. **Custom Providers** - Interactive setup for any API
3. **Field Mapping System** - Map provider-specific fields to standard metrics
4. **Editable Services** - Modify configurations after creation

## Architecture

### Key Components

**1. Provider Registry** (`src/config/providers.py`)
- Stores pre-defined provider configurations
- Defines standard metrics used across all providers
- Currently includes: OpenRouter (more can be added)

**2. Interactive Conversation Flow** (`src/telegram_bot/service_config_conversation.py`)
- Multi-step guided setup via Telegram bot
- Collects endpoint URLs, request/response formats, field mappings
- Validates configurations before creation

**3. Flexible Credit Monitor** (`src/monitoring/credit_monitor.py`)
- Reads provider configuration from database
- Makes HTTP requests according to endpoint config
- Applies field mappings to translate provider fields to internal metrics
- Merges data from multiple endpoints

**4. Service Model** (`src/models/service.py`)
- `api_tracking_config` JSON field stores complete provider configuration
- Supports multiple endpoints per service
- Each endpoint has its own field mappings

## How It Works

### Pre-defined Provider Flow (OpenRouter Example)

1. **Super admin starts**: `/add_service`
2. **Bot asks**: Service type → Choose "API Credit Tracking"
3. **Bot asks**: Provider mode → Choose "Pre-defined Provider"
4. **Bot shows**: List of providers → Select "OpenRouter"
5. **Bot asks**: Service name and optional custom base URL
   - Example: `MyOpenRouter` (uses default https://openrouter.ai)
   - Or: `MyOpenRouter https://custom-openrouter.com`
6. **Bot shows**: Configuration summary
7. **Confirm**: Service created with OpenRouter's dual-method tracking:
   - Method 1: `/api/v1/key` → Detailed usage (daily/weekly/monthly/BYOK)
   - Method 2: `/api/v1/credits` → Simple balance

### Custom Provider Flow

1. **Super admin starts**: `/add_service`
2. **Bot asks**: Service type → Choose "API Credit Tracking"
3. **Bot asks**: Provider mode → Choose "Custom Provider"
4. **Bot asks**: Service name and base URL
   - Example: `MyAPI https://api.myprovider.com`
5. **Bot asks**: How many endpoints? (1-5)
   - Example: `2` (key info + credits)
6. **For each endpoint, bot asks**: Endpoint configuration (JSON)
   ```json
   {
     "name": "key_info",
     "path": "/v1/account/key",
     "method": "GET"
   }
   ```
7. **For each endpoint, bot asks**: Field mappings (JSON)
   ```json
   {
     "balance": "remaining_credit",
     "total_limit": "total_credit",
     "used_amount": "total_usage"
   }
   ```
8. **Bot shows**: Configuration summary
9. **Confirm**: Service created with custom configuration

## Standard Metrics

All providers map their fields to these standard internal metrics:

| Metric Name | Description |
|------------|-------------|
| `remaining_credit` | Remaining credit/balance |
| `total_credit` | Total credit limit |
| `total_usage` | Total usage (all time) |
| `usage_daily` | Usage today (current UTC day) |
| `usage_weekly` | Usage this week (current UTC week) |
| `usage_monthly` | Usage this month (current UTC month) |
| `byok_usage` | BYOK usage (all time) |
| `byok_usage_daily` | BYOK usage today |
| `byok_usage_weekly` | BYOK usage this week |
| `byok_usage_monthly` | BYOK usage this month |
| `key_label` | API key label/name |
| `limit_reset` | When the limit resets |
| `is_free_tier` | Whether on free tier |
| `include_byok_in_limit` | Whether BYOK counts toward limit |

## Service Configuration Format

The `api_tracking_config` JSON field stores:

```json
{
  "provider_id": "openrouter",
  "provider_name": "OpenRouter",
  "endpoints": [
    {
      "name": "key_management",
      "path": "/api/v1/key",
      "method": "GET",
      "headers_template": {
        "Authorization": "Bearer {api_key}"
      },
      "response_data_path": ["data"],
      "field_mappings": {
        "label": "key_label",
        "limit": "total_credit",
        "limit_remaining": "remaining_credit",
        "usage": "total_usage",
        "usage_daily": "usage_daily",
        "usage_weekly": "usage_weekly",
        "usage_monthly": "usage_monthly"
      }
    },
    {
      "name": "credits",
      "path": "/api/v1/credits",
      "method": "GET",
      "headers_template": {
        "Authorization": "Bearer {api_key}"
      },
      "response_data_path": ["data"],
      "field_mappings": {
        "total_credits": "total_credit",
        "total_usage": "total_usage"
      }
    }
  ]
}
```

## Field Mapping Examples

### Example 1: OpenRouter → Standard Metrics
```
OpenRouter Response:
{
  "data": {
    "limit": 100.0,
    "limit_remaining": 75.5,
    "usage": 24.5,
    "usage_daily": 5.2
  }
}

Field Mappings:
{
  "limit": "total_credit",
  "limit_remaining": "remaining_credit",
  "usage": "total_usage",
  "usage_daily": "usage_daily"
}

Result (Internal Metrics):
{
  "total_credit": 100.0,
  "remaining_credit": 75.5,
  "total_usage": 24.5,
  "usage_daily": 5.2
}
```

### Example 2: Custom Provider → Standard Metrics
```
Custom Provider Response:
{
  "account": {
    "balance": 50.0,
    "quota": 100.0,
    "spent": 50.0
  }
}

Field Mappings (with response_data_path: ["account"]):
{
  "balance": "remaining_credit",
  "quota": "total_credit",
  "spent": "total_usage"
}

Result (Internal Metrics):
{
  "remaining_credit": 50.0,
  "total_credit": 100.0,
  "total_usage": 50.0
}
```

## Complete Usage Example

### Step 1: Add OpenRouter Service
```
User: /add_service
Bot: [Shows service type options]
User: [Clicks "API Credit Tracking"]
Bot: [Shows provider mode options]
User: [Clicks "Pre-defined Provider"]
Bot: [Shows OpenRouter]
User: [Clicks "OpenRouter"]
Bot: [Asks for service name]
User: MyOpenRouter
Bot: [Shows confirmation]
User: [Clicks "✅ Create Service"]
Bot: Service created! ID: 1
```

### Step 2: Set API Key
```
User: /set_api_key 1 sk-or-v1-your-key-here
Bot: [Deletes message for security]
Bot: API key configured and encrypted
```

### Step 3: Assign Users
```
User: /assign 5 1
Bot: User assigned to service
```

### Step 4: Monitor
The system now automatically:
- Calls both OpenRouter endpoints (/api/v1/key + /api/v1/credits)
- Maps all fields to standard metrics
- Checks against threshold
- Sends alerts if credit is low
- Generates unified reports

## Adding New Pre-defined Providers

To add a new provider (e.g., Anthropic, OpenAI), edit `src/config/providers.py`:

```python
PROVIDERS = {
    "openrouter": ProviderConfig(...),  # Existing

    "anthropic": ProviderConfig(
        name="Anthropic",
        provider_id="anthropic",
        base_url="https://api.anthropic.com",
        description="Anthropic Claude API",
        endpoints=[
            EndpointConfig(
                name="usage",
                path="/v1/usage",
                method="GET",
                headers_template={"x-api-key": "{api_key}"},
                response_data_path=[],
                field_mappings={
                    "remaining_credits": "remaining_credit",
                    "total_credits": "total_credit",
                    # ... map other fields
                }
            )
        ]
    ),
}
```

## Benefits

✅ **Truly Generic** - Works with any API, not hardcoded to OpenRouter
✅ **Guided Setup** - Interactive bot flow prevents configuration errors
✅ **Flexible Mapping** - Different providers use different field names
✅ **Unified Reporting** - All metrics mapped to standard names
✅ **Multi-Endpoint Support** - Combine data from multiple APIs
✅ **Future-Proof** - Easy to add new providers without code changes
✅ **Type-Safe** - Automatic type conversion for metrics

## Migration

**For existing services:**
Old services without proper `api_tracking_config` will need to be re-created using the new `/add_service` flow. The system will guide you through the proper configuration.

**For new deployments:**
1. Run migration: `make migrate`
2. Restart bot: `make dev`
3. Use `/add_service` to create services with interactive flow
