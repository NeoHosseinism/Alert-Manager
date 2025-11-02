# Alert Manager

A production-ready IT infrastructure monitoring and alerting system with Telegram integration, featuring health checks, API credit monitoring, and automated reporting.

## Features

- **Health Check Monitoring**: Monitor HTTP endpoints with configurable retry logic
- **API Credit Monitoring**: Track API usage and balance (OpenRouter, extensible)
- **Smart Alerting**: Alert aggregation, deduplication, and cooldown periods
- **Recovery Notifications**: Automatic notifications when services recover
- **Telegram Integration**: Dual-bot support (production and sandbox) with role-based access
- **Jalali Calendar Reports**: Daily, weekly, monthly, quarterly, and yearly reports
- **High-Quality Charts**: Professional charts optimized for Telegram
- **Secure**: Encrypted API keys, phone-based authentication
- **Resilient**: Retry logic, graceful degradation, never crashes on external failures
- **Production-Ready**: Docker deployment, structured logging, comprehensive testing

## Tech Stack

- **Python 3.11+** with Poetry for dependency management
- **PostgreSQL** with async SQLAlchemy 2.0 and asyncpg
- **Alembic** for database migrations
- **python-telegram-bot** for Telegram integration (async)
- **APScheduler** for job scheduling
- **httpx** for async HTTP requests
- **structlog** for structured logging (ASCII-only)
- **Pydantic v2** for settings management
- **persiantools** for Jalali calendar
- **matplotlib + seaborn** for chart generation
- **cryptography** for API key encryption
- **Docker** with multi-stage builds

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Poetry
- Telegram bot token (from @BotFather)

### Installation

```bash
# Clone repository
cd alert-manager

# Install dependencies
make install

# Generate encryption key
make generate-key

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
make migrate

# Bootstrap initial data (optional)
make bootstrap

# Run in development mode
make dev
```

### Docker Deployment

```bash
# Build and start with docker-compose
make docker-compose-up

# View logs
make docker-compose-logs

# Stop services
make docker-compose-down
```

## Configuration

### Environment Variables

See `.env.example` for all available configuration options.

**Critical Settings:**

```env
# Environment: dev, stage, or prod
ENVIRONMENT=prod

# Database connection
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Telegram bots
TELEGRAM_MAIN_BOT_TOKEN=your-production-bot-token
TELEGRAM_SANDBOX_BOT_TOKEN=your-development-bot-token

# Encryption (generate with: make generate-key)
ENCRYPTION_KEY=your-fernet-key

# Monitoring defaults
DEFAULT_HEALTH_CHECK_INTERVAL=300
DEFAULT_MAX_RETRIES=3
ALERT_AGGREGATION_WINDOW=120
```

### Database Setup

```bash
# Create database
createdb alert_manager_db

# Run migrations
make migrate

# Create a migration (after model changes)
make migrate-create MSG="add new field"

# Rollback migration
make migrate-down
```

## Usage

### Telegram Bot Commands

**All Users:**
- `/start` - Get started and see available commands
- `/status` - Show current status of all your services
- `/services` - List services you have access to
- `/alerts [count]` - Show recent alerts (default: 10)
- `/mute <service> [hours]` - Mute alerts for a service (default: 1 hour)
- `/unmute <service>` - Unmute a service
- `/muted` - List currently muted services

**Admin + Super Admin:**
- `/assign <phone> <service>` - Assign service to user
- `/unassign <phone> <service>` - Remove service access

**Super Admin Only:**
- `/add_user <phone> <role>` - Add new user (roles: viewer, admin, super_admin)
- `/add_service <name> <type> <url>` - Add new service
- `/edit_service <name> <field> <value>` - Edit service configuration
- `/remove_service <name>` - Remove service
- `/list_all_services` - List all services
- `/list_users` - List all users
- `/set_archive_days <service> <days>` - Configure alert archiving

### Adding Services

**Health Check Service:**
```bash
/add_service payment-api health_check https://api.example.com/health
```

**API Credit Service:**
```bash
/add_service openrouter-credits api_credit openrouter
# Then set the API key:
/edit_service openrouter-credits api_key sk-your-api-key-here
```

### Phone Number Format

All phone numbers must be in E.164 format:
- ✅ `+989123456789` (Iran)
- ✅ `+12025551234` (USA)
- ❌ `9123456789` (missing country code)

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Main Application                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Scheduler   │  │  Telegram    │  │  Database    │ │
│  │ (APScheduler)│  │     Bot      │  │ (PostgreSQL) │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │          │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
    ┌─────▼─────┐      ┌────▼────┐      ┌─────▼─────┐
    │  Health   │      │ Alert   │      │Repository │
    │  Checker  │──────│ Engine  │──────│  Pattern  │
    └───────────┘      └────┬────┘      └───────────┘
          │                 │
    ┌─────▼─────┐      ┌────▼────┐
    │  Credit   │      │ Report  │
    │  Monitor  │      │Generator│
    └───────────┘      └─────────┘
```

### Data Flow

1. **Scheduled Checks**: APScheduler triggers health and credit checks
2. **Failure Detection**: Failed checks go through retry logic
3. **Alert Creation**: After all retries fail, alert is created
4. **Alert Aggregation**: Alerts are grouped in 2-minute windows
5. **User Notification**: Telegram messages sent to authorized users
6. **Recovery Detection**: When service becomes healthy, recovery notification sent

### Database Schema

See `Architecture.md` for detailed ER diagrams.

**Main Tables:**
- `users` - User accounts with roles
- `services` - Monitored services (health checks, API credits)
- `alerts` - Generated alerts with resolution tracking
- `health_checks` - Historical health check results
- `muted_services` - Per-user service muting
- `user_service_permissions` - Access control
- `report_schedules` - Automated report configuration

## Development

### Running Tests

```bash
# Run all tests with coverage
make test

# Run specific test file
poetry run pytest tests/unit/test_health_checker.py -v
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Clean build artifacts
make clean
```

### Project Structure

```
alert-manager/
├── src/alert_manager/
│   ├── config/          # Settings and logging
│   ├── core/            # Database, encryption, exceptions
│   ├── models/          # SQLAlchemy models
│   ├── repositories/    # Data access layer
│   ├── monitoring/      # Health checks, credit monitoring
│   ├── alerts/          # Alert engine and aggregation
│   ├── telegram/        # Bot and handlers
│   ├── reports/         # Report generation
│   └── utils/           # Utility functions
├── tests/               # Test suite
├── alembic/             # Database migrations
├── scripts/             # Utility scripts
├── Dockerfile           # Multi-stage Docker build
├── docker-compose.yml   # Local development setup
├── Makefile             # Common tasks
└── pyproject.toml       # Poetry configuration
```

## Monitoring Best Practices

### Health Check Configuration

- **Interval**: 300 seconds (5 minutes) for most services
- **Timeout**: 10 seconds maximum
- **Max Retries**: 3 attempts with 30-second delays
- **Expected Status**: 200 OK (configurable)

### Alert Management

- **Cooldown**: 30 minutes between duplicate alerts
- **Aggregation**: 2-minute window for grouping failures
- **Batch Limits**: Flush after 10 alerts or 5 critical alerts
- **Muting**: Temporary mute support (default: 1 hour)

### API Credit Monitoring

- **Threshold**: Alert when balance drops below $20 (configurable)
- **Check Frequency**: Every 24 hours
- **Providers**: OpenRouter (extensible for others)

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql $DATABASE_URL

# Check pool settings in .env
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### Telegram Bot Not Responding

1. Check bot token is correct
2. Verify environment (dev uses sandbox bot)
3. Check user phone number is registered
4. View logs: `docker-compose logs app`

### Migrations Failing

```bash
# Reset to specific revision
poetry run alembic downgrade <revision>

# Generate new migration
make migrate-create MSG="fix schema"
```

## Security

- **API Keys**: Encrypted at rest using Fernet encryption
- **Authentication**: Phone-based user authentication
- **Authorization**: Role-based access control (RBAC)
- **Database**: Connection pooling and prepared statements
- **Logging**: No sensitive data in logs (ASCII-only for Docker compatibility)
- **Docker**: Non-root user, minimal attack surface

## Performance

- **Async Operations**: All I/O operations are asynchronous
- **Connection Pooling**: Configurable database pool (default: 10-30 connections)
- **Concurrent Checks**: Services checked in parallel
- **Image Size**: <300MB Docker image with multi-stage builds
- **Resource Usage**: Low memory footprint, efficient scheduling

## Production Deployment

### Recommended Setup

- PostgreSQL 13+ with replication
- 2+ application instances behind load balancer
- Separate database for each environment (dev/stage/prod)
- Monitoring with Prometheus/Grafana
- Log aggregation with ELK stack

### Environment-Specific Configuration

**Development:**
- Uses sandbox Telegram bot
- Console logging with colors
- Full error messages
- Lower check frequencies

**Production:**
- Uses main Telegram bot
- JSON logging for aggregation
- Minimal error messages
- Optimized check frequencies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass: `make test`
5. Format code: `make format`
6. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Contact the development team
- See `Architecture.md` for detailed technical documentation

## Changelog

### Version 1.0.0
- Initial release
- Health check monitoring with retry logic
- API credit monitoring (OpenRouter)
- Telegram bot integration
- Alert aggregation and deduplication
- Recovery notifications
- Jalali calendar reports
- Docker deployment
- Comprehensive test suite
