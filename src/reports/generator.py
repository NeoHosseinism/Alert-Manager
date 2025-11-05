"""
Report generator for scheduled periodic reports (daily, weekly, monthly)
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from utils.charts import (
    create_horizontal_bar_chart,
    create_sparkline,
    create_trend_indicator,
    create_uptime_indicator,
    create_credit_gauge,
    create_timeline,
    create_comparison_table
)
from utils.jalali import format_jalali_datetime
from utils.formatting import format_currency


@dataclass
class ServiceStats:
    """Statistics for a service over a period"""
    service_name: str
    service_type: str  # health_check or api_credit
    environment: str

    # Health check stats
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    uptime_percent: float = 0.0
    avg_response_time: Optional[float] = None
    downtime_incidents: int = 0
    total_downtime_minutes: float = 0.0

    # Credit stats
    starting_credits: Optional[float] = None
    ending_credits: Optional[float] = None
    credits_used: Optional[float] = None
    avg_daily_usage: Optional[float] = None

    # Trend data
    hourly_checks: List[int] = None  # For sparkline
    daily_usage: List[float] = None  # For sparkline


@dataclass
class AlertStats:
    """Alert statistics for a period"""
    total_alerts: int = 0
    critical_alerts: int = 0
    warning_alerts: int = 0
    info_alerts: int = 0
    resolved_alerts: int = 0
    avg_resolution_time_minutes: Optional[float] = None
    top_services: List[tuple] = None  # List of (service_name, alert_count)


class ReportGenerator:
    """Generate formatted reports for different time periods"""

    def generate_daily_report(
        self,
        date: datetime,
        services: List[ServiceStats],
        alerts: AlertStats
    ) -> str:
        """
        Generate a daily report

        Args:
            date: Date for the report
            services: List of service statistics
            alerts: Alert statistics

        Returns:
            Formatted report string
        """
        lines = []

        # Header
        lines.append("=" * 50)
        lines.append("📊 DAILY SERVICE REPORT")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Date: {date.strftime('%Y-%m-%d')}")
        lines.append(f"      {format_jalali_datetime(date, include_time=False)} (Persian)")
        lines.append("")

        # Summary
        total_services = len(services)
        health_services = [s for s in services if s.service_type == "health_check"]
        credit_services = [s for s in services if s.service_type == "api_credit"]

        lines.append("📈 Summary")
        lines.append("─" * 50)
        lines.append(f"Total Services Monitored: {total_services}")
        lines.append(f"  • Health Check Services: {len(health_services)}")
        lines.append(f"  • API Credit Services: {len(credit_services)}")
        lines.append(f"Total Alerts: {alerts.total_alerts}")
        lines.append(f"  • Critical: {alerts.critical_alerts}")
        lines.append(f"  • Warning: {alerts.warning_alerts}")
        lines.append("")

        # Health Check Services
        if health_services:
            lines.append("🏥 Health Check Services")
            lines.append("─" * 50)
            lines.append("")

            # Uptime chart
            uptime_data = [
                (s.service_name, s.uptime_percent)
                for s in health_services
            ]
            lines.append("Uptime % (Last 24 Hours):")
            lines.append(create_horizontal_bar_chart(uptime_data, max_width=25))
            lines.append("")

            # Detailed stats
            for service in health_services:
                lines.append(f"• {service.service_name} ({service.environment})")
                lines.append(f"  {create_uptime_indicator(service.uptime_percent)}")
                lines.append(f"  Checks: {service.successful_checks}/{service.total_checks} successful")

                if service.avg_response_time:
                    lines.append(f"  Avg Response: {service.avg_response_time:.0f}ms")

                if service.downtime_incidents > 0:
                    lines.append(f"  Downtime: {service.downtime_incidents} incidents ({service.total_downtime_minutes:.1f} min)")

                # Sparkline for hourly checks
                if service.hourly_checks:
                    sparkline = create_sparkline(service.hourly_checks, width=24)
                    lines.append(f"  Activity: {sparkline} (hourly)")

                lines.append("")

        # API Credit Services
        if credit_services:
            lines.append("💳 API Credit Services")
            lines.append("─" * 50)
            lines.append("")

            for service in credit_services:
                lines.append(f"• {service.service_name} ({service.environment})")

                if service.ending_credits is not None and service.starting_credits is not None:
                    # Show credit gauge
                    total = service.starting_credits
                    remaining = service.ending_credits
                    lines.append(f"  {create_credit_gauge(remaining, total, width=20)}")
                    lines.append(f"  Remaining: {format_currency(remaining)}")

                    # Show usage
                    if service.credits_used:
                        lines.append(f"  Used Today: {format_currency(service.credits_used)}")

                    # Show trend
                    if service.starting_credits != service.ending_credits:
                        trend = create_trend_indicator(
                            service.ending_credits,
                            service.starting_credits
                        )
                        lines.append(f"  Change: {trend}")

                    # Sparkline for daily usage pattern
                    if service.daily_usage:
                        sparkline = create_sparkline(service.daily_usage, width=24)
                        lines.append(f"  Usage Pattern: {sparkline} (hourly)")

                lines.append("")

        # Alert Summary
        if alerts.total_alerts > 0:
            lines.append("🚨 Alert Summary")
            lines.append("─" * 50)
            lines.append(f"Total Alerts: {alerts.total_alerts}")
            lines.append(f"Resolved: {alerts.resolved_alerts}/{alerts.total_alerts}")

            if alerts.avg_resolution_time_minutes:
                lines.append(f"Avg Resolution Time: {alerts.avg_resolution_time_minutes:.1f} minutes")

            if alerts.top_services:
                lines.append("")
                lines.append("Top Alert Sources:")
                for service_name, count in alerts.top_services[:5]:
                    lines.append(f"  • {service_name}: {count} alerts")

            lines.append("")

        # Footer
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append("=" * 50)

        return "\n".join(lines)

    def generate_weekly_report(
        self,
        start_date: datetime,
        end_date: datetime,
        services: List[ServiceStats],
        alerts: AlertStats
    ) -> str:
        """
        Generate a weekly report

        Args:
            start_date: Week start date
            end_date: Week end date
            services: List of service statistics
            alerts: Alert statistics

        Returns:
            Formatted report string
        """
        lines = []

        # Header
        lines.append("=" * 50)
        lines.append("📊 WEEKLY SERVICE REPORT")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        lines.append(f"        {format_jalali_datetime(start_date, include_time=False)} to")
        lines.append(f"        {format_jalali_datetime(end_date, include_time=False)} (Persian)")
        lines.append("")

        # Executive Summary
        total_services = len(services)
        avg_uptime = sum(s.uptime_percent for s in services if s.service_type == "health_check") / max(len([s for s in services if s.service_type == "health_check"]), 1)

        lines.append("📈 Executive Summary")
        lines.append("─" * 50)
        lines.append(f"Services Monitored: {total_services}")
        lines.append(f"Average Uptime: {avg_uptime:.2f}%")
        lines.append(f"Total Alerts: {alerts.total_alerts}")
        lines.append(f"Alert Resolution Rate: {(alerts.resolved_alerts / max(alerts.total_alerts, 1) * 100):.1f}%")
        lines.append("")

        # Uptime Leaderboard
        health_services = [s for s in services if s.service_type == "health_check"]
        if health_services:
            lines.append("🏆 Uptime Leaderboard")
            lines.append("─" * 50)
            sorted_services = sorted(health_services, key=lambda s: s.uptime_percent, reverse=True)

            leaderboard_data = [
                (f"{i+1}. {s.service_name}", s.uptime_percent)
                for i, s in enumerate(sorted_services[:10])
            ]
            lines.append(create_horizontal_bar_chart(leaderboard_data, max_width=25))
            lines.append("")

        # Service Health Table
        if health_services:
            lines.append("🏥 Service Health Summary")
            lines.append("─" * 50)
            lines.append("")

            headers = ["Service", "Uptime", "Incidents", "Total Downtime"]
            rows = []
            for s in sorted(health_services, key=lambda x: x.uptime_percent, reverse=True):
                rows.append([
                    s.service_name[:20],
                    f"{s.uptime_percent:.2f}%",
                    str(s.downtime_incidents),
                    f"{s.total_downtime_minutes:.0f}m"
                ])

            lines.append(create_comparison_table(headers, rows, max_width=20))
            lines.append("")

        # Credit Usage Summary
        credit_services = [s for s in services if s.service_type == "api_credit"]
        if credit_services:
            lines.append("💳 Credit Usage Summary")
            lines.append("─" * 50)
            lines.append("")

            for service in credit_services:
                lines.append(f"• {service.service_name}")

                if service.credits_used:
                    lines.append(f"  Weekly Usage: {format_currency(service.credits_used)}")

                    if service.avg_daily_usage:
                        lines.append(f"  Avg Daily: {format_currency(service.avg_daily_usage)}")

                    # Weekly usage sparkline
                    if service.daily_usage:
                        sparkline = create_sparkline(service.daily_usage, width=7)
                        lines.append(f"  Week Pattern: {sparkline} (daily)")

                if service.ending_credits is not None:
                    lines.append(f"  Remaining: {format_currency(service.ending_credits)}")

                lines.append("")

        # Alert Analysis
        if alerts.total_alerts > 0:
            lines.append("🚨 Alert Analysis")
            lines.append("─" * 50)

            severity_data = [
                ("Critical", alerts.critical_alerts),
                ("Warning", alerts.warning_alerts),
                ("Info", alerts.info_alerts),
            ]
            lines.append("")
            lines.append("Alerts by Severity:")
            lines.append(create_horizontal_bar_chart(severity_data, max_width=20, show_values=False))
            lines.append(f"  Critical: {alerts.critical_alerts}")
            lines.append(f"  Warning: {alerts.warning_alerts}")
            lines.append(f"  Info: {alerts.info_alerts}")
            lines.append("")

            if alerts.top_services:
                lines.append("Most Affected Services:")
                for service_name, count in alerts.top_services[:5]:
                    pct = (count / alerts.total_alerts * 100)
                    lines.append(f"  • {service_name}: {count} alerts ({pct:.1f}%)")

            lines.append("")

        # Footer
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append("=" * 50)

        return "\n".join(lines)

    def generate_monthly_report(
        self,
        month: datetime,
        services: List[ServiceStats],
        alerts: AlertStats
    ) -> str:
        """
        Generate a monthly report

        Args:
            month: Month for the report (first day of month)
            services: List of service statistics
            alerts: Alert statistics

        Returns:
            Formatted report string
        """
        lines = []

        month_name = month.strftime("%B %Y")

        # Header
        lines.append("=" * 50)
        lines.append("📊 MONTHLY SERVICE REPORT")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Period: {month_name}")
        lines.append(f"        {format_jalali_datetime(month, include_time=False)} (Persian)")
        lines.append("")

        # Executive Dashboard
        total_services = len(services)
        health_services = [s for s in services if s.service_type == "health_check"]
        credit_services = [s for s in services if s.service_type == "api_credit"]

        avg_uptime = sum(s.uptime_percent for s in health_services) / max(len(health_services), 1) if health_services else 0

        lines.append("📈 Executive Dashboard")
        lines.append("─" * 50)
        lines.append(f"Services Monitored: {total_services}")
        lines.append(f"  • Health Checks: {len(health_services)}")
        lines.append(f"  • Credit Tracking: {len(credit_services)}")
        lines.append("")
        lines.append(f"Overall Uptime: {avg_uptime:.2f}%")
        lines.append(f"Total Checks Performed: {sum(s.total_checks for s in health_services)}")
        lines.append(f"Total Alerts: {alerts.total_alerts}")
        lines.append(f"  • Critical: {alerts.critical_alerts}")
        lines.append(f"  • Warning: {alerts.warning_alerts}")
        lines.append(f"  • Info: {alerts.info_alerts}")
        lines.append("")

        # Top Performers
        if health_services:
            lines.append("⭐ Top Performers (Highest Uptime)")
            lines.append("─" * 50)
            top_performers = sorted(health_services, key=lambda s: s.uptime_percent, reverse=True)[:5]

            for i, service in enumerate(top_performers, 1):
                medal = ["🥇", "🥈", "🥉", "🏅", "🏅"][i-1]
                lines.append(f"{medal} {service.service_name}")
                lines.append(f"   {create_uptime_indicator(service.uptime_percent)}")
                lines.append(f"   {service.successful_checks:,} successful checks")

            lines.append("")

        # Services Needing Attention
        services_with_issues = [s for s in health_services if s.uptime_percent < 99.0 or s.downtime_incidents > 3]
        if services_with_issues:
            lines.append("⚠️ Services Needing Attention")
            lines.append("─" * 50)

            for service in sorted(services_with_issues, key=lambda s: s.uptime_percent):
                lines.append(f"• {service.service_name}")
                lines.append(f"  {create_uptime_indicator(service.uptime_percent)}")
                lines.append(f"  {service.downtime_incidents} downtime incidents")
                lines.append(f"  Total downtime: {service.total_downtime_minutes:.0f} minutes")

            lines.append("")

        # Monthly Credit Report
        if credit_services:
            lines.append("💰 Monthly Credit Report")
            lines.append("─" * 50)

            total_spent = sum(s.credits_used or 0 for s in credit_services)
            lines.append(f"Total Spent: {format_currency(total_spent)}")
            lines.append("")

            # Spending by service
            spending_data = [
                (s.service_name, s.credits_used or 0)
                for s in credit_services if s.credits_used
            ]
            if spending_data:
                # Calculate percentages
                spending_pct = [
                    (name, (spent / total_spent * 100) if total_spent > 0 else 0)
                    for name, spent in spending_data
                ]
                lines.append("Spending Distribution:")
                lines.append(create_horizontal_bar_chart(spending_pct, max_width=25))
                lines.append("")

            # Individual service details
            for service in credit_services:
                if service.credits_used:
                    lines.append(f"• {service.service_name}")
                    lines.append(f"  Monthly Usage: {format_currency(service.credits_used)}")

                    if service.avg_daily_usage:
                        lines.append(f"  Avg Daily: {format_currency(service.avg_daily_usage)}")

                    if service.ending_credits:
                        lines.append(f"  Current Balance: {format_currency(service.ending_credits)}")

                    lines.append("")

        # Alert Trends
        if alerts.total_alerts > 0:
            lines.append("🚨 Alert Trends")
            lines.append("─" * 50)
            lines.append(f"Total Alerts: {alerts.total_alerts}")
            lines.append(f"Resolution Rate: {(alerts.resolved_alerts / alerts.total_alerts * 100):.1f}%")

            if alerts.avg_resolution_time_minutes:
                lines.append(f"Avg Resolution Time: {alerts.avg_resolution_time_minutes:.1f} minutes")

            lines.append("")

            # Top alert sources
            if alerts.top_services:
                lines.append("Top Alert Sources:")
                for service_name, count in alerts.top_services[:7]:
                    lines.append(f"  • {service_name}: {count} alerts")

            lines.append("")

        # Recommendations
        lines.append("💡 Recommendations")
        lines.append("─" * 50)

        if services_with_issues:
            lines.append("• Review services with uptime below 99%")

        if alerts.critical_alerts > 10:
            lines.append("• Investigate root causes of critical alerts")

        high_spenders = [s for s in credit_services if s.credits_used and s.credits_used > 100]
        if high_spenders:
            lines.append(f"• Monitor credit usage for {len(high_spenders)} high-usage services")

        if not (services_with_issues or alerts.critical_alerts > 10 or high_spenders):
            lines.append("• All systems operating normally ✅")

        lines.append("")

        # Footer
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append("=" * 50)

        return "\n".join(lines)
