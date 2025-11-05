"""
Tests for Plotly chart generation
"""
import pytest
from datetime import datetime
from utils.plotly_charts import PlotlyChartGenerator


class TestPlotlyChartGenerator:
    """Test Plotly chart generation"""

    @pytest.fixture
    def chart_gen(self):
        """Create chart generator instance"""
        return PlotlyChartGenerator(theme="plotly_white")

    def test_create_uptime_chart(self, chart_gen):
        """Test uptime chart generation"""
        services_data = [
            ("Service A", 99.95),
            ("Service B", 99.50),
            ("Service C", 98.00),
        ]

        result = chart_gen.create_uptime_chart(services_data)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_uptime_chart_empty(self, chart_gen):
        """Test uptime chart with empty data"""
        result = chart_gen.create_uptime_chart([])
        assert result is None

    def test_create_credit_usage_chart(self, chart_gen):
        """Test credit usage pie chart"""
        services_data = [
            ("OpenRouter", 45.50),
            ("Anthropic", 30.25),
            ("OpenAI", 24.25),
        ]

        result = chart_gen.create_credit_usage_chart(services_data)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_credit_usage_chart_empty(self, chart_gen):
        """Test credit usage chart with empty data"""
        result = chart_gen.create_credit_usage_chart([])
        assert result is None

    def test_create_alerts_timeline(self, chart_gen):
        """Test alerts timeline chart"""
        alert_data = [
            (datetime(2025, 11, 4, 10, 0), "critical", "Service A"),
            (datetime(2025, 11, 4, 11, 30), "warning", "Service B"),
            (datetime(2025, 11, 4, 14, 15), "info", "Service C"),
        ]

        result = chart_gen.create_alerts_timeline(alert_data)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_alerts_timeline_empty(self, chart_gen):
        """Test alerts timeline with empty data"""
        result = chart_gen.create_alerts_timeline([])
        assert result is None

    def test_create_multi_metric_dashboard(self, chart_gen):
        """Test multi-metric dashboard"""
        uptime_data = [("Service A", 99.95), ("Service B", 99.50)]
        credit_data = [("Service A", 100.0), ("Service B", 75.5)]
        alert_counts = {"critical": 5, "warning": 10, "info": 20}

        result = chart_gen.create_multi_metric_dashboard(
            uptime_data, credit_data, alert_counts
        )

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_trend_chart(self, chart_gen):
        """Test trend chart generation"""
        timestamps = [
            datetime(2025, 11, 4, i, 0) for i in range(24)
        ]
        values = [95.0 + i * 0.2 for i in range(24)]

        result = chart_gen.create_trend_chart(timestamps, values)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_trend_chart_empty(self, chart_gen):
        """Test trend chart with empty data"""
        result = chart_gen.create_trend_chart([], [])
        assert result is None

    def test_create_comparison_heatmap(self, chart_gen):
        """Test comparison heatmap"""
        service_names = ["Service A", "Service B", "Service C"]
        metrics = ["Uptime %", "Response Time", "Error Rate"]
        values = [
            [99.9, 99.5, 98.0],
            [120, 150, 200],
            [0.1, 0.5, 2.0],
        ]

        result = chart_gen.create_comparison_heatmap(
            service_names, metrics, values
        )

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_create_comparison_heatmap_empty(self, chart_gen):
        """Test heatmap with empty data"""
        result = chart_gen.create_comparison_heatmap([], [], [])
        assert result is None

    def test_chart_generator_themes(self):
        """Test different themes"""
        themes = ["plotly", "plotly_white", "plotly_dark"]

        for theme in themes:
            gen = PlotlyChartGenerator(theme=theme)
            assert gen.theme == theme

            # Test that charts can be generated with different themes
            result = gen.create_uptime_chart([("Test", 99.9)])
            assert result is not None


class TestChartEdgeCases:
    """Test edge cases for chart generation"""

    @pytest.fixture
    def chart_gen(self):
        """Create chart generator instance"""
        return PlotlyChartGenerator()

    def test_single_data_point(self, chart_gen):
        """Test charts with single data point"""
        result = chart_gen.create_uptime_chart([("Service A", 99.9)])
        assert result is not None

        result = chart_gen.create_credit_usage_chart([("Service A", 100.0)])
        assert result is not None

    def test_large_dataset(self, chart_gen):
        """Test charts with large datasets"""
        # 100 services
        services_data = [(f"Service {i}", 95.0 + i * 0.05) for i in range(100)]
        result = chart_gen.create_uptime_chart(services_data)
        assert result is not None

    def test_extreme_values(self, chart_gen):
        """Test charts with extreme values"""
        # Very low uptime
        result = chart_gen.create_uptime_chart([("Service A", 0.01)])
        assert result is not None

        # Perfect uptime
        result = chart_gen.create_uptime_chart([("Service A", 100.0)])
        assert result is not None

        # Very large credits
        result = chart_gen.create_credit_usage_chart([("Service A", 999999.99)])
        assert result is not None

    def test_special_characters_in_names(self, chart_gen):
        """Test service names with special characters"""
        services_data = [
            ("Service-A (Production)", 99.9),
            ("Service_B [Staging]", 99.5),
            ("Service#C & D", 98.0),
        ]

        result = chart_gen.create_uptime_chart(services_data)
        assert result is not None
