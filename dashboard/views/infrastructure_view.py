"""
SentinelOps AI - Infrastructure & Fleet Monitoring View.
Displays node health, live telemetry, and historical trend charts for the active tenant.
"""

import streamlit as st
import pandas as pd
from dashboard.api_client import SaaSClient
from dashboard.components.cards import calculate_overall_health, HEALTH_BADGES, HEALTH_COLORS
from dashboard.components.charts import create_metric_history_chart


def render_infrastructure_view(client: SaaSClient):
    org_id = client.active_org["id"] if client.active_org else ""
    st.title("🖥️ Monitored Infrastructure")
    st.caption("Real-time telemetry and health diagnostics scoped to your organization.")

    # Fetch tenant metrics
    metrics = client.get_tenant_metrics(org_id, limit=200)

    if not metrics:
        st.info("📡 No telemetry records found for this workspace yet. Enroll a collector or send a test packet to begin monitoring.")
        return

    # Group by source_id to get latest per node
    nodes_latest = {}
    for r in reversed(metrics):  # chronological order to newest
        nodes_latest[r["source_id"]] = r

    # Node Health Cards
    st.subheader(f"Monitored Nodes ({len(nodes_latest)} Active)")
    node_cols = st.columns(min(len(nodes_latest), 3))

    friendly_names = {
        "node_a81f": "App Server (Production-Web)",
        "node_b92c": "Database Master (Postgres)",
        "node_c73d": "API Gateway & Ingress",
    }

    for i, (source_id, data) in enumerate(nodes_latest.items()):
        col = node_cols[i % len(node_cols)]
        health = calculate_overall_health(data)
        color = HEALTH_COLORS.get(health, "#10B981")
        friendly = friendly_names.get(source_id, "Infrastructure Node")

        with col:
            st.markdown(f"""
            <div style='background: #1E293B; border-radius: 8px; border-top: 4px solid {color}; padding: 14px; margin-bottom: 12px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h4 style='margin:0;'>{source_id}</h4>
                    <span style='color: {color}; font-weight: bold;'>{HEALTH_BADGES.get(health, health)}</span>
                </div>
                <div style='color: #94A3B8; font-size: 0.85em; margin-bottom: 8px;'>{friendly}</div>
                <hr style='border-color: #334155; margin: 6px 0;'/>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 0.9em;'>
                    <div><strong>CPU:</strong> {data['cpu']}%</div>
                    <div><strong>RAM:</strong> {data['memory']}%</div>
                    <div><strong>Disk:</strong> {data['disk']}%</div>
                    <div><strong>Latency:</strong> {data['latency_ms']} ms</div>
                    <div><strong>Pkt Loss:</strong> {data['packet_loss_pct']}%</div>
                    <div><strong>Errors:</strong> {data['error_count']}</div>
                </div>
                <div style='margin-top: 8px; font-size: 0.75em; color: #64748B;'>
                    Collector: {data.get('collector_status', 'ONLINE').upper()} • Timestamp: {data.get('timestamp_utc')[:19]}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Historical Telemetry Trends
    st.subheader("📈 Historical Metric Trends")
    df = pd.DataFrame(metrics)
    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        df = df.sort_values("timestamp_utc")

        t1, t2, t3 = st.tabs(["CPU & Memory Utilization", "Network Latency & Packet Loss", "Raw Database Records"])

        with t1:
            c1, c2 = st.columns(2)
            with c1:
                fig_cpu = create_metric_history_chart(df, "cpu", "CPU Utilization Across Fleet", "%", 70.0, 90.0)
                if fig_cpu:
                    st.plotly_chart(fig_cpu, use_container_width=True)
                else:
                    st.line_chart(df.pivot(index="timestamp_utc", columns="source_id", values="cpu"))
            with c2:
                fig_mem = create_metric_history_chart(df, "memory", "Memory Utilization Across Fleet", "%", 75.0, 90.0)
                if fig_mem:
                    st.plotly_chart(fig_mem, use_container_width=True)
                else:
                    st.line_chart(df.pivot(index="timestamp_utc", columns="source_id", values="memory"))

        with t2:
            c1, c2 = st.columns(2)
            with c1:
                fig_lat = create_metric_history_chart(df, "latency_ms", "Network Latency Across Fleet", "ms", 100.0, 250.0)
                if fig_lat:
                    st.plotly_chart(fig_lat, use_container_width=True)
                else:
                    st.line_chart(df.pivot(index="timestamp_utc", columns="source_id", values="latency_ms"))
            with c2:
                fig_pkt = create_metric_history_chart(df, "packet_loss_pct", "Packet Loss Percentage", "%", 1.0, 5.0)
                if fig_pkt:
                    st.plotly_chart(fig_pkt, use_container_width=True)
                else:
                    st.line_chart(df.pivot(index="timestamp_utc", columns="source_id", values="packet_loss_pct"))

        with t3:
            st.dataframe(df[["payload_id", "source_id", "cpu", "memory", "disk", "latency_ms", "packet_loss_pct", "error_count", "timestamp_utc"]], use_container_width=True)
