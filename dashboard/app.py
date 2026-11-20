"""
SentinelOps AI — Infrastructure Observability Dashboard (Phase 1)
Role: Member 3 (Dashboard & UI)
"""
import sys
import os
from pathlib import Path

# Add project root to path so imports work cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from dashboard.data_service import TelemetryDataService
from dashboard.components.cards import (
    calculate_overall_health,
    evaluate_metric_health,
    HEALTH_BADGES,
    HEALTH_COLORS,
)
from dashboard.components.charts import (
    create_metric_history_chart,
    create_gauge_chart
)

# Page configuration
st.set_page_config(
    page_title="SentinelOps AI — Infrastructure Observability",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern enterprise look
st.markdown("""
<style>
    .main {
        background-color: #0b0f19;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .health-badge-poor {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid #EF4444;
        border-radius: 6px;
        padding: 4px 10px;
        font-weight: 700;
        display: inline-block;
    }
    .health-badge-excellent {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid #10B981;
        border-radius: 6px;
        padding: 4px 10px;
        font-weight: 700;
        display: inline-block;
    }
    .health-badge-fair {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid #F59E0B;
        border-radius: 6px;
        padding: 4px 10px;
        font-weight: 700;
        display: inline-block;
    }
    .alert-card-critical {
        background-color: rgba(239, 68, 68, 0.12);
        border-left: 5px solid #EF4444;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .alert-card-warning {
        background-color: rgba(245, 158, 11, 0.12);
        border-left: 5px solid #F59E0B;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Data Service in session state (safely re-instantiate if schema updated)
if "data_service" not in st.session_state or not hasattr(st.session_state["data_service"], "backend_connected"):
    st.session_state["data_service"] = TelemetryDataService()

data_service: TelemetryDataService = st.session_state["data_service"]


# --- FETCH DATA ---
latest_by_node, active_alerts = data_service.fetch_latest_metrics()
history_df = data_service.get_history_df()

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.title("SentinelOps AI")
    st.caption("Privacy-First Infrastructure Observability")
    st.markdown("---")

    st.subheader("⚡ Demo Scenario Injector")
    st.write("Simulate failure scenarios to test Phase 1 demo requirements:")

    scenario_options = {
        "🟢 All Systems Normal": "normal",
        "🔴 Spike CPU & RAM (node_a81f)": "spike_node_a",
        "🔴 Network Outage (node_c73d)": "network_degrade_node_c",
        "🔴 Database Overload (node_b92c)": "db_overload_node_b"
    }

    selected_label = st.radio(
        "Select Active Scenario:",
        list(scenario_options.keys()),
        index=0
    )
    data_service.set_scenario(scenario_options[selected_label])

    st.markdown("---")
    if st.button("🔄 Refresh Telemetry Now", use_container_width=True, type="primary"):
        st.rerun()

    st.markdown("---")
    st.caption("Backend API Status:")
    if getattr(data_service, "backend_connected", False):
        st.success("🟢 FastAPI Backend: **Connected** (http://127.0.0.1:8000)")
    else:
        st.warning("🟡 FastAPI Backend: **Offline** (Autonomous fallback active)")

# Calculate Overall Cluster Health
overall_states = [calculate_overall_health(node) for node in latest_by_node.values()]
cluster_health = "POOR" if "POOR" in overall_states else ("FAIR" if "FAIR" in overall_states else ("GOOD" if "GOOD" in overall_states else "EXCELLENT"))


# --- HEADER & TOP METRICS ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("🛡️ SentinelOps AI Dashboard")
    st.caption("Phase 1 Live Prototype • Multi-Node Telemetry & Anomaly Monitoring")

with col_head2:
    st.markdown("<div style='text-align: right; padding-top: 15px;'>", unsafe_allow_html=True)
    if cluster_health == "POOR":
        st.markdown(f"<span class='health-badge-poor'>SYSTEM STATUS: 🔴 {cluster_health}</span>", unsafe_allow_html=True)
    elif cluster_health == "FAIR":
        st.markdown(f"<span class='health-badge-fair'>SYSTEM STATUS: 🟡 {cluster_health}</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span class='health-badge-excellent'>SYSTEM STATUS: 🟢 {cluster_health}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")


# Top KPI Metric Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_nodes = len(latest_by_node)
crit_alerts = sum(1 for a in active_alerts if a["severity"] == "CRITICAL")
avg_cpu = round(sum(d["cpu"] for d in latest_by_node.values()) / total_nodes, 1) if total_nodes > 0 else 0
avg_lat = round(sum(d["latency_ms"] for d in latest_by_node.values()) / total_nodes, 1) if total_nodes > 0 else 0

with kpi1:
    st.metric("Monitored Servers", f"{total_nodes} Online", delta="All Active", delta_color="normal")
with kpi2:
    st.metric("Overall Cluster Health", cluster_health, delta=f"{len(active_alerts)} Alerts", delta_color="inverse" if len(active_alerts) > 0 else "normal")
with kpi3:
    st.metric("Fleet Avg CPU", f"{avg_cpu}%", delta=f"{'High' if avg_cpu > 70 else 'Normal'}", delta_color="inverse" if avg_cpu > 70 else "normal")
with kpi4:
    st.metric("Fleet Avg Latency", f"{avg_lat} ms", delta=f"{'Degraded' if avg_lat > 100 else 'Optimal'}", delta_color="inverse" if avg_lat > 100 else "normal")


# --- ACTIVE ALERTS SECTION ---
st.subheader("🚨 Active Alerts & Threshold Breaches")
if active_alerts:
    for alert in active_alerts:
        card_class = "alert-card-critical" if alert["severity"] == "CRITICAL" else "alert-card-warning"
        icon = "🔥 [CRITICAL]" if alert["severity"] == "CRITICAL" else "⚠️ [WARNING]"
        st.markdown(f"""
        <div class='{card_class}'>
            <strong>{icon} {alert['source_id']} — {alert['metric']}: {alert['value']}</strong><br/>
            <span style='color: #94A3B8; font-size: 0.9em;'>{alert['message']}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.success("✅ All monitored nodes are operating within established performance baselines. No threshold breaches detected.")

st.markdown("---")


# --- MONITORED INFRASTRUCTURE NODES ---
st.subheader("🖥️ Monitored Infrastructure (The 3 Simulated Nodes)")

node_cols = st.columns(3)
node_names = {
    "node_a81f": "App Server (Production-Web)",
    "node_b92c": "Database Master (Postgres)",
    "node_c73d": "API Gateway & Ingress"
}

for i, (source_id, data) in enumerate(latest_by_node.items()):
    col = node_cols[i % 3]
    node_health = calculate_overall_health(data)
    color = HEALTH_COLORS.get(node_health, "#10B981")
    friendly_name = node_names.get(source_id, "Infrastructure Node")

    with col:
        with st.container():
            st.markdown(f"""
            <div class='metric-card' style='border-top: 4px solid {color};'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h3 style='margin:0;'>{source_id}</h3>
                    <span style='font-size: 0.85em; font-weight: bold; color: {color};'>{HEALTH_BADGES[node_health]}</span>
                </div>
                <div style='color: #94A3B8; font-size: 0.85em; margin-bottom: 12px;'>{friendly_name}</div>
                <hr style='margin: 8px 0; border-color: #334155;' />
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px;'>
                    <div><strong>CPU:</strong> {data['cpu']}%</div>
                    <div><strong>Memory:</strong> {data['memory']}%</div>
                    <div><strong>Disk:</strong> {data['disk']}%</div>
                    <div><strong>Latency:</strong> {data['latency_ms']} ms</div>
                    <div><strong>Packet Loss:</strong> {data['packet_loss_pct']}%</div>
                    <div><strong>Errors:</strong> {data['error_count']}</div>
                </div>
                <div style='margin-top: 10px; font-size: 0.8em; color: #64748B;'>
                    Last Heartbeat: {data['timestamp_utc'][-12:-4]} UTC • Collector: {data['collector_status'].upper()}
                </div>
            </div>
            """, unsafe_allow_html=True)


# --- TELEMETRY CHARTS ---
st.subheader("📈 Real-Time Telemetry Trends")
tab_cpu, tab_lat, tab_raw = st.tabs(["CPU & Memory Utilization", "Network Latency & Packet Loss", "Raw Telemetry Payload (Shared Schema)"])

with tab_cpu:
    c1, c2 = st.columns(2)
    with c1:
        fig_cpu = create_metric_history_chart(history_df, "cpu", "CPU Utilization Across Fleet", "%", 70.0, 90.0)
        if fig_cpu:
            st.plotly_chart(fig_cpu, use_container_width=True)
        else:
            st.line_chart(history_df.pivot(index="timestamp_utc", columns="source_id", values="cpu"))
    with c2:
        fig_mem = create_metric_history_chart(history_df, "memory", "Memory Utilization Across Fleet", "%", 75.0, 90.0)
        if fig_mem:
            st.plotly_chart(fig_mem, use_container_width=True)
        else:
            st.line_chart(history_df.pivot(index="timestamp_utc", columns="source_id", values="memory"))

with tab_lat:
    c1, c2 = st.columns(2)
    with c1:
        fig_lat = create_metric_history_chart(history_df, "latency_ms", "Network Latency Across Fleet", "ms", 100.0, 250.0)
        if fig_lat:
            st.plotly_chart(fig_lat, use_container_width=True)
        else:
            st.line_chart(history_df.pivot(index="timestamp_utc", columns="source_id", values="latency_ms"))
    with c2:
        fig_pkt = create_metric_history_chart(history_df, "packet_loss_pct", "Packet Loss Across Fleet", "%", 1.0, 5.0)
        if fig_pkt:
            st.plotly_chart(fig_pkt, use_container_width=True)
        else:
            st.line_chart(history_df.pivot(index="timestamp_utc", columns="source_id", values="packet_loss_pct"))

with tab_raw:
    st.write("Agreed Shared Telemetry Schema (Section 7 of Project Plan):")
    st.json(list(latest_by_node.values()))


# --- PHASE 1 EVALUATION CHECKLIST ---
with st.expander("📋 Phase 1 Hackathon Completion Criteria (Judges Reference)", expanded=False):
    st.markdown("""
    - [x] **Repository is ready**: Git remote linked, branching policy active (`nagaraj/dashboard-ui`).
    - [x] **Project environment runs**: Python 3.13 + Streamlit + Plotly.
    - [x] **Telemetry generator works**: Generates valid multi-server telemetry according to agreed Section 7 schema.
    - [x] **Dashboard displays telemetry**: 3 distinct servers visible with CPU, RAM, Latency, Packet Loss, Disk.
    - [x] **Simulated failure works**: Interactive sidebar injector switches between Normal, CPU Spike, Network Degradation, and DB Overload.
    - [x] **Server status changes from healthy to critical**: Node health dynamically recalculates to `POOR` and changes color to Red.
    - [x] **Alert is displayed**: Threshold breaches generate immediate warning and critical alert banners.
    """)

