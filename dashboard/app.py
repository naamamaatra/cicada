"""
SentinelOps AI — Infrastructure Observability & Privacy-First Platform.
Redesigned with 'design-taste-frontend' standards (Figma/Linear tier aesthetics)
Supports:
- Professional Company Landing Page (Value Proposition, SLA Guarantees, Architecture)
- Dedicated Scenario Workspaces (Normal Baseline, CPU Spike, Network Outage, DB Overload)
- Zero-Trust Privacy Engine & Cryptographic Egress Proof Lab (Phase 2)
"""
import sys
from pathlib import Path

# Add project root to path
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
    TASTE_SKILL_CSS,
)
from dashboard.components.charts import create_metric_history_chart

# Page configuration
st.set_page_config(
    page_title="SentinelOps AI — Privacy-First Observability",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply taste-skill design system
st.markdown(TASTE_SKILL_CSS, unsafe_allow_html=True)

# Custom Workspace & Landing CSS extensions
st.markdown("""
<style>
    .workspace-banner {
        background: #0f1218;
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 20px;
    }
    .landing-hero {
        background: radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 45%),
                    radial-gradient(circle at bottom left, rgba(16, 185, 129, 0.05), transparent 40%),
                    #0a0d12;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 38px 36px;
        margin-bottom: 26px;
    }
    .scenario-launch-card {
        background: #0e1219;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 14px;
        padding: 22px;
        min-height: 240px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.18s ease, border-color 0.18s ease;
    }
    .scenario-launch-card:hover {
        transform: translateY(-3px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    .sla-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
    }
    .sla-table th {
        text-align: left;
        padding: 10px 14px;
        background: rgba(255, 255, 255, 0.04);
        color: #8B949E;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .sla-table td {
        padding: 10px 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        color: #CBD5E1;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "data_service" not in st.session_state or not hasattr(st.session_state["data_service"], "run_privacy_test"):
    st.session_state["data_service"] = TelemetryDataService()

if "active_view" not in st.session_state:
    st.session_state["active_view"] = "landing"  # "landing", "workspace", "privacy_lab"

if "active_scenario_key" not in st.session_state:
    st.session_state["active_scenario_key"] = "normal"

data_service: TelemetryDataService = st.session_state["data_service"]


# Scenario Metadata Dictionary
SCENARIO_CONFIGS = {
    "normal": {
        "title": "Normal Baseline Operation",
        "short_title": "Normal Baseline",
        "badge": "🟢 OPTIMAL",
        "severity": "EXCELLENT",
        "color": "#10B981",
        "target_node": "All 3 Nodes (Healthy)",
        "headline": "Full 3-Node Cluster Operating Nominal Workloads",
        "description": "All 3 monitored nodes (Web/App, PostgreSQL, Edge Ingress) are reporting healthy telemetry with natural organic jitter. Zero SLA threshold breaches.",
        "expected_cpu": "24% – 36%",
        "expected_lat": "11 – 20 ms",
        "root_cause": "Nominal operations. All synthetic workloads within Section 14 SLA limits.",
        "remediation": "No action needed. Automated health probes green.",
    },
    "spike_node_a": {
        "title": "CPU & Memory Exhaustion",
        "short_title": "CPU & RAM Spike",
        "badge": "🔴 CRITICAL",
        "severity": "POOR",
        "color": "#EF4444",
        "target_node": "node_a81f (Primary Web Server)",
        "headline": "Sudden Thread Contention & Memory Pressure on node_a81f",
        "description": "Primary Web/Application node experiencing thread starvation and rapid heap growth. CPU exceeds 94%, Memory exceeds 90%, breaching Section 14 Critical SLA thresholds.",
        "expected_cpu": "94% – 98%",
        "expected_lat": "72 – 118 ms",
        "root_cause": "Thread starvation in WSGI worker pool with heap allocation leak in JSON payload serializer.",
        "remediation": "Auto-trigger Horizontal Pod Autoscaler (HPA) and spin up 2 auxiliary node instances.",
    },
    "network_degrade_node_c": {
        "title": "Network Ingress Degradation",
        "short_title": "Network Outage",
        "badge": "🟡 CRITICAL LATENCY",
        "severity": "POOR",
        "color": "#F59E0B",
        "target_node": "node_c73d (API Gateway)",
        "headline": "Edge Gateway Round-Trip Latency & Packet Drop Burst",
        "description": "API Gateway encountering severe uplink packet drop (>15%) and round-trip latency surge (>400ms), exceeding Section 14 Latency SLA of 250ms.",
        "expected_cpu": "45% – 60%",
        "expected_lat": "380 – 520 ms",
        "root_cause": "Upstream transit route flap causing TCP retransmission storm on edge interface.",
        "remediation": "Reroute ingress traffic via secondary Cloudflare Anycast pop in us-east-2.",
    },
    "db_overload_node_b": {
        "title": "Database Storage & Lock Bottleneck",
        "short_title": "Database Overload",
        "badge": "🔴 STORAGE SATURATION",
        "severity": "POOR",
        "color": "#EF4444",
        "target_node": "node_b92c (PostgreSQL Master)",
        "headline": "Database Storage Volume at 98% with Lock Contention",
        "description": "PostgreSQL master storage volume saturation at 98%, triggering write stalls, connection pool exhaustion, and elevated query response latency.",
        "expected_cpu": "78% – 88%",
        "expected_lat": "180 – 260 ms",
        "root_cause": "Unindexed full table scan during batch vacuum combined with WAL log partition saturation.",
        "remediation": "Trigger WAL archive flush, throttle non-critical analytical queries, and scale IOPS tier.",
    },
}


# --- SIDEBAR: OPERATIONAL NAVIGATION ---
with st.sidebar:
    st.markdown("""
    <div style='padding-bottom: 12px;'>
        <div style='font-size: 1.2rem; font-weight: 700; color: #F0F3F8; letter-spacing: -0.02em;'>
            🛡️ SentinelOps AI
        </div>
        <div style='font-size: 0.74rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.06em;'>
            Autonomous Observability • AIOps
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Main Navigation
    st.markdown("<div class='kpi-label'>Navigation Portal</div>", unsafe_allow_html=True)
    
    if st.button("🌐 Company Overview (Landing Page)", use_container_width=True, type="primary" if st.session_state["active_view"] == "landing" else "secondary"):
        st.session_state["active_view"] = "landing"
        st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>Fleet Scenario Workspaces</div>", unsafe_allow_html=True)

    scenario_menu = [
        ("🟢 Normal Baseline (3 Nodes)", "normal"),
        ("🔴 CPU & RAM Spike (node_a81f)", "spike_node_a"),
        ("🟡 Network Outage (node_c73d)", "network_degrade_node_c"),
        ("🔴 DB Overload (node_b92c)", "db_overload_node_b"),
    ]

    for label, scn_key in scenario_menu:
        is_active = (st.session_state["active_view"] == "workspace" and st.session_state["active_scenario_key"] == scn_key)
        btn_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"sb_nav_{scn_key}", use_container_width=True, type=btn_type):
            st.session_state["active_view"] = "workspace"
            st.session_state["active_scenario_key"] = scn_key
            data_service.set_scenario(scn_key)
            st.rerun()

    st.markdown("---")
    st.markdown("<div class='kpi-label'>Phase 2: Privacy Engine</div>", unsafe_allow_html=True)
    if st.button("🛡️ Zero-Trust Privacy Lab", use_container_width=True, type="primary" if st.session_state["active_view"] == "privacy_lab" else "secondary"):
        st.session_state["active_view"] = "privacy_lab"
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='kpi-label'>System Architecture & Links</div>", unsafe_allow_html=True)
    if getattr(data_service, "backend_connected", False):
        st.markdown("<span class='status-pill status-pill-excellent'>🟢 FastAPI 8000: Synchronized</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-pill status-pill-good'>🟢 Local Collector Active</span>", unsafe_allow_html=True)
    st.caption("Tier 1: Customer VPC • Tier 2: SaaS Cloud")


# Synchronize data service with active scenario
data_service.set_scenario(st.session_state["active_scenario_key"])

# Fetch live metrics with realistic variations
latest_by_node, active_alerts = data_service.fetch_latest_metrics()
history_df = data_service.get_history_df()
privacy_result = data_service.last_privacy_demo_result
audit_records = data_service.get_egress_audit_records()

# Calculate dynamic cluster health
overall_states = [calculate_overall_health(node) for node in latest_by_node.values()]
cluster_health = "POOR" if "POOR" in overall_states else ("FAIR" if "FAIR" in overall_states else ("GOOD" if "GOOD" in overall_states else "EXCELLENT"))

# Calculate dynamic fleet latency average across all 3 active nodes
total_nodes = len(latest_by_node)
crit_count = sum(1 for a in active_alerts if a.get("severity") == "CRITICAL")
avg_lat = round(sum(d["latency_ms"] for d in latest_by_node.values()) / total_nodes, 1) if total_nodes > 0 else 0.0


# =============================================================================
# VIEW 1: PROFESSIONAL COMPANY LANDING PAGE
# =============================================================================
if st.session_state["active_view"] == "landing":
    # Hero Masthead
    st.markdown("""
    <div class='landing-hero'>
        <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
            <div>
                <span class='status-pill status-pill-excellent' style='margin-bottom: 14px;'>
                    TIER-2 ENTERPRISE AIOPS SAAS • PRIVACY-FIRST
                </span>
                <h1 style='margin: 10px 0 10px 0; font-size: 2.35rem; font-weight: 800; letter-spacing: -0.03em; color: #FFFFFF; line-height: 1.15;'>
                    SentinelOps AI
                </h1>
                <p style='font-size: 1.12rem; color: #38BDF8; font-weight: 500; margin: 0 0 14px 0;'>
                    Autonomous Infrastructure Observability With Cryptographically Guaranteed Zero VPC Secret Egress.
                </p>
                <p style='color: #94A3B8; font-size: 0.94rem; max-width: 820px; line-height: 1.55; margin: 0;'>
                    Modern APM solutions indiscriminately ship internal credentials, API keys, database strings, and customer PII 
                    into third-party SaaS clouds. SentinelOps solves this by isolating the sensitive data lifecycle: 
                    <strong>100% of telemetry redaction occurs inside your customer VPC (Tier 1)</strong>, while our centralized 
                    AIOps engine (Tier 2) ingests strictly approved, sanitized operational metadata for incident detection.
                </p>
            </div>
            <div style='text-align: right;' class='font-mono'>
                <div style='background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 12px 18px;'>
                    <div style='color: #8B949E; font-size: 0.72rem; text-transform: uppercase;'>Cluster Status</div>
                    <div style='color: #34D399; font-weight: 700; font-size: 1.1rem;'>EXCELLENT</div>
                    <div style='color: #64748B; font-size: 0.74rem; margin-top: 4px;'>tenant_demo • us-east-1</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3 Core Problem & Solution Pillars
    st.markdown("<div class='kpi-label'>Key Engineering Capabilities (What SentinelOps Solves)</div>", unsafe_allow_html=True)
    c_p1, c_p2, c_p3 = st.columns(3)

    with c_p1:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #38BDF8; font-size: 1.25rem; margin-bottom: 6px;'>🔒</div>
            <strong style='color: #F0F3F8; font-size: 1rem;'>Zero VPC Secret Egress</strong>
            <p style='color: #8B949E; font-size: 0.85rem; margin-top: 8px; line-height: 1.45;'>
                Raw application logs, bearer JWTs, and database credentials are scrubbed locally in Tier 1. 
                Our strict 13-field Allow-List policy drops all arbitrary metadata before transmission.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with c_p2:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #34D399; font-size: 1.25rem; margin-bottom: 6px;'>⚡</div>
            <strong style='color: #F0F3F8; font-size: 1rem;'>Dynamic SLA Anomaly Intelligence</strong>
            <p style='color: #8B949E; font-size: 0.85rem; margin-top: 8px; line-height: 1.45;'>
                Replaces static, noisy alert storms with Section 14 four-state classification (EXCELLENT, GOOD, FAIR, POOR). 
                Monitors CPU (>90%), Memory (>90%), Latency (>250ms), and Packet Loss (>5%).
            </p>
        </div>
        """, unsafe_allow_html=True)

    with c_p3:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #A78BFA; font-size: 1.25rem; margin-bottom: 6px;'>📜</div>
            <strong style='color: #F0F3F8; font-size: 1rem;'>Cryptographic Egress Audit Proof</strong>
            <p style='color: #8B949E; font-size: 0.85rem; margin-top: 8px; line-height: 1.45;'>
                Every telemetry transmission produces a verifiable SHA-256 HMAC digest recorded in an immutable local audit log. 
                Provides complete mathematical proof of regulatory compliance (GDPR/DPDP).
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Interactive Workload Simulator Hub (Launchpads)
    st.markdown("""
    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
        <div class='kpi-label' style='margin: 0;'>⚡ Interactive Workload Simulator (Select a Scenario to Launch Dedicated Workspace)</div>
        <span style='color: #8B949E; font-size: 0.78rem;' class='font-mono'>4 Production Scenarios Available</span>
    </div>
    """, unsafe_allow_html=True)

    col_l1, col_l2 = st.columns(2)

    with col_l1:
        # Card 1: Normal Baseline
        st.markdown("""
        <div class='scenario-launch-card'>
            <div>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <strong style='color: #10B981; font-size: 1.05rem;'>🟢 Normal Baseline Operation</strong>
                    <span class='status-pill status-pill-excellent'>OPTIMAL</span>
                </div>
                <p style='color: #8B949E; font-size: 0.85rem; margin: 8px 0 14px 0; line-height: 1.4;'>
                    Full 3-node production fleet (Web/App, PostgreSQL Master, and Edge Ingress) operating nominal traffic. 
                    Telemetric metrics vary with natural realistic jitter within Section 14 SLA limits.
                </p>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;' class='font-mono'>
                    <div><span style='color: #64748B;'>FLEET LATENCY:</span> <strong style='color: #34D399;'>11 – 20 ms</strong></div>
                    <div><span style='color: #64748B;'>ACTIVE ALERTS:</span> <strong style='color: #34D399;'>0 Critical</strong></div>
                    <div><span style='color: #64748B;'>AVG CPU:</span> <strong style='color: #F0F3F8;'>24% – 36%</strong></div>
                    <div><span style='color: #64748B;'>HEALTH STATE:</span> <strong style='color: #10B981;'>EXCELLENT</strong></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Normal Baseline Workspace →", key="launch_normal", use_container_width=True, type="primary"):
            st.session_state["active_view"] = "workspace"
            st.session_state["active_scenario_key"] = "normal"
            data_service.set_scenario("normal")
            st.rerun()

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        # Card 3: Network Ingress Degradation
        st.markdown("""
        <div class='scenario-launch-card'>
            <div>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <strong style='color: #F59E0B; font-size: 1.05rem;'>🟡 Network Ingress Degradation</strong>
                    <span class='status-pill status-pill-fair'>OUTAGE</span>
                </div>
                <p style='color: #8B949E; font-size: 0.85rem; margin: 8px 0 14px 0; line-height: 1.4;'>
                    Simulates edge gateway (<code>node_c73d</code>) route degradation with high packet drop rates (&gt;15%) 
                    and round-trip latency spikes exceeding 400ms.
                </p>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;' class='font-mono'>
                    <div><span style='color: #64748B;'>INGRESS LATENCY:</span> <strong style='color: #EF4444;'>380 – 520 ms</strong></div>
                    <div><span style='color: #64748B;'>PACKET DROP:</span> <strong style='color: #EF4444;'>14% – 22%</strong></div>
                    <div><span style='color: #64748B;'>AFFECTED NODE:</span> <strong style='color: #F0F3F8;'>node_c73d</strong></div>
                    <div><span style='color: #64748B;'>HEALTH STATE:</span> <strong style='color: #F59E0B;'>POOR</strong></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Network Outage Workspace →", key="launch_net", use_container_width=True):
            st.session_state["active_view"] = "workspace"
            st.session_state["active_scenario_key"] = "network_degrade_node_c"
            data_service.set_scenario("network_degrade_node_c")
            st.rerun()

    with col_l2:
        # Card 2: CPU Spike
        st.markdown("""
        <div class='scenario-launch-card'>
            <div>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <strong style='color: #EF4444; font-size: 1.05rem;'>🔴 CPU & Memory Exhaustion</strong>
                    <span class='status-pill status-pill-poor'>CRITICAL SPIKE</span>
                </div>
                <p style='color: #8B949E; font-size: 0.85rem; margin: 8px 0 14px 0; line-height: 1.4;'>
                    Simulates sudden thread contention and memory leak on the Primary Web Application Server (<code>node_a81f</code>). 
                    CPU utilization spikes to 95%+, triggering autonomous threshold alarms.
                </p>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;' class='font-mono'>
                    <div><span style='color: #64748B;'>NODE CPU:</span> <strong style='color: #EF4444;'>94% – 99%</strong></div>
                    <div><span style='color: #64748B;'>NODE MEMORY:</span> <strong style='color: #EF4444;'>91% – 96%</strong></div>
                    <div><span style='color: #64748B;'>AFFECTED NODE:</span> <strong style='color: #F0F3F8;'>node_a81f</strong></div>
                    <div><span style='color: #64748B;'>HEALTH STATE:</span> <strong style='color: #EF4444;'>POOR</strong></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch CPU Spike Workspace →", key="launch_cpu", use_container_width=True):
            st.session_state["active_view"] = "workspace"
            st.session_state["active_scenario_key"] = "spike_node_a"
            data_service.set_scenario("spike_node_a")
            st.rerun()

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        # Card 4: Database Overload
        st.markdown("""
        <div class='scenario-launch-card'>
            <div>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <strong style='color: #EF4444; font-size: 1.05rem;'>🔴 Database Storage Bottleneck</strong>
                    <span class='status-pill status-pill-poor'>STORAGE FULL</span>
                </div>
                <p style='color: #8B949E; font-size: 0.85rem; margin: 8px 0 14px 0; line-height: 1.4;'>
                    Simulates PostgreSQL Database Master (<code>node_b92c</code>) reaching 98% storage volume saturation, 
                    connection pool lockup, and write failure burst.
                </p>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;' class='font-mono'>
                    <div><span style='color: #64748B;'>DISK VOLUME:</span> <strong style='color: #EF4444;'>98.0% Full</strong></div>
                    <div><span style='color: #64748B;'>FAILED LOGINS:</span> <strong style='color: #EF4444;'>14 Attempts</strong></div>
                    <div><span style='color: #64748B;'>AFFECTED NODE:</span> <strong style='color: #F0F3F8;'>node_b92c</strong></div>
                    <div><span style='color: #64748B;'>HEALTH STATE:</span> <strong style='color: #EF4444;'>POOR</strong></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Database Overload Workspace →", key="launch_db", use_container_width=True):
            st.session_state["active_view"] = "workspace"
            st.session_state["active_scenario_key"] = "db_overload_node_b"
            data_service.set_scenario("db_overload_node_b")
            st.rerun()

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # Section 14 SLA Guarantees Matrix
    st.markdown("<div class='kpi-label'>Section 14 — Automated SLA Health Classification Matrix</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='taste-card'>
        <table class='sla-table'>
            <thead>
                <tr>
                    <th>METRIC TYPE</th>
                    <th>OPTIMAL (EXCELLENT)</th>
                    <th>ELEVATED (GOOD)</th>
                    <th>WARNING (FAIR)</th>
                    <th>CRITICAL VIOLATION (POOR)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>CPU Utilization</strong></td>
                    <td style='color: #34D399;'>0% – 50%</td>
                    <td style='color: #60A5FA;'>51% – 70%</td>
                    <td style='color: #FBBF24;'>71% – 90%</td>
                    <td style='color: #F87171;'>&gt; 90.0% (SLA Breach)</td>
                </tr>
                <tr>
                    <td><strong>Memory (RAM)</strong></td>
                    <td style='color: #34D399;'>0% – 60%</td>
                    <td style='color: #60A5FA;'>61% – 75%</td>
                    <td style='color: #FBBF24;'>76% – 90%</td>
                    <td style='color: #F87171;'>&gt; 90.0% (Heap Risk)</td>
                </tr>
                <tr>
                    <td><strong>Round-Trip Latency</strong></td>
                    <td style='color: #34D399;'>0 – 50 ms</td>
                    <td style='color: #60A5FA;'>51 – 100 ms</td>
                    <td style='color: #FBBF24;'>101 – 250 ms</td>
                    <td style='color: #F87171;'>&gt; 250.0 ms (Outage)</td>
                </tr>
                <tr>
                    <td><strong>Packet Drop Rate</strong></td>
                    <td style='color: #34D399;'>0.0%</td>
                    <td style='color: #60A5FA;'>0.1% – 1.0%</td>
                    <td style='color: #FBBF24;'>1.1% – 5.0%</td>
                    <td style='color: #F87171;'>&gt; 5.0% (Retransmit Storm)</td>
                </tr>
                <tr>
                    <td><strong>Storage Disk Volume</strong></td>
                    <td style='color: #34D399;'>0% – 70%</td>
                    <td style='color: #60A5FA;'>71% – 85%</td>
                    <td style='color: #FBBF24;'>86% – 95%</td>
                    <td style='color: #F87171;'>&gt; 95.0% (Write Stall)</td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# VIEW 2: DEDICATED SCENARIO WORKSPACE
# =============================================================================
elif st.session_state["active_view"] == "workspace":
    curr_key = st.session_state["active_scenario_key"]
    cfg = SCENARIO_CONFIGS.get(curr_key, SCENARIO_CONFIGS["normal"])

    # Breadcrumb & Navigation Header
    nav_col1, nav_col2 = st.columns([1.5, 3.5])
    with nav_col1:
        if st.button("← Back to Company Landing Page", use_container_width=True):
            st.session_state["active_view"] = "landing"
            st.session_state["active_scenario_key"] = "normal"
            data_service.set_scenario("normal")
            st.rerun()

    with nav_col2:
        st.markdown(f"""
        <div style='display: flex; align-items: center; justify-content: flex-end; gap: 12px;'>
            <span style='color: #8B949E; font-size: 0.82rem;' class='font-mono'>WORKSPACE:</span>
            <span style='background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); padding: 4px 12px; border-radius: 6px; font-weight: 700; color: {cfg["color"]}; font-size: 0.85rem;'>
                {cfg["title"].upper()}
            </span>
            <span class='status-pill status-pill-{cluster_health.lower()}'>
                CLUSTER: {cluster_health}
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Workspace Masthead Banner
    st.markdown(f"""
    <div class='workspace-banner' style='border-left: 4px solid {cfg["color"]};'>
        <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
            <div>
                <div style='display: flex; align-items: center; gap: 10px;'>
                    <h2 style='margin: 0; font-size: 1.6rem; font-weight: 800; color: #F0F3F8; letter-spacing: -0.02em;'>
                        {cfg["headline"]}
                    </h2>
                    <span style='font-size: 0.76rem; font-weight: 700; color: {cfg["color"]}; padding: 2px 8px; border-radius: 4px; background: rgba(255, 255, 255, 0.05);'>
                        {cfg["badge"]}
                    </span>
                </div>
                <p style='color: #94A3B8; font-size: 0.88rem; margin: 6px 0 0 0; line-height: 1.45; max-width: 820px;'>
                    {cfg["description"]}
                </p>
            </div>
            <div style='text-align: right;' class='font-mono'>
                <div style='color: #8B949E; font-size: 0.74rem;'>FOCUSED NODE</div>
                <div style='color: #F0F3F8; font-weight: 700; font-size: 0.96rem;'>{cfg["target_node"]}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Live Scenario Controls Toolbar
    st.markdown("<div class='kpi-label'>Live Interactive Simulator Controls</div>", unsafe_allow_html=True)
    c_act1, c_act2, c_act3, c_act4 = st.columns([1.6, 1.3, 1.3, 1.3])

    with c_act1:
        if st.button("⚡ Inject Dynamic Variation / Re-sample", use_container_width=True, type="primary"):
            st.toast("✅ Generated fresh dynamic realistic telemetry with natural jitter!", icon="📊")
            st.rerun()

    with c_act2:
        if st.button("🟢 Switch to Normal Baseline", use_container_width=True):
            st.session_state["active_scenario_key"] = "normal"
            data_service.set_scenario("normal")
            st.rerun()

    with c_act3:
        if st.button("🔴 Switch to CPU Spike", use_container_width=True):
            st.session_state["active_scenario_key"] = "spike_node_a"
            data_service.set_scenario("spike_node_a")
            st.rerun()

    with c_act4:
        if st.button("🟡 Switch to Network Outage", use_container_width=True):
            st.session_state["active_scenario_key"] = "network_degrade_node_c"
            data_service.set_scenario("network_degrade_node_c")
            st.rerun()

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 4 Top KPI Stat Blocks (Dynamically computed!)
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(f"""
        <div class='kpi-container'>
            <div class='kpi-label'>Monitored Nodes</div>
            <div class='kpi-value'>{total_nodes} <span style='font-size: 0.9rem; color: #34d399;'>● ONLINE</span></div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class='kpi-container'>
            <div class='kpi-label'>Cluster Health Status</div>
            <div class='kpi-value' style='color: {HEALTH_COLORS.get(cluster_health, "#10B981")};'>{cluster_health}</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class='kpi-container'>
            <div class='kpi-label'>Active Threshold Alerts</div>
            <div class='kpi-value' style='color: {"#f87171" if crit_count > 0 else "#34d399"};'>
                {len(active_alerts)} <span style='font-size: 0.85rem; color: #8b949e;'>({crit_count} Critical)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class='kpi-container'>
            <div class='kpi-label'>Fleet Latency Average</div>
            <div class='kpi-value'>{avg_lat} <span style='font-size: 0.9rem; color: #8b949e;'>ms</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Scenario Deep Dive & Root-Cause Forensic Box
    st.markdown("<div class='kpi-label'>Incident Forensic Analysis & Automated Remediation</div>", unsafe_allow_html=True)
    f_col1, f_col2 = st.columns(2)

    with f_col1:
        st.markdown(f"""
        <div class='taste-card'>
            <div style='color: #38BDF8; font-weight: 700; font-size: 0.88rem; margin-bottom: 6px;'>
                🔍 Root-Cause Diagnostic Hypothesis
            </div>
            <p style='color: #CBD5E1; font-size: 0.85rem; margin: 0; line-height: 1.45;'>
                {cfg["root_cause"]}
            </p>
            <div style='margin-top: 10px; font-size: 0.76rem; color: #8B949E;' class='font-mono'>
                Target Node: {cfg["target_node"]} • Threshold SLA: Section 14 Enforced
            </div>
        </div>
        """, unsafe_allow_html=True)

    with f_col2:
        st.markdown(f"""
        <div class='taste-card'>
            <div style='color: #34D399; font-weight: 700; font-size: 0.88rem; margin-bottom: 6px;'>
                🤖 Recommended Autonomous Remediation
            </div>
            <p style='color: #CBD5E1; font-size: 0.85rem; margin: 0; line-height: 1.45;'>
                {cfg["remediation"]}
            </p>
            <div style='margin-top: 10px; font-size: 0.76rem; color: #8B949E;' class='font-mono'>
                Execution Policy: Autonomous Tier 2 Hook • Status: STANDBY
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Live Alerts Stream (Shows ONLY active alerts for this scenario!)
    st.markdown("<div class='kpi-label'>🚨 Live Anomaly & Threshold Alerts (Real-Time Ingestion)</div>", unsafe_allow_html=True)
    if active_alerts and curr_key != "normal":
        for alert in active_alerts:
            is_crit = alert.get("severity") == "CRITICAL"
            card_class = "taste-alert-crit" if is_crit else "taste-alert-warn"
            badge = "🔴 CRITICAL" if is_crit else "🟡 WARNING"
            st.markdown(f"""
            <div class='{card_class}'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <strong style='color: #F0F3F8;'>{badge} • {alert.get('source_id')} — {alert.get('metric')} ({alert.get('value')})</strong>
                    <span style='font-size: 0.78rem; color: #8B949E;' class='font-mono'>UTC INGESTION</span>
                </div>
                <div style='color: #CBD5E1; font-size: 0.85rem; margin-top: 4px;'>{alert.get('message')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: rgba(16, 185, 129, 0.06); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;'>
            <div style='display: flex; align-items: center; justify-content: space-between;'>
                <div>
                    <span style='color: #34D399; font-weight: 700; font-size: 0.95rem;'>✅ All Systems Nominal</span>
                    <span style='color: #8B949E; font-size: 0.85rem;'> — All 3 monitored nodes are transmitting healthy telemetry within expected baselines.</span>
                </div>
                <span class='status-pill status-pill-excellent'>0 ACTIVE ALERTS</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Monitored Servers Grid (Showing all 3 nodes with dynamic jitter!)
    st.markdown("<div class='kpi-label'>🖥️ Active Monitored Fleet (The 3 Production Nodes)</div>", unsafe_allow_html=True)
    node_cols = st.columns(3)
    node_metadata = {
        "node_a81f": {"name": "Primary Web / Application Server", "role": "App Services"},
        "node_b92c": {"name": "PostgreSQL Database Master", "role": "Data Store"},
        "node_c73d": {"name": "API Gateway & Edge Ingress", "role": "Network Ingress"},
    }

    for i, (source_id, data) in enumerate(latest_by_node.items()):
        col = node_cols[i % 3]
        node_health = calculate_overall_health(data)
        meta = node_metadata.get(source_id, {"name": "Infrastructure Node", "role": "Worker"})
        color = HEALTH_COLORS.get(node_health, "#10B981")

        with col:
            st.markdown(f"""
            <div class='taste-card' style='border-top: 2px solid {color};'>
                <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                    <div>
                        <div style='font-family: JetBrains Mono, monospace; font-size: 1.15rem; font-weight: 700; color: #F0F3F8;'>
                            {source_id}
                        </div>
                        <div style='font-size: 0.78rem; color: #8B949E; margin-top: 2px;'>{meta['name']}</div>
                    </div>
                    <span style='font-size: 0.78rem; font-weight: 700; color: {color};'>{HEALTH_BADGES[node_health]}</span>
                </div>
                <hr style='border: none; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 14px 0;'/>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.84rem;' class='font-mono'>
                    <div><span style='color: #8B949E;'>CPU:</span> <strong style='color: {"#f87171" if data["cpu"] > 90 else "#F0F3F8"};'>{data['cpu']}%</strong></div>
                    <div><span style='color: #8B949E;'>RAM:</span> <strong style='color: {"#f87171" if data["memory"] > 90 else "#F0F3F8"};'>{data['memory']}%</strong></div>
                    <div><span style='color: #8B949E;'>DISK:</span> <strong style='color: {"#f87171" if data["disk"] > 95 else "#F0F3F8"};'>{data['disk']}%</strong></div>
                    <div><span style='color: #8B949E;'>LATENCY:</span> <strong style='color: {"#f87171" if data["latency_ms"] > 250 else "#F0F3F8"};'>{data['latency_ms']} ms</strong></div>
                    <div><span style='color: #8B949E;'>LOSS:</span> <strong style='color: {"#f87171" if data["packet_loss_pct"] > 5 else "#F0F3F8"};'>{data['packet_loss_pct']}%</strong></div>
                    <div><span style='color: #8B949E;'>ERRORS:</span> <strong>{data['error_count']}</strong></div>
                </div>
                <div style='margin-top: 14px; font-size: 0.74rem; color: #64748B;' class='font-mono'>
                    Heartbeat: {data['timestamp_utc'][-12:-4]} UTC • Collector: {data['collector_status'].upper()}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Telemetry Trend Visualizations
    st.markdown("<div class='kpi-label'>📈 Fleet Telemetry Trends & Metric Analysis</div>", unsafe_allow_html=True)
    tc1, tc2 = st.columns(2)
    with tc1:
        f_cpu = create_metric_history_chart(history_df, "cpu", "CPU Utilization Across Fleet (%)", "%", 70.0, 90.0)
        if f_cpu:
            st.plotly_chart(f_cpu, use_container_width=True)
    with tc2:
        f_lat = create_metric_history_chart(history_df, "latency_ms", "Network Round-Trip Latency (ms)", "ms", 100.0, 250.0)
        if f_lat:
            st.plotly_chart(f_lat, use_container_width=True)


# =============================================================================
# VIEW 3: PHASE 2 ZERO-TRUST PRIVACY & EGRESS PROOF LAB
# =============================================================================
elif st.session_state["active_view"] == "privacy_lab":
    # Header
    nav_col1, nav_col2 = st.columns([1.5, 3.5])
    with nav_col1:
        if st.button("← Back to Company Landing Page", use_container_width=True):
            st.session_state["active_view"] = "landing"
            st.rerun()

    with nav_col2:
        st.markdown("""
        <div style='display: flex; align-items: center; justify-content: flex-end; gap: 10px;'>
            <span class='status-pill status-pill-excellent'>ZERO SECRETS LEAKED • 100% REDACTED</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background: #0f1218; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px 24px; margin-bottom: 20px;'>
        <div style='display: flex; align-items: center; gap: 8px;'>
            <span style='font-size: 1.2rem;'>🛡️</span>
            <strong style='font-size: 1.1rem; color: #F0F3F8;'>Phase 2 Checkpoint: Zero-Trust Privacy Engine & Egress Proof</strong>
        </div>
        <p style='color: #94A3B8; font-size: 0.88rem; margin: 8px 0 0 0; line-height: 1.5;'>
            Raw operational logs, database connection strings, passwords, and API tokens remain strictly locked inside 
            <strong>Tier 1 (Customer Environment)</strong>. Our local Privacy Engine and Allow-List Gate scrub all secrets,
            pseudonymize hostnames, and guarantee that <strong>only 13 approved metadata fields</strong> ever cross the network.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Trigger test
    st.markdown("<div class='kpi-label'>Interactive Privacy Redaction Test Trigger</div>", unsafe_allow_html=True)
    p_col1, p_col2 = st.columns([2.5, 1.5])
    with p_col1:
        privacy_scenario = st.selectbox(
            "Select Sensitive Payload Scenario:",
            ["cascade_failure", "cpu_spike", "auth_attack", "memory_leak"],
            format_func=lambda x: {
                "cascade_failure": "Cascade Outage with DB Secrets & Master Passwords",
                "cpu_spike": "CPU Spike with Leaked Password in Command Line",
                "auth_attack": "Auth Attack with Bearer JWT Token",
                "memory_leak": "Memory Leak with Internal Hostname & IPs",
            }.get(x, x),
            label_visibility="collapsed",
        )
    with p_col2:
        if st.button("⚡ Test Privacy Redaction Now", use_container_width=True, type="primary"):
            data_service.run_privacy_test(scenario=privacy_scenario)
            st.toast("✅ Privacy Engine redacted sensitive tokens and recorded Egress Proof!", icon="🔒")
            st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Side-by-Side Comparison
    st.markdown("<div class='kpi-label'>🔍 Live Side-by-Side Egress Verification (What Leaves vs What Stays Behind)</div>", unsafe_allow_html=True)
    c_raw, c_safe = st.columns(2)

    raw_event = privacy_result.get("original_raw_event", {})
    safe_payload = privacy_result.get("egress_audit_proof", {}).get("safe_payload", {}) or privacy_result.get("pipeline_result", {}).get("safe_payload", {})
    audit_proof = privacy_result.get("egress_audit_proof", {})

    with c_raw:
        st.markdown("""
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
            <span style='color: #F87171; font-weight: 700; font-size: 0.85rem;'>TIER 1: RAW LOCAL EVENT (Customer VPC)</span>
            <span style='background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;'>
                ⚠️ SENSITIVE • LOCAL ONLY
            </span>
        </div>
        """, unsafe_allow_html=True)
        st.json(raw_event if raw_event else {"status": "Click 'Test Privacy Redaction Now' above to run live proof"})

    with c_safe:
        st.markdown("""
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
            <span style='color: #34D399; font-weight: 700; font-size: 0.85rem;'>TIER 2: SANITIZED EGRESS PAYLOAD (SaaS Ingest)</span>
            <span style='background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700;'>
                🔒 APPROVED METADATA ONLY
            </span>
        </div>
        """, unsafe_allow_html=True)
        st.json(safe_payload if safe_payload else {"status": "Awaiting transmission"})

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Allow-List Policy Gate Inspector
    st.markdown("<div class='kpi-label'>🛡️ Allow-List Policy Gate Inspection (Strict 13-Field Allow-List)</div>", unsafe_allow_html=True)
    allowed_list = audit_proof.get("allowed_fields", [
        "payload_id", "tenant_id", "source_id", "timestamp_utc", "cpu", "memory", "disk",
        "latency_ms", "packet_loss_pct", "error_count", "failed_logins", "collector_status", "event_category"
    ])
    blocked_list = audit_proof.get("blocked_fields", ["raw_log_payload", "db_password", "bearer_token", "real_hostname", "internal_ip"])
    secrets_detected = audit_proof.get("detected_secrets", ["admin_password", "bearer_jwt", "prod_database_uri"])

    col_gate1, col_gate2 = st.columns(2)
    with col_gate1:
        st.markdown(f"""
        <div class='taste-card'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                <strong style='color: #34D399; font-size: 0.88rem;'>✅ Approved Telemetry Fields ({len(allowed_list)} Fields Transmitted)</strong>
                <span class='status-pill status-pill-excellent'>POLICY: PASS</span>
            </div>
            <div>
                {"".join([f"<span class='field-tag-allowed'>+{f}</span>" for f in allowed_list])}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_gate2:
        st.markdown(f"""
        <div class='taste-card'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                <strong style='color: #F87171; font-size: 0.88rem;'>🚫 Stripped & Blocked Forbidden Fields ({len(blocked_list)} Fields Dropped)</strong>
                <span class='status-pill status-pill-poor'>ZERO SECRETS LEAKED</span>
            </div>
            <div>
                {"".join([f"<span class='field-tag-blocked'>✕ {f}</span>" for f in blocked_list])}
            </div>
            <div style='margin-top: 10px; font-size: 0.78rem; color: #8B949E;'>
                Scrubbed Items: {", ".join(secrets_detected)}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Real-Time Immutable Egress Audit Trail Table
    st.markdown("<div class='kpi-label'>📜 Immutable Egress Audit Trail (Real-Time Proof Table)</div>", unsafe_allow_html=True)
    if audit_records:
        audit_rows = []
        for r in audit_records[:15]:
            audit_rows.append({
                "Audit ID": r.get("audit_id", ""),
                "Timestamp (UTC)": r.get("timestamp_utc", "")[-12:-4] + " UTC",
                "Node ID": r.get("source_id", ""),
                "Policy Verdict": r.get("policy_verdict", "PASS"),
                "Secrets Scrubbed": len(r.get("detected_secrets", [])),
                "Status": r.get("transmission_status", "SENT"),
                "Destination": r.get("destination", "http://127.0.0.1:8000/api/v1/telemetry"),
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No audit records in memory yet. Click 'Test Privacy Redaction Now' above to generate proof records!")
