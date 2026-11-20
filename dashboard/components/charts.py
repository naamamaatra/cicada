"""
Interactive chart helpers for SentinelOps AI Dashboard.
"""
import pandas as pd
try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def create_metric_history_chart(history_df: pd.DataFrame, metric_col: str, title: str, unit: str = "%", threshold_warn: float = 70.0, threshold_crit: float = 90.0):
    """
    Renders an interactive Plotly line chart with warning and critical threshold bands.
    """
    if not HAS_PLOTLY or history_df.empty:
        return None

    fig = go.Figure()

    # Add line for each node
    nodes = history_df["source_id"].unique()
    colors = ["#3B82F6", "#10B981", "#8B5CF6"]

    for i, node in enumerate(nodes):
        node_df = history_df[history_df["source_id"] == node].sort_values("timestamp_utc")
        fig.add_trace(go.Scatter(
            x=node_df["timestamp_utc"],
            y=node_df[metric_col],
            mode="lines+markers",
            name=f"{node}",
            line=dict(color=colors[i % len(colors)], width=2.5),
            marker=dict(size=4)
        ))

    # Add threshold lines
    fig.add_hline(y=threshold_warn, line_dash="dash", line_color="#F59E0B", annotation_text=f"Fair Warning ({threshold_warn}{unit})")
    fig.add_hline(y=threshold_crit, line_dash="dash", line_color="#EF4444", annotation_text=f"Poor Critical ({threshold_crit}{unit})")

    fig.update_layout(
        title=title,
        xaxis_title="Time (UTC)",
        yaxis_title=f"Value ({unit})",
        margin=dict(l=20, r=20, t=40, b=20),
        height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0.4)",
        plot_bgcolor="rgba(15, 23, 42, 0.4)"
    )
    return fig


def create_gauge_chart(value: float, title: str, unit: str = "%", max_val: float = 100.0, warn_val: float = 70.0, crit_val: float = 90.0):
    """
    Renders a radial gauge chart for real-time KPIs.
    """
    if not HAS_PLOTLY:
        return None

    if value >= crit_val:
        color = "#EF4444"
    elif value >= warn_val:
        color = "#F59E0B"
    else:
        color = "#10B981"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 14}},
        number={'suffix': f" {unit}", 'font': {'size': 20, 'color': color}},
        gauge={
            'axis': {'range': [0, max_val], 'tickwidth': 1, 'tickcolor': "#94A3B8"},
            'bar': {'color': color},
            'bgcolor': "rgba(30, 41, 59, 0.7)",
            'borderwidth': 1,
            'bordercolor': "#334155",
            'steps': [
                {'range': [0, warn_val], 'color': "rgba(16, 185, 129, 0.15)"},
                {'range': [warn_val, crit_val], 'color': "rgba(245, 158, 11, 0.15)"},
                {'range': [crit_val, max_val], 'color': "rgba(239, 68, 68, 0.2)"}
            ],
        }
    ))

    fig.update_layout(
        height=180,
        margin=dict(l=15, r=15, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={'color': "#F8FAFC"}
    )
    return fig
