# Alert Manager - System Architecture

## Overview

This document describes the architecture of Alert Manager, a production-ready solution for monitoring IT infrastructure with Telegram notifications.

## System Components

```mermaid
graph TB
    subgraph "Core Application"
        A[Main Application]
        B[APScheduler]
        C[Health Checker]
        D[Credit Monitor]
        E[Alert Engine]
        F[Report Generator]
    end

    subgraph "Communication Layer"
        G[Telegram Main Bot]
        H[Telegram Sandbox Bot]
        I[Message Formatter]
    end

    subgraph "Data Layer"
        J[(PostgreSQL Database)]
        K[Repositories]
        L[SQLAlchemy Models]
    end

    subgraph "External Services"
        M[Service Health Endpoints]
        N[OpenRouter API]
        O[Other API Providers]
    end

    A --> B
    B --> C
    B --> D
    B --> F

    C --> E
    D --> E
    E --> I
    I --> G
    I --> H

    C -.HTTP GET.-> M
    D -.HTTP GET.-> N
    D -.HTTP GET.-> O

    C --> K
    D --> K
    E --> K
    F --> K
    G --> K
    K --> L
    L --> J
```

## Alert Processing Flow

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant HC as Health Checker
    participant AE as Alert Engine
    participant DB as Database
    participant N as Notifier
    participant T as Telegram Bot
    participant U as User

    S->>HC: Trigger health check
    HC->>HC: Attempt 1 (fail)
    HC->>HC: Wait retry_delay
    HC->>HC: Attempt 2 (fail)
    HC->>HC: Wait retry_delay
    HC->>HC: Attempt 3 (fail)

    HC->>DB: Store failed health check
    HC->>AE: Create alert with retry logs

    AE->>DB: Check cooldown period
    DB-->>AE: No recent alert

    AE->>DB: Create alert record
    AE->>DB: Get authorized users
    DB-->>AE: User list

    AE->>DB: Check muted services
    DB-->>AE: Filter muted users

    AE->>N: Send notifications
    N->>T: Send Telegram messages
    T->>U: Alert notification

    AE->>DB: Update alert with notified users
```

## Recovery Detection Flow

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant HC as Health Checker
    participant DB as Database
    participant AE as Alert Engine
    participant T as Telegram Bot
    participant U as User

    S->>HC: Trigger health check
    HC->>HC: Check endpoint (success)
    HC->>DB: Store successful check

    HC->>DB: Query unresolved alerts
    DB-->>HC: Found unresolved alert

    HC->>HC: Calculate downtime
    HC->>DB: Mark alert as resolved

    HC->>AE: Trigger recovery notification
    AE->>DB: Get notified users from original alert
    DB-->>AE: User list

    AE->>T: Send recovery messages
    T->>U: Service recovered notification
```

## Database Schema

```mermaid
erDiagram
    users ||--o{ user_service_permissions : has
    services ||--o{ user_service_permissions : "granted to"
    services ||--o{ alerts : generates
    services ||--o{ health_checks : monitored
    services ||--o{ alert_archive_config : configured
    users ||--o{ muted_services : mutes
    services ||--o{ muted_services : "can be muted"

    users {
        int id PK
        string phone_number UK
        string role
        bigint telegram_user_id UK
        string telegram_username
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    services {
        int id PK
        string name
        string service_type
        string endpoint_url
        int expected_status_code
        int timeout_seconds
        string api_provider
        text api_key_encrypted
        decimal credit_threshold
        int check_interval_seconds
        int max_retries
        int retry_delay_seconds
        boolean is_active
        string environment
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    user_service_permissions {
        int id PK
        int user_id FK
        int service_id FK
        boolean can_receive_alerts
        boolean can_mute
        timestamp created_at
    }

    alerts {
        int id PK
        int service_id FK
        string alert_type
        string severity
        text message
        jsonb details
        int retry_count
        jsonb retry_logs
        int_array notified_user_ids
        jsonb telegram_message_ids
        timestamp resolved_at
        timestamp created_at
    }

    health_checks {
        int id PK
        int service_id FK
        boolean is_healthy
        int response_time_ms
        int status_code
        text error_message
        timestamp checked_at
    }

    muted_services {
        int id PK
        int user_id FK
        int service_id FK
        timestamp muted_until
        string muted_by_command
        timestamp created_at
    }

    report_schedules {
        int id PK
        string name
        string frequency
        int jalali_day_of_week
        int jalali_day_of_month
        int jalali_month
        int_array target_user_ids
        timestamp last_run_at
        timestamp next_run_at
        boolean is_active
        timestamp created_at
    }

    alert_archive_config {
        int id PK
        int service_id FK
        int archive_after_days
        boolean auto_archive_enabled
        timestamp created_at
    }
```

## Telegram Bot Interaction

```mermaid
sequenceDiagram
    participant U as User
    participant T as Telegram
    participant M as Middleware
    participant H as Handler
    participant DB as Database
    participant R as Repository

    U->>T: Send command
    T->>M: Authenticate
    M->>DB: Check telegram_user_id
    DB-->>M: User record

    alt User not found
        M->>U: Access denied message
    else User inactive
        M->>U: Account disabled message
    else User authenticated
        M->>H: Store user in context
        H->>R: Execute business logic
        R->>DB: Database operations
        DB-->>R: Results
        R-->>H: Data
        H->>U: Response message
    end
```

## Scheduled Jobs

```mermaid
gantt
    title Monitoring System Job Schedule
    dateFormat HH:mm
    axisFormat %H:%M

    section Health Checks
    Service 1 Check    :done, h1, 00:00, 5m
    Service 2 Check    :done, h2, 00:00, 5m
    Service 3 Check    :done, h3, 00:00, 5m
    Next Round         :h4, 00:05, 5m

    section Credit Monitoring
    OpenRouter Check   :done, c1, 00:00, 1h
    Next Check         :c2, 01:00, 1h

    section Reports
    Daily Report       :done, r1, 09:00, 30m
    Weekly Report      :r2, 09:00, 30m
    Monthly Report     :r3, 09:00, 30m
```

## Data Flow Diagram

```mermaid
flowchart LR
    A[External Services] -->|HTTP| B[Health Checker]
    C[API Providers] -->|HTTP| D[Credit Monitor]

    B -->|Check Results| E[Database]
    D -->|Credit Data| E

    E -->|Unresolved Alerts| F[Alert Engine]
    F -->|New Alerts| E

    F -->|Notifications| G[Telegram Notifier]
    G -->|Messages| H[Users]

    H -->|Commands| I[Telegram Bot]
    I -->|Queries| E
    E -->|Data| I
    I -->|Responses| H
```

## Component Responsibilities

### Health Checker
- Poll service health endpoints at configurable intervals
- Implement retry logic with exponential backoff
- Record response times and status codes
- Detect service failures after all retries exhausted
- Store health check history in database
- Trigger alert creation on persistent failures

### Credit Monitor
- Check API provider credit balances
- Decrypt stored API keys for authentication
- Compare remaining credits against thresholds
- Support multiple providers (OpenRouter, extensible)
- Create alerts when credits drop below threshold
- Schedule checks at configurable intervals

### Alert Engine
- Receive failure notifications from monitors
- Check alert cooldown periods to prevent spam
- Aggregate multiple alerts in time windows
- Deduplicate similar alerts
- Store alert records with full context
- Coordinate user notifications via Telegram

### Recovery Detection
- Monitor health check transitions
- Detect when previously failed services recover
- Calculate service downtime duration
- Mark alerts as resolved in database
- Send recovery notifications to affected users
- Track recovery metrics for reporting

### Telegram Bot
- Provide dual-bot support (production + sandbox)
- Authenticate users via phone number registration
- Implement role-based command access control
- Handle user commands (status, alerts, mute, etc.)
- Send proactive failure and recovery notifications
- Format messages for optimal mobile viewing

### Report Generator
- Generate periodic service health reports
- Calculate uptime percentages and metrics
- Create high-quality charts (150 DPI minimum)
- Use Jalali calendar for Persian date formatting
- Support multiple frequencies (daily to yearly)
- Deliver reports via Telegram as images

## Security Architecture

```mermaid
flowchart TB
    subgraph "External Layer"
        A[Telegram API]
        B[Monitored Services]
    end

    subgraph "Application Layer"
        C[Bot Authentication]
        D[Role-Based Access]
        E[Encrypted Storage]
    end

    subgraph "Data Layer"
        F[(Encrypted API Keys)]
        G[(User Credentials)]
        H[(Service Config)]
    end

    A -->|TLS| C
    B -->|HTTPS| C
    C --> D
    D --> E
    E --> F
    E --> G
    E --> H
```

## Deployment Architecture

```mermaid
flowchart TB
    subgraph "Production Environment"
        A[Load Balancer]
        B[App Instance 1]
        C[App Instance 2]
        D[(PostgreSQL Primary)]
        E[(PostgreSQL Replica)]
        F[Telegram API]
    end

    A --> B
    A --> C
    B --> D
    C --> D
    D --> E
    B --> F
    C --> F
```

## Error Handling Strategy

### External API Failures
- Never crash the application
- Implement timeouts on all external calls
- Use retry logic with exponential backoff
- Log errors with full context (no sensitive data)
- Degrade gracefully when services unavailable
- Alert administrators on persistent failures

### Database Failures
- Use connection pooling with health checks
- Implement automatic reconnection logic
- Cache critical data when possible
- Log database errors comprehensively
- Provide meaningful error messages to users

### Telegram API Failures
- Queue messages for retry on failure
- Implement rate limiting to avoid bans
- Handle network timeouts gracefully
- Log failed message attempts
- Notify administrators of persistent issues

## Scalability Considerations

### Horizontal Scaling
- Stateless application design
- Multiple instances behind load balancer
- Distributed scheduler coordination
- Shared PostgreSQL database

### Vertical Scaling
- Configurable connection pool sizes
- Async I/O throughout application
- Efficient database queries with indexes
- Minimal memory footprint per check

### Performance Optimization
- Concurrent health checks
- Database query result caching
- Efficient alert aggregation
- Batch notification delivery

## Monitoring & Observability

### Logging
- Structured logging with structlog
- JSON format for production
- ASCII-only output (Docker compatible)
- Log levels by environment
- No sensitive data in logs

### Metrics
- Health check success rates
- Alert creation frequency
- Notification delivery times
- Database connection pool usage
- API response times

### Alerting
- Self-monitoring capabilities
- Database connection failures
- Scheduler job failures
- High error rates
- Resource exhaustion

## Technology Choices

### Why PostgreSQL?
- ACID compliance for reliability
- Native JSON support for flexible data
- Excellent Python async support (asyncpg)
- Battle-tested in production
- No Redis needed for our use case

### Why Async Python?
- Efficient I/O operations
- Concurrent health checks
- Better resource utilization
- Modern Python best practices
- SQLAlchemy 2.0 native support

### Why Telegram?
- Free, reliable infrastructure
- Excellent mobile apps
- Bot API with rich features
- No SMS costs
- Group chat support

### Why Jalali Calendar?
- Persian/Iranian market requirement
- Cultural relevance for users
- Familiar date formats
- Holiday awareness

## Future Enhancements

### Planned Features
- Web dashboard for configuration
- Webhook support for external integrations
- Custom alert templates
- Advanced reporting with trends
- Multi-language support
- Prometheus metrics export

### Extensibility Points
- New API provider support
- Additional monitoring types
- Custom notification channels
- Plugin architecture for checks
- Custom report templates

## Glossary

- **Health Check**: HTTP request to verify service availability
- **Credit Monitor**: System tracking API usage and balance
- **Alert Aggregation**: Grouping multiple alerts in time window
- **Recovery Notification**: Message sent when service resumes
- **Cooldown Period**: Time between duplicate alerts
- **Jalali Calendar**: Persian solar calendar system
- **Role-Based Access Control (RBAC)**: Permission system by user role
- **Fernet Encryption**: Symmetric encryption for API keys
