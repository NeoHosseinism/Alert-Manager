"""
Professional chart generation using Plotly for reports
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io


class PlotlyChartGenerator:
    """Generate professional charts using Plotly"""

    def __init__(self, theme: str = "plotly_dark"):
        """
        Initialize chart generator

        Args:
            theme: Plotly theme (plotly, plotly_white, plotly_dark, etc.)
        """
        self.theme = theme
        self.default_colors = px.colors.qualitative.Plotly

    def create_uptime_chart(
        self,
        services_data: List[Tuple[str, float]],
        title: str = "Service Uptime %"
    ) -> bytes:
        """
        Create a horizontal bar chart for uptime percentages

        Args:
            services_data: List of (service_name, uptime_percent) tuples
            title: Chart title

        Returns:
            PNG image bytes
        """
        if not services_data:
            return None

        names, uptimes = zip(*services_data)

        # Color code based on uptime
        colors = []
        for uptime in uptimes:
            if uptime >= 99.9:
                colors.append('#00D084')  # Green
            elif uptime >= 99.0:
                colors.append('#FFA500')  # Orange
            else:
                colors.append('#FF4444')  # Red

        fig = go.Figure(go.Bar(
            x=uptimes,
            y=names,
            orientation='h',
            marker=dict(color=colors),
            text=[f'{u:.2f}%' for u in uptimes],
            textposition='auto',
        ))

        fig.update_layout(
            title=title,
            xaxis_title="Uptime %",
            yaxis_title="Service",
            template=self.theme,
            height=max(400, len(services_data) * 40),
            xaxis=dict(range=[0, 100]),
        )

        return self._fig_to_bytes(fig)

    def create_credit_usage_chart(
        self,
        services_data: List[Tuple[str, float]],
        title: str = "Credit Usage by Service"
    ) -> bytes:
        """
        Create a pie chart for credit usage distribution

        Args:
            services_data: List of (service_name, credits_used) tuples
            title: Chart title

        Returns:
            PNG image bytes
        """
        if not services_data:
            return None

        names, credits = zip(*services_data)

        fig = go.Figure(go.Pie(
            labels=names,
            values=credits,
            hole=0.3,
            textinfo='label+percent',
            textposition='auto',
        ))

        fig.update_layout(
            title=title,
            template=self.theme,
            height=500,
        )

        return self._fig_to_bytes(fig)

    def create_alerts_timeline(
        self,
        alert_data: List[Tuple[datetime, str, str]],
        title: str = "Alerts Timeline"
    ) -> bytes:
        """
        Create a timeline chart for alerts

        Args:
            alert_data: List of (timestamp, severity, service_name) tuples
            title: Chart title

        Returns:
            PNG image bytes
        """
        if not alert_data:
            return None

        timestamps, severities, services = zip(*alert_data)

        # Map severity to color and y-position
        severity_map = {
            'critical': ('#FF4444', 3),
            'warning': ('#FFA500', 2),
            'info': ('#4169E1', 1),
        }

        colors = [severity_map.get(s.lower(), ('#808080', 0))[0] for s in severities]
        y_positions = [severity_map.get(s.lower(), ('#808080', 0))[1] for s in severities]

        fig = go.Figure(go.Scatter(
            x=timestamps,
            y=y_positions,
            mode='markers',
            marker=dict(
                size=12,
                color=colors,
                line=dict(width=1, color='white')
            ),
            text=[f"{s}<br>{svc}" for s, svc in zip(severities, services)],
            hovertemplate='%{text}<br>%{x}<extra></extra>',
        ))

        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis=dict(
                tickmode='array',
                tickvals=[1, 2, 3],
                ticktext=['Info', 'Warning', 'Critical'],
            ),
            template=self.theme,
            height=400,
        )

        return self._fig_to_bytes(fig)

    def create_multi_metric_dashboard(
        self,
        uptime_data: List[Tuple[str, float]],
        credit_data: List[Tuple[str, float]],
        alert_counts: Dict[str, int],
        title: str = "Service Health Dashboard"
    ) -> bytes:
        """
        Create a comprehensive dashboard with multiple metrics

        Args:
            uptime_data: List of (service_name, uptime_percent) tuples
            credit_data: List of (service_name, credits_remaining) tuples
            alert_counts: Dict of {severity: count}
            title: Dashboard title

        Returns:
            PNG image bytes
        """
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Service Uptime',
                'Alert Distribution',
                'Credit Status',
                'System Health'
            ),
            specs=[
                [{'type': 'bar'}, {'type': 'pie'}],
                [{'type': 'bar'}, {'type': 'indicator'}]
            ]
        )

        # 1. Uptime bar chart
        if uptime_data:
            names, uptimes = zip(*uptime_data)
            colors = ['#00D084' if u >= 99.9 else '#FFA500' if u >= 99.0 else '#FF4444'
                     for u in uptimes]

            fig.add_trace(
                go.Bar(
                    x=list(names),
                    y=list(uptimes),
                    marker=dict(color=colors),
                    showlegend=False
                ),
                row=1, col=1
            )
            fig.update_yaxes(range=[0, 100], row=1, col=1)

        # 2. Alert pie chart
        if alert_counts:
            fig.add_trace(
                go.Pie(
                    labels=list(alert_counts.keys()),
                    values=list(alert_counts.values()),
                    marker=dict(colors=['#FF4444', '#FFA500', '#4169E1']),
                    showlegend=True
                ),
                row=1, col=2
            )

        # 3. Credit bar chart
        if credit_data:
            names, credits = zip(*credit_data)
            fig.add_trace(
                go.Bar(
                    x=list(names),
                    y=list(credits),
                    marker=dict(color='#4169E1'),
                    showlegend=False
                ),
                row=2, col=1
            )

        # 4. Overall health indicator
        if uptime_data:
            avg_uptime = sum(u for _, u in uptime_data) / len(uptime_data)
            color = '#00D084' if avg_uptime >= 99.9 else '#FFA500' if avg_uptime >= 99.0 else '#FF4444'

            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=avg_uptime,
                    title={'text': "Avg Uptime %"},
                    delta={'reference': 99.9},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': color},
                        'steps': [
                            {'range': [0, 99], 'color': "rgba(255,68,68,0.3)"},
                            {'range': [99, 99.9], 'color': "rgba(255,165,0,0.3)"},
                            {'range': [99.9, 100], 'color': "rgba(0,208,132,0.3)"}
                        ],
                    }
                ),
                row=2, col=2
            )

        fig.update_layout(
            title_text=title,
            template=self.theme,
            height=800,
            showlegend=True,
        )

        return self._fig_to_bytes(fig)

    def create_trend_chart(
        self,
        timestamps: List[datetime],
        values: List[float],
        title: str = "Trend Analysis",
        y_label: str = "Value"
    ) -> bytes:
        """
        Create a line chart showing trends over time

        Args:
            timestamps: List of datetime values
            values: List of metric values
            title: Chart title
            y_label: Y-axis label

        Returns:
            PNG image bytes
        """
        if not timestamps or not values:
            return None

        fig = go.Figure(go.Scatter(
            x=timestamps,
            y=values,
            mode='lines+markers',
            line=dict(color='#4169E1', width=2),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(65,105,225,0.2)',
        ))

        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title=y_label,
            template=self.theme,
            height=400,
        )

        return self._fig_to_bytes(fig)

    def create_comparison_heatmap(
        self,
        service_names: List[str],
        metrics: List[str],
        values: List[List[float]],
        title: str = "Service Metrics Heatmap"
    ) -> bytes:
        """
        Create a heatmap comparing multiple metrics across services

        Args:
            service_names: List of service names
            metrics: List of metric names
            values: 2D array of values [metrics][services]
            title: Chart title

        Returns:
            PNG image bytes
        """
        if not values:
            return None

        fig = go.Figure(go.Heatmap(
            z=values,
            x=service_names,
            y=metrics,
            colorscale='RdYlGn',
            text=values,
            texttemplate='%{text:.1f}',
            textfont={"size": 10},
        ))

        fig.update_layout(
            title=title,
            template=self.theme,
            height=max(300, len(metrics) * 50),
        )

        return self._fig_to_bytes(fig)

    def _fig_to_bytes(self, fig: go.Figure, format: str = "png") -> bytes:
        """
        Convert plotly figure to image bytes

        Args:
            fig: Plotly figure
            format: Image format (png, jpg, etc.)

        Returns:
            Image bytes
        """
        img_bytes = fig.to_image(format=format, width=1200, height=None, scale=2)
        return img_bytes
