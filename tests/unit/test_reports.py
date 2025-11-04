"""
Tests for report generation system
"""
import pytest
from datetime import datetime, timedelta
from reports.generator import ReportGenerator, ServiceStats, AlertStats


class TestReportGenerator:
    """Test report generation"""

    @pytest.fixture
    def report_gen(self):
        """Create report generator instance"""
        return ReportGenerator()

    @pytest.fixture
    def sample_service_stats(self):
        """Sample service statistics"""
        return [
            ServiceStats(
                service_name="API Gateway",
                service_type="health_check",
                environment="production",
                total_checks=288,
                successful_checks=287,
                failed_checks=1,
                uptime_percent=99.65,
                avg_response_time=145.5,
                downtime_incidents=1,
                total_downtime_minutes=5.0,
                hourly_checks=[12] * 24,
            ),
            ServiceStats(
                service_name="OpenRouter",
                service_type="api_credit",
                environment="production",
                starting_credits=100.0,
                ending_credits=85.50,
                credits_used=14.50,
                avg_daily_usage=2.07,
                daily_usage=[1.5, 2.0, 2.5, 3.0, 2.0, 1.5, 2.0],
            ),
        ]

    @pytest.fixture
    def sample_alert_stats(self):
        """Sample alert statistics"""
        return AlertStats(
            total_alerts=15,
            critical_alerts=2,
            warning_alerts=8,
            info_alerts=5,
            resolved_alerts=13,
            avg_resolution_time_minutes=25.5,
            top_services=[
                ("API Gateway", 6),
                ("Database", 4),
                ("Cache", 3),
                ("Worker", 2),
            ]
        )

    def test_generate_daily_report(self, report_gen, sample_service_stats, sample_alert_stats):
        """Test daily report generation"""
        date = datetime(2025, 11, 4)

        report = report_gen.generate_daily_report(
            date=date,
            services=sample_service_stats,
            alerts=sample_alert_stats
        )

        assert isinstance(report, str)
        assert len(report) > 0

        # Check header
        assert "DAILY SERVICE REPORT" in report
        assert "2025-11-04" in report

        # Check service names appear
        assert "API Gateway" in report
        assert "OpenRouter" in report

        # Check alert stats
        assert "Total Alerts: 15" in report
        assert "Critical: 2" in report

    def test_generate_weekly_report(self, report_gen, sample_service_stats, sample_alert_stats):
        """Test weekly report generation"""
        start_date = datetime(2025, 11, 1)
        end_date = datetime(2025, 11, 7)

        report = report_gen.generate_weekly_report(
            start_date=start_date,
            end_date=end_date,
            services=sample_service_stats,
            alerts=sample_alert_stats
        )

        assert isinstance(report, str)
        assert len(report) > 0

        # Check header
        assert "WEEKLY SERVICE REPORT" in report
        assert "2025-11-01" in report
        assert "2025-11-07" in report

        # Check executive summary
        assert "Executive Summary" in report
        assert "Average Uptime" in report

    def test_generate_monthly_report(self, report_gen, sample_service_stats, sample_alert_stats):
        """Test monthly report generation"""
        month = datetime(2025, 11, 1)

        report = report_gen.generate_monthly_report(
            month=month,
            services=sample_service_stats,
            alerts=sample_alert_stats
        )

        assert isinstance(report, str)
        assert len(report) > 0

        # Check header
        assert "MONTHLY SERVICE REPORT" in report
        assert "November 2025" in report

        # Check executive dashboard
        assert "Executive Dashboard" in report
        assert "Services Monitored" in report

        # Check recommendations section
        assert "Recommendations" in report

    def test_daily_report_empty_services(self, report_gen):
        """Test daily report with no services"""
        date = datetime(2025, 11, 4)
        alerts = AlertStats(total_alerts=0)

        report = report_gen.generate_daily_report(
            date=date,
            services=[],
            alerts=alerts
        )

        assert isinstance(report, str)
        assert "Total Services Monitored: 0" in report

    def test_daily_report_only_health_checks(self, report_gen, sample_alert_stats):
        """Test daily report with only health check services"""
        services = [
            ServiceStats(
                service_name="Service A",
                service_type="health_check",
                environment="production",
                total_checks=100,
                successful_checks=99,
                failed_checks=1,
                uptime_percent=99.0,
            ),
        ]

        report = report_gen.generate_daily_report(
            date=datetime(2025, 11, 4),
            services=services,
            alerts=sample_alert_stats
        )

        assert "Health Check Services: 1" in report
        assert "API Credit Services: 0" in report

    def test_daily_report_only_credits(self, report_gen, sample_alert_stats):
        """Test daily report with only credit services"""
        services = [
            ServiceStats(
                service_name="OpenRouter",
                service_type="api_credit",
                environment="production",
                starting_credits=100.0,
                ending_credits=90.0,
                credits_used=10.0,
            ),
        ]

        report = report_gen.generate_daily_report(
            date=datetime(2025, 11, 4),
            services=services,
            alerts=sample_alert_stats
        )

        assert "Health Check Services: 0" in report
        assert "API Credit Services: 1" in report

    def test_weekly_report_uptime_calculation(self, report_gen):
        """Test weekly report average uptime calculation"""
        services = [
            ServiceStats(
                service_name="Service A",
                service_type="health_check",
                environment="production",
                uptime_percent=99.9,
                total_checks=100,
                successful_checks=100,
                failed_checks=0,
            ),
            ServiceStats(
                service_name="Service B",
                service_type="health_check",
                environment="production",
                uptime_percent=99.0,
                total_checks=100,
                successful_checks=99,
                failed_checks=1,
            ),
        ]

        alerts = AlertStats(total_alerts=5, resolved_alerts=4)

        report = report_gen.generate_weekly_report(
            start_date=datetime(2025, 11, 1),
            end_date=datetime(2025, 11, 7),
            services=services,
            alerts=alerts
        )

        # Average should be (99.9 + 99.0) / 2 = 99.45%
        assert "99.4" in report or "99.5" in report

    def test_monthly_report_top_performers(self, report_gen):
        """Test monthly report top performers section"""
        services = [
            ServiceStats(
                service_name=f"Service {i}",
                service_type="health_check",
                environment="production",
                uptime_percent=99.9 - (i * 0.1),
                total_checks=1000,
                successful_checks=999 - i,
                failed_checks=i,
                downtime_incidents=i,
                total_downtime_minutes=i * 5.0,
            )
            for i in range(10)
        ]

        alerts = AlertStats(total_alerts=10, resolved_alerts=8)

        report = report_gen.generate_monthly_report(
            month=datetime(2025, 11, 1),
            services=services,
            alerts=alerts
        )

        # Should show top 5 performers
        assert "Top Performers" in report
        # Best service should have medal emoji
        assert "🥇" in report or "Service 0" in report

    def test_monthly_report_services_needing_attention(self, report_gen):
        """Test services needing attention section"""
        services = [
            ServiceStats(
                service_name="Problem Service",
                service_type="health_check",
                environment="production",
                uptime_percent=95.0,  # Below 99%
                total_checks=1000,
                successful_checks=950,
                failed_checks=50,
                downtime_incidents=10,  # More than 3
                total_downtime_minutes=120.0,
            ),
        ]

        alerts = AlertStats(total_alerts=5, resolved_alerts=4)

        report = report_gen.generate_monthly_report(
            month=datetime(2025, 11, 1),
            services=services,
            alerts=alerts
        )

        assert "Services Needing Attention" in report
        assert "Problem Service" in report

    def test_report_footer_timestamp(self, report_gen, sample_service_stats, sample_alert_stats):
        """Test that reports include generation timestamp"""
        report = report_gen.generate_daily_report(
            date=datetime(2025, 11, 4),
            services=sample_service_stats,
            alerts=sample_alert_stats
        )

        assert "Generated:" in report
        assert "UTC" in report


class TestServiceStats:
    """Test ServiceStats dataclass"""

    def test_create_health_check_stats(self):
        """Test creating health check service stats"""
        stats = ServiceStats(
            service_name="Test Service",
            service_type="health_check",
            environment="production",
            total_checks=100,
            successful_checks=99,
            failed_checks=1,
            uptime_percent=99.0,
        )

        assert stats.service_name == "Test Service"
        assert stats.service_type == "health_check"
        assert stats.uptime_percent == 99.0

    def test_create_credit_stats(self):
        """Test creating credit service stats"""
        stats = ServiceStats(
            service_name="OpenRouter",
            service_type="api_credit",
            environment="production",
            starting_credits=100.0,
            ending_credits=90.0,
            credits_used=10.0,
        )

        assert stats.service_name == "OpenRouter"
        assert stats.service_type == "api_credit"
        assert stats.credits_used == 10.0


class TestAlertStats:
    """Test AlertStats dataclass"""

    def test_create_alert_stats(self):
        """Test creating alert statistics"""
        stats = AlertStats(
            total_alerts=20,
            critical_alerts=5,
            warning_alerts=10,
            info_alerts=5,
            resolved_alerts=18,
            avg_resolution_time_minutes=30.5,
            top_services=[("Service A", 10), ("Service B", 5)]
        )

        assert stats.total_alerts == 20
        assert stats.critical_alerts == 5
        assert stats.resolved_alerts == 18
        assert len(stats.top_services) == 2
