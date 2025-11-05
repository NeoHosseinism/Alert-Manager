# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Alert Manager is a production-ready IT infrastructure monitoring and alerting system with Telegram integration. It monitors HTTP endpoints (health checks) and API credits (OpenRouter and custom providers), sending alerts via Telegram when services fail or credits run low.

**Key Technologies:**
- Python 3.11+ with Poetry for dependency management
- PostgreSQL with async SQLAlchemy 2.0 and asyncpg
- Alembic for database migrations
- python-telegram-bot for Telegram integration (async)
- APScheduler for job scheduling
- Pydantic v2 for settings management

## Development Commands

### Setup and Installation
```bash
# Install dependencies
make install

# Generate encryption key (required for API key encryption)
make generate-key

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
make migrate

# Create a new migration (after model changes)
make migrate-create MSG="description"

# Rollback last migration
make migrate-down
```

### Running the Application
```bash
# Run in development mode
make dev

# Add a user (required before first use)
make add-user PHONE=+989123456789 ROLE=super_admin NAME="Admin User"
```

### Testing and Quality
```bash
# Run all tests with coverage
make test

# Run specific test file
poetry run pytest tests/unit/test_health_checker.py -v

# Format code
poetry run black src/ tests/

# Lint code
poetry run ruff src/ tests/
```

### Docker
```bash
# Build Docker image
make docker-build

# Start with docker-compose (includes PostgreSQL)
make docker-compose-up

# View logs
make docker-compose-logs

# Stop services
make docker-compose-down
```

## Architecture Overview

### Core Components

**Main Application** (`src/main.py`):
- Entry point that initializes all components
- Creates APScheduler for periodic checks
- Starts Telegram bot
- Manages graceful shutdown

**Health Checker** (`src/monitoring/health_checker.py`):
- Polls HTTP endpoints at configurable intervals
- Implements retry logic (default: 3 retries with 30s delay)
- Creates alerts after all retries fail
- Detects recovery and sends recovery notifications
- Stores health check history in database

**Credit Monitor** (`src/monitoring/credit_monitor.py`):
- Monitors API credit balances using flexible provider system
- Supports pre-defined providers (OpenRouter) and custom providers
- Uses field mappings to translate provider-specific fields to standard metrics
- Creates alerts when credits drop below threshold
- Decrypts stored API keys for authentication

**Alert Engine** (`src/alerts/engine.py`):
- Receives failure notifications from monitors
- Checks cooldown periods to prevent spam (default: 30 minutes)
- Aggregates alerts in time windows (default: 2 minutes)
- Coordinates user notifications via Telegram
- Tracks which users were notified for recovery messages

**Telegram Bot** (`src/telegram_bot/bot.py`):
- Dual-bot support: production and sandbox bots
- Phone-based authentication (E.164 format required: +989123456789)
- Role-based access control (viewer, admin, super_admin)
- Handles commands: /status, /alerts, /mute, /services, etc.
- Interactive service configuration flow for API credit tracking

**Report Generator** (`src/reports/generator.py`):
- Generates periodic health reports
- Uses Jalali calendar for Persian date formatting
- Creates high-quality charts (150 DPI minimum)
- Supports daily, weekly, monthly, quarterly, yearly reports

### Provider System (API Credit Tracking)

The system uses a flexible provider configuration system that supports both pre-defined providers and custom providers.

**Pre-defined Providers** (`src/config/providers.py`):
- Currently includes OpenRouter with dual-endpoint tracking
- Easy to add new providers (Anthropic, OpenAI, etc.)
- Each provider defines endpoints and field mappings

**Custom Provider Flow**:
- Interactive Telegram bot conversation guides setup
- Users provide endpoint URLs, HTTP methods, field mappings
- Configurations stored in `api_tracking_config` JSON field
- Supports multiple endpoints per service (e.g., wallet + key endpoints)

**Standard Metrics**: All providers map their fields to standard internal metrics:
- `remaining_credit`, `total_credit`, `total_usage`
- `usage_daily`, `usage_weekly`, `usage_monthly`
- `byok_usage`, `key_label`, etc.

**OpenRouter Specific**: OpenRouter uses dual-threshold monitoring:
- Wallet level: Total account credits
- API Key level: Per-key limits and usage

### Data Layer

**Repository Pattern** (`src/repositories/`):
- All database access goes through repository classes
- Uses async SQLAlchemy sessions
- Provides clean abstraction over database operations

**Key Models** (`src/models/`):
- `User`: Phone-based authentication, roles (viewer/admin/super_admin), Telegram ID
- `Service`: Monitored services with type (health_check/api_credit), configuration stored in JSON fields
- `Alert`: Failure records with retry logs, notified users, resolution tracking
- `HealthCheck`: Historical health check results with response times
- `MutedService`: Per-user service muting with expiration
- `UserServicePermission`: Granular access control

### Error Handling Philosophy

**Never crash on external failures**:
- All external API calls have timeouts
- Retry logic with exponential backoff
- Graceful degradation when services unavailable
- Comprehensive logging (ASCII-only, no sensitive data)

## Critical Implementation Details

### Phone Numbers
- **MUST** be in E.164 format: `+989123456789` (with country code)
- Invalid: `9123456789` (missing +98 country code)
- Used for authentication, not stored as Telegram usernames

### Environment-Specific Behavior
- **dev**: Uses sandbox Telegram bot, DEBUG logging, full errors
- **stage/prod**: Uses main Telegram bot, INFO logging, minimal errors

### API Key Security
- API keys encrypted at rest using Fernet encryption
- Never log API keys
- Telegram messages containing API keys are deleted immediately after processing

### Async Operations
- All I/O operations are async (database, HTTP, Telegram)
- Use `await` for all repository calls
- Use async context managers for database sessions

### Database Migrations
- Always create migrations after model changes: `make migrate-create MSG="description"`
- Test migrations both up and down
- Use `ENVIRONMENT=dev` for local migrations
- Alembic looks for models in `src/models/__init__.py`

### Testing
- Use pytest with pytest-asyncio for async tests
- Mock external services (HTTP endpoints, Telegram API)
- Database tests should use test fixtures, not production DB
- Test coverage expected for all new functionality

### Logging
- Use structlog for structured logging
- Log format: JSON in production, console in development
- ASCII-only output (Docker compatibility)
- Include context in logs: service_id, user_id, alert_id
- Log levels: DEBUG (dev), INFO (stage/prod), WARNING (issues), ERROR (failures)

## Common Development Patterns

### Adding a New Service Type
1. Add service type to `ServiceType` enum in `src/models/service.py`
2. Create monitor class in `src/monitoring/`
3. Register periodic job in `src/main.py` scheduler
4. Add Telegram bot commands in `src/telegram_bot/bot.py`
5. Update documentation

### Adding a New Pre-defined Provider
1. Edit `src/config/providers.py`
2. Add provider configuration with endpoints and field mappings
3. Test with real API credentials
4. Document in PROVIDER_SYSTEM.md

### Adding Telegram Bot Commands
1. Add command handler in `src/telegram_bot/bot.py`
2. Use authentication middleware for user verification
3. Check permissions using user role
4. Use repositories for database access
5. Format responses for mobile viewing (use markdown)

### Working with Alerts
1. Check cooldown period before creating duplicate alerts
2. Include retry logs in alert details
3. Store notified user IDs for recovery messages
4. Mark alerts as resolved when service recovers
5. Calculate downtime from created_at to resolved_at

## File Structure Key Locations

- `src/main.py` - Application entry point
- `src/config/settings.py` - Environment configuration (Pydantic settings)
- `src/config/providers.py` - API provider configurations
- `src/core/database.py` - Database connection and session management
- `src/core/encryption.py` - Fernet encryption for API keys
- `src/models/` - SQLAlchemy models (base.py for shared base class)
- `src/repositories/` - Database access layer
- `src/monitoring/health_checker.py` - HTTP endpoint monitoring
- `src/monitoring/credit_monitor.py` - API credit tracking
- `src/alerts/engine.py` - Alert creation and notification coordination
- `src/telegram_bot/bot.py` - Bot initialization and command handlers
- `src/telegram_bot/service_config_conversation.py` - Interactive service setup
- `src/reports/generator.py` - Report generation with charts
- `src/utils/` - Shared utilities
- `tests/` - Test suite (unit tests in tests/unit/)
- `alembic/` - Database migrations
- `scripts/` - Utility scripts (e.g., add_user.py)

## Important Notes

- The system uses **PostgreSQL's JSON fields** extensively for flexible configuration (service.api_tracking_config, service.metadata, alert.details)
- **Recovery notifications** are sent to the exact same users who received the original failure alert (tracked in alert.notified_user_ids)
- **Scheduler jobs** run concurrently - health checks for all services happen in parallel
- **Alert aggregation** batches multiple failures within 2-minute windows to avoid spam
- **Muting** is per-user, per-service with expiration times
- The **provider system** allows monitoring any API without code changes - just configure endpoints and field mappings via Telegram bot
