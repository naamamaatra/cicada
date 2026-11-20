"""
Interactive Plotly Charts for SentinelOps AI Dashboard.
Engineered with 'design-taste-frontend' visual design principles.
"""
import pandas as pd
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


def create_metric_history_chart(
    history_df: pd.DataFrame,
    metric_col: str,
    title: str,
    unit: str = "%",
    threshold_warn: float = 70.0,
    threshold_crit: float = 90.0,
):
    """
    Renders high-contrast dark telemetry trend chart with subtle threshold bands.
    """
    if not HAS_PLOTLY or history_df.empty or metric_col not in history_df.columns:
        return None

    fig = go.Figure()

    nodes = history_df["source_id"].unique()
    colors = ["#38BDF8", "#34D399", "#A78BFA"]  # Cyan, Emerald, Purple luminous accents

    for i, node in enumerate(nodes):
        node_df = history_df[history_df["source_id"] == node].sort_values("timestamp_utc")
        fig.add_trace(go.Scatter(
            x=node_df["timestamp_utc"],
            y=node_df[metric_col],
            mode="lines+markers",
            name=f"{node}",
            line=dict(color=colors[i % len(colors)], width=2.2),
            marker=dict(size=4.5, symbol="circle")
        ))

    # Threshold horizontal reference bands
    fig.add_hline(
        y=threshold_warn,
        line_dash="dot",
        line_color="rgba(245, 158, 11, 0.7)",
        annotation_text=f"Fair Warning ({threshold_warn}{unit})",
        annotation_font_size=10,
        annotation_position="top right"
    )
    fig.add_hline(
        y=threshold_crit,
        line_dash="dash",
        line_color="rgba(239, 68, 68, 0.8)",
        annotation_text=f"Critical Breach ({threshold_crit}{unit})",
        annotation_font_size=10,
        annotation_position="bottom right"
    )

    fig.update_layout(
        title=dict(text=title, font=dict(family="Plus Jakarta Sans, sans-serif", size=13, color="#E6EDF3")),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(family="JetBrains Mono, monospace", size=9, color="#8B949E")
        ),
        yaxis=dict(
            title=f"{unit}",
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#8B949E")
        ),
        margin=dict(l=15, r=15, t=35, b=15),
        height=260,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family="JetBrains Mono, monospace", size=10, color="#94A3B8")
        ),
        paper_bgcolor="#0F1218",
        plot_bgcolor="#0F1218",
    )
    return fig
