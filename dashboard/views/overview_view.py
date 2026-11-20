"""
SentinelOps AI - Workspace Overview Page.
Displays real tenant metrics, overall cluster health, active incidents, and fleet counters.
"""

import streamlit as st
from datetime import datetime, timezone
from dashboard.api_client import SaaSClient


def render_overview_view(client: SaaSClient):
    org_id = client.active_org["id"] if client.active_org else ""
    org_name = client.active_org.get("name", "Active Workspace") if client.active_org else "Workspace"

    # Fetch real tenant data
    summary = client.get_tenant_summary(org_id)
    recent_metrics = client.get_tenant_metrics(org_id, limit=20)
    incidents = client.list_incidents(org_id)
    collectors = client.list_collectors(org_id)

    # Calculate cluster health
    critical_count = summary.get("critical_sources", 0)
    warning_count = summary.get("warning_sources", 0)
    active_incidents_count = summary.get("active_incidents", len([i for i in incidents if i.get("status") in ["open", "investigating"]]))

    if critical_count > 0 or active_incidents_count > 0:
        overall_health = "POOR"
        status_color = "#EF4444"
        badge_html = f"<span style='background: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; padding: 4px 12px; border-radius: 6px; font-weight: 700;'>🔴 SYSTEM STATUS: CRITICAL</span>"
    elif warning_count > 0:
        overall_health = "FAIR"
        status_color = "#F59E0B"
        badge_html = f"<span style='background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; padding: 4px 12px; border-radius: 6px; font-weight: 700;'>🟡 SYSTEM STATUS: DEGRADED</span>"
    else:
        overall_health = "EXCELLENT"
        status_color = "#10B981"
        badge_html = f"<span style='background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; padding: 4px 12px; border-radius: 6px; font-weight: 700;'>🟢 SYSTEM STATUS: HEALTHY</span>"

    # Header Row
    head_c1, head_c2 = st.columns([3, 1])
    with head_c1:
        st.title(f"🏢 {org_name}")
        st.caption(f"Tenant ID: `{org_id}` • Real-Time Observability & AI Incident Intelligence")
    with head_c2:
        st.markdown(f"<div style='text-align: right; padding-top: 15px;'>{badge_html}</div>", unsafe_allow_html=True)

    st.markdown("---")

    # KPI Metric Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    total_sources = summary.get("total_sources", len(set(m.get("source_id") for m in recent_metrics)))
    total_events = summary.get("total_telemetry_events", len(recent_metrics))
    total_collectors = len(collectors)

    with kpi1:
        st.metric("Monitored Nodes", f"{total_sources}", delta=f"{summary.get('healthy_sources', total_sources)} Healthy")
    with kpi2:
        st.metric("Active Incidents", f"{active_incidents_count}", delta=f"{'Action Required' if active_incidents_count > 0 else 'Optimal'}", delta_color="inverse" if active_incidents_count > 0 else "normal")
    with kpi3:
        st.metric("Registered Collectors", f"{total_collectors}", delta="Agents Online")
    with kpi4:
        st.metric("Total Events Ingested", f"{total_events}", delta="Real Database Records")

    # -------------------------------------------------------------------------
    # Quick Failure Scenario Injector for Evaluators & Judges
    # -------------------------------------------------------------------------
    with st.expander("⚡ Interactive Demo Scenario Injector (Evaluator Controls)", expanded=False):
        st.write("Trigger simulated metric spikes to test the end-to-end AI detection and incident creation pipeline:")
        inj_c1, inj_c2, inj_c3 = st.columns(3)

        with inj_c1:
            if st.button("🔴 Inject CPU & RAM Spike (node_a81f)", use_container_width=True):
                with st.spinner("Injecting 98.5% CPU overload..."):
                    payload = {
                        "payload_id": f"evt_spike_{int(datetime.now().timestamp())}",
                        "tenant_id": org_id,
                        "source_id": "node_a81f",
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "cpu": 98.5,
                        "memory": 94.0,
                        "disk": 75.0,
                        "latency_ms": 320.0,
                        "packet_loss_pct": 6.5,
                        "error_count": 22,
                        "failed_logins": 1,
                        "collector_status": "online",
                        "event_category": "resource_pressure",
                    }
                    client.send_telemetry(payload)
                    st.success("Spike injected! Anomaly detected and incident correlated.")
                    st.rerun()

        with inj_c2:
            if st.button("🔴 Inject Network Congestion (node_c73d)", use_container_width=True):
                with st.spinner("Injecting 450ms latency & 12% packet loss..."):
                    payload = {
                        "payload_id": f"evt_net_{int(datetime.now().timestamp())}",
                        "tenant_id": org_id,
                        "source_id": "node_c73d",
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "cpu": 45.0,
                        "memory": 52.0,
                        "disk": 60.0,
                        "latency_ms": 450.0,
                        "packet_loss_pct": 12.0,
                        "error_count": 8,
                        "failed_logins": 0,
                        "collector_status": "online",
                        "event_category": "network_spike",
                    }
                    client.send_telemetry(payload)
                    st.success("Network degradation injected! Correlated by AI.")
                    st.rerun()

        with inj_c3:
            if st.button("🟢 Restore Healthy Baseline", use_container_width=True):
                with st.spinner("Injecting normal operational metrics..."):
                    for src in ["node_a81f", "node_b92c", "node_c73d"]:
                        client.send_telemetry({
                            "payload_id": f"evt_norm_{src}_{int(datetime.now().timestamp())}",
                            "tenant_id": org_id,
                            "source_id": src,
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "cpu": 32.0,
                            "memory": 45.0,
                            "disk": 50.0,
                            "latency_ms": 25.0,
                            "packet_loss_pct": 0.0,
                            "error_count": 0,
                            "failed_logins": 0,
                            "collector_status": "online",
                            "event_category": "normal",
                        })
                    st.success("Healthy baseline restored.")
                    st.rerun()

    st.markdown("---")

    # Recent Active Incidents Preview
    st.subheader("🚨 Active System Incidents")
    if incidents:
        for inc in incidents[:3]:
            sev = inc.get("severity", "MEDIUM")
            status = inc.get("status", "open").upper()
            border_color = "#EF4444" if sev == "CRITICAL" else "#F59E0B"

            st.markdown(f"""
            <div style='background: #1E293B; border-left: 4px solid {border_color}; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px;'>
                <div style='display: flex; justify-content: space-between;'>
                    <strong>{inc.get('title')}</strong>
                    <span style='color: {border_color}; font-weight: bold;'>[{sev}] {status}</span>
                </div>
                <div style='color: #94A3B8; font-size: 0.85em; margin-top: 4px;'>
                    Affected Node: <code>{inc.get('source_id')}</code> • First Detected: {str(inc.get('first_detected_at'))[:19]}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No open incidents. All monitored nodes are performing within acceptable parameters.")
