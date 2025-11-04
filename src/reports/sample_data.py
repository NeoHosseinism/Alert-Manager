"""
Sample data generators for report preview and testing
"""
import random
from datetime import datetime, timedelta
from typing import List

from reports.generator import ServiceStats, AlertStats


def generate_sample_health_service(
    name: str,
    environment: str = "production",
    uptime_range: tuple = (95.0, 100.0)
) -> ServiceStats:
    """
    Generate sample health check service statistics

    Args:
        name: Service name
        environment: Service environment
        uptime_range: Range of uptime percentages (min, max)

    Returns:
        ServiceStats with realistic health check data
    """
    uptime = random.uniform(*uptime_range)
    total_checks = random.randint(200, 300)  # Checks per day (every ~5 min)
    successful = int(total_checks * (uptime / 100))
    failed = total_checks - successful

    # Generate hourly check counts (24 hours)
    hourly_checks = [random.randint(8, 12) for _ in range(24)]

    # Response times
    avg_response = random.randint(50, 500)

    # Downtime incidents
    if uptime < 99.9:
        incidents = random.randint(1, 5)
        downtime_per_incident = random.uniform(5, 30)
        total_downtime = incidents * downtime_per_incident
    else:
        incidents = 0
        total_downtime = 0.0

    return ServiceStats(
        service_name=name,
        service_type="health_check",
        environment=environment,
        total_checks=total_checks,
        successful_checks=successful,
        failed_checks=failed,
        uptime_percent=uptime,
        avg_response_time=avg_response,
        downtime_incidents=incidents,
        total_downtime_minutes=total_downtime,
        hourly_checks=hourly_checks
    )


def generate_sample_credit_service(
    name: str,
    environment: str = "production",
    starting_balance: float = 1000.0,
    usage_rate: float = 50.0
) -> ServiceStats:
    """
    Generate sample API credit service statistics

    Args:
        name: Service name
        environment: Service environment
        starting_balance: Starting credit balance
        usage_rate: Daily usage rate

    Returns:
        ServiceStats with realistic credit data
    """
    credits_used = usage_rate + random.uniform(-usage_rate * 0.2, usage_rate * 0.2)
    ending = starting_balance - credits_used

    # Generate hourly usage pattern (24 hours)
    hourly_usage = []
    for hour in range(24):
        # Higher usage during business hours (9-17)
        if 9 <= hour <= 17:
            usage = random.uniform(2.0, 5.0)
        else:
            usage = random.uniform(0.5, 2.0)
        hourly_usage.append(usage)

    # Generate daily usage for the week
    daily_usage = [
        usage_rate * random.uniform(0.8, 1.2)
        for _ in range(7)
    ]

    return ServiceStats(
        service_name=name,
        service_type="api_credit",
        environment=environment,
        starting_credits=starting_balance,
        ending_credits=ending,
        credits_used=credits_used,
        avg_daily_usage=usage_rate,
        daily_usage=daily_usage,
        hourly_checks=hourly_usage  # Reuse for hourly pattern
    )


def generate_sample_alert_stats(
    num_services: int,
    service_names: List[str],
    severity: str = "mixed"
) -> AlertStats:
    """
    Generate sample alert statistics

    Args:
        num_services: Number of services
        service_names: List of service names
        severity: Alert severity distribution ("low", "medium", "high", "mixed")

    Returns:
        AlertStats with realistic alert data
    """
    if severity == "low":
        total = random.randint(5, 15)
        critical = random.randint(0, 2)
        warning = random.randint(2, 5)
    elif severity == "medium":
        total = random.randint(15, 40)
        critical = random.randint(2, 8)
        warning = random.randint(5, 15)
    elif severity == "high":
        total = random.randint(40, 100)
        critical = random.randint(10, 30)
        warning = random.randint(15, 40)
    else:  # mixed
        total = random.randint(10, 50)
        critical = random.randint(1, 10)
        warning = random.randint(3, 20)

    info = total - critical - warning
    resolved = int(total * random.uniform(0.7, 0.95))

    # Generate top alert sources
    top_services = []
    remaining_alerts = total
    for service in random.sample(service_names, min(5, len(service_names))):
        count = random.randint(1, min(remaining_alerts, total // 2))
        top_services.append((service, count))
        remaining_alerts -= count

    top_services.sort(key=lambda x: x[1], reverse=True)

    # Average resolution time
    avg_resolution = random.uniform(10, 60)

    return AlertStats(
        total_alerts=total,
        critical_alerts=critical,
        warning_alerts=warning,
        info_alerts=info,
        resolved_alerts=resolved,
        avg_resolution_time_minutes=avg_resolution,
        top_services=top_services
    )


def generate_daily_sample_data(date: datetime = None) -> dict:
    """
    Generate complete sample data for a daily report

    Args:
        date: Date for the report (defaults to today)

    Returns:
        Dictionary with date, services, and alerts
    """
    if date is None:
        date = datetime.utcnow()

    # Mix of healthy and problematic services
    services = [
        generate_sample_health_service("Payment API", "production", (99.5, 100.0)),
        generate_sample_health_service("Auth Service", "production", (99.8, 100.0)),
        generate_sample_health_service("Database", "production", (99.9, 100.0)),
        generate_sample_health_service("Cache Service", "production", (95.0, 98.0)),
        generate_sample_health_service("API Gateway", "staging", (98.0, 99.9)),
        generate_sample_credit_service("OpenRouter API", "production", 408.15, 17.85),
        generate_sample_credit_service("Anthropic API", "production", 1000.0, 50.0),
        generate_sample_credit_service("OpenAI API", "dev", 250.0, 25.0),
    ]

    service_names = [s.service_name for s in services]
    alerts = generate_sample_alert_stats(len(services), service_names, "low")

    return {
        "date": date,
        "services": services,
        "alerts": alerts
    }


def generate_weekly_sample_data(start_date: datetime = None) -> dict:
    """
    Generate complete sample data for a weekly report

    Args:
        start_date: Start date for the week (defaults to last Monday)

    Returns:
        Dictionary with start_date, end_date, services, and alerts
    """
    if start_date is None:
        today = datetime.utcnow()
        start_date = today - timedelta(days=today.weekday())  # Last Monday

    end_date = start_date + timedelta(days=6)

    services = [
        generate_sample_health_service("Payment API", "production", (99.7, 100.0)),
        generate_sample_health_service("Auth Service", "production", (99.5, 100.0)),
        generate_sample_health_service("Database", "production", (99.9, 100.0)),
        generate_sample_health_service("Cache Service", "production", (96.0, 99.0)),
        generate_sample_health_service("API Gateway", "production", (98.5, 99.9)),
        generate_sample_health_service("WebSocket Server", "production", (97.0, 99.5)),
        generate_sample_health_service("Background Jobs", "production", (99.0, 100.0)),
        generate_sample_health_service("Email Service", "production", (99.8, 100.0)),
        generate_sample_credit_service("OpenRouter API", "production", 408.15, 17.85 * 7),
        generate_sample_credit_service("Anthropic API", "production", 1000.0, 50.0 * 7),
        generate_sample_credit_service("OpenAI API", "production", 500.0, 35.0 * 7),
    ]

    service_names = [s.service_name for s in services]
    alerts = generate_sample_alert_stats(len(services), service_names, "medium")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "services": services,
        "alerts": alerts
    }


def generate_monthly_sample_data(month: datetime = None) -> dict:
    """
    Generate complete sample data for a monthly report

    Args:
        month: Month for the report (first day of month, defaults to current month)

    Returns:
        Dictionary with month, services, and alerts
    """
    if month is None:
        today = datetime.utcnow()
        month = datetime(today.year, today.month, 1)

    # More comprehensive service list for monthly report
    services = [
        # High performers
        generate_sample_health_service("Payment API", "production", (99.95, 100.0)),
        generate_sample_health_service("Auth Service", "production", (99.9, 100.0)),
        generate_sample_health_service("Database Primary", "production", (99.99, 100.0)),

        # Good performers
        generate_sample_health_service("API Gateway", "production", (99.5, 99.9)),
        generate_sample_health_service("Cache Service", "production", (99.3, 99.8)),
        generate_sample_health_service("WebSocket Server", "production", (99.0, 99.7)),
        generate_sample_health_service("Background Jobs", "production", (99.4, 99.9)),

        # Services needing attention
        generate_sample_health_service("Legacy API", "production", (95.0, 98.0)),
        generate_sample_health_service("Third-party Integration", "production", (96.0, 98.5)),

        # Staging/Dev
        generate_sample_health_service("API Gateway", "staging", (98.0, 99.5)),
        generate_sample_health_service("Test Environment", "dev", (95.0, 99.0)),

        # Credit services with monthly usage
        generate_sample_credit_service("OpenRouter API", "production", 408.15, 17.85 * 30),
        generate_sample_credit_service("Anthropic API", "production", 2000.0, 50.0 * 30),
        generate_sample_credit_service("OpenAI API", "production", 1500.0, 35.0 * 30),
        generate_sample_credit_service("Google AI", "production", 800.0, 20.0 * 30),
    ]

    service_names = [s.service_name for s in services]
    alerts = generate_sample_alert_stats(len(services), service_names, "mixed")

    return {
        "month": month,
        "services": services,
        "alerts": alerts
    }
