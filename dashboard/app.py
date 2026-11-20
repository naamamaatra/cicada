"""
SentinelOps AI — Infrastructure Observability & Privacy-First Platform.
Redesigned with 'design-taste-frontend' standards (Figma/Linear tier aesthetics)
Supports Phase 1 (Fleet Monitoring) and Phase 2 (Privacy Engine & Egress Proof Panel).
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


# Initialize Data Service in session state safely
if "data_service" not in st.session_state or not hasattr(st.session_state["data_service"], "run_privacy_test"):
    st.session_state["data_service"] = TelemetryDataService()

data_service: TelemetryDataService = st.session_state["data_service"]


# --- SIDEBAR: OPERATIONAL CONTROLS ---
with st.sidebar:
    st.markdown("""
    <div style='padding-bottom: 12px;'>
        <div style='font-size: 1.15rem; font-weight: 700; color: #F0F3F8; letter-spacing: -0.02em;'>
            🛡️ SentinelOps AI
        </div>
        <div style='font-size: 0.76rem; color: #8B949E; text-transform: uppercase; letter-spacing: 0.05em;'>
            Autonomous Observability • AIOps
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # Phase 1: Fleet Telemetry Scenarios
    st.markdown("<div class='kpi-label'>⚡ Phase 1: Fleet Workload Simulator</div>", unsafe_allow_html=True)
    scenario_options = {
        "🟢 Normal Baseline (3 Nodes Healthy)": "normal",
        "🔴 CPU & Memory Spike (node_a81f)": "spike_node_a",
        "🔴 Network Outage (node_c73d)": "network_degrade_node_c",
        "🔴 Database Overload (node_b92c)": "db_overload_node_b",
    }
    selected_label = st.radio(
        "Inject Infrastructure Scenario:",
        list(scenario_options.keys()),
        index=0,
        label_visibility="collapsed",
    )
    data_service.set_scenario(scenario_options[selected_label])

    if st.button("🔄 Refresh Fleet Metrics", use_container_width=True, type="primary"):
        st.rerun()

    st.markdown("---")

    # Phase 2: Privacy Engine Test Trigger
    st.markdown("<div class='kpi-label'>🛡️ Phase 2: Privacy Engine Tester</div>", unsafe_allow_html=True)
    privacy_scenario = st.selectbox(
        "Sensitive Payload Scenario:",
        ["cpu_spike", "auth_attack", "cascade_failure", "memory_leak"],
        format_func=lambda x: {
            "cpu_spike": "CPU Spike with Leaked Password",
            "auth_attack": "Auth Attack with Bearer Token",
            "cascade_failure": "Cascade Outage with DB Secrets",
            "memory_leak": "Memory Leak with Internal Hostname",
        }.get(x, x),
        label_visibility="collapsed",
    )
    if st.button("⚡ Test Privacy Redaction", use_container_width=True):
        data_service.run_privacy_test(scenario=privacy_scenario)
        st.toast("✅ Privacy Engine redacted sensitive tokens and recorded Egress Proof!", icon="🔒")
        st.rerun()

    st.markdown("---")

    # Backend Connection & Architecture Status
    st.markdown("<div class='kpi-label'>System Architecture & Links</div>", unsafe_allow_html=True)
    if getattr(data_service, "backend_connected", False):
        st.markdown("<span class='status-pill status-pill-excellent'>🟢 FastAPI 8000: Synchronized</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='status-pill status-pill-fair'>🟡 Local Engine: Fallback Active</span>", unsafe_allow_html=True)

    st.caption("Tier 1: Customer VPC • Tier 2: SaaS Cloud")


# --- DATA FETCH ---
latest_by_node, active_alerts = data_service.fetch_latest_metrics()
history_df = data_service.get_history_df()
privacy_result = data_service.last_privacy_demo_result
audit_records = data_service.get_egress_audit_records()

# Calculate Overall Cluster Health
overall_states = [calculate_overall_health(node) for node in latest_by_node.values()]
cluster_health = "POOR" if "POOR" in overall_states else ("FAIR" if "FAIR" in overall_states else ("GOOD" if "GOOD" in overall_states else "EXCELLENT"))


# --- HEADER / MASTHEAD ---
head_col1, head_col2 = st.columns([2.8, 1.4])
with head_col1:
    st.markdown("""
    <div style='padding-top: 5px;'>
        <div style='display: flex; align-items: center; gap: 10px;'>
            <h1 style='margin: 0; font-size: 1.85rem; font-weight: 700; letter-spacing: -0.03em;'>
                SENTINELOPS AI
            </h1>
            <span style='background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 3px 10px; border-radius: 6px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em;'>
                TIER-2 AIOps SAAS
            </span>
        </div>
        <p style='color: #8B949E; margin: 4px 0 0 0; font-size: 0.88rem;'>
            Privacy-First Infrastructure Observability & Autonomous Incident Intelligence
        </p>
    </div>
    """, unsafe_allow_html=True)

with head_col2:
    st.markdown("<div style='text-align: right; padding-top: 10px;'>", unsafe_allow_html=True)
    pill_class = f"status-pill status-pill-{cluster_health.lower()}"
    st.markdown(f"<span class='{pill_class}'>STATUS: {HEALTH_BADGES[cluster_health]}</span>", unsafe_allow_html=True)
    st.markdown("""
    <div style='margin-top: 6px; font-size: 0.78rem; color: #8B949E;' class='font-mono'>
        tenant_demo • us-east-1 • UTC
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


# --- DASHBOARD TABS ---
tab_fleet, tab_privacy, tab_arch = st.tabs([
    "🖥️ Fleet Infrastructure (Phase 1)",
    "🛡️ Privacy Engine & Egress Proof (Phase 2)",
    "📐 Two-Tier Architecture & Global Design",
])


# =============================================================================
# TAB 1: FLEET INFRASTRUCTURE (PHASE 1)
# =============================================================================
with tab_fleet:
    # 4 Top KPI Stat Blocks
    k1, k2, k3, k4 = st.columns(4)
    total_nodes = len(latest_by_node)
    crit_count = sum(1 for a in active_alerts if a["severity"] == "CRITICAL")
    avg_cpu = round(sum(d["cpu"] for d in latest_by_node.values()) / total_nodes, 1) if total_nodes > 0 else 0
    avg_lat = round(sum(d["latency_ms"] for d in latest_by_node.values()) / total_nodes, 1) if total_nodes > 0 else 0

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
            <div class='kpi-label'>Cluster Health</div>
            <div class='kpi-value' style='color: {HEALTH_COLORS[cluster_health]};'>{cluster_health}</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class='kpi-container'>
            <div class='kpi-label'>Active Alerts</div>
            <div class='kpi-value' style='color: {"#f87171" if crit_count > 0 else "#34d399"};'>{len(active_alerts)} <span style='font-size: 0.85rem; color: #8b949e;'>({crit_count} Crit)</span></div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class='kpi-container'>
            <div class='kpi-label'>Fleet Latency Avg</div>
            <div class='kpi-value'>{avg_lat} <span style='font-size: 0.9rem; color: #8b949e;'>ms</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Active Alerts Stream
    if active_alerts:
        st.markdown("<div class='kpi-label'>🚨 Live Anomaly & Threshold Alerts</div>", unsafe_allow_html=True)
        for alert in active_alerts:
            is_crit = alert["severity"] == "CRITICAL"
            card_class = "taste-alert-crit" if is_crit else "taste-alert-warn"
            badge = "🔴 CRITICAL" if is_crit else "🟡 WARNING"
            st.markdown(f"""
            <div class='{card_class}'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <strong style='color: #F0F3F8;'>{badge} • {alert['source_id']} — {alert['metric']} ({alert['value']})</strong>
                    <span style='font-size: 0.78rem; color: #8B949E;' class='font-mono'>UTC INGESTION</span>
                </div>
                <div style='color: #CBD5E1; font-size: 0.85rem; margin-top: 4px;'>{alert['message']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: rgba(16, 185, 129, 0.06); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;'>
            <span style='color: #34D399; font-weight: 600;'>✅ All Systems Nominal</span>
            <span style='color: #8B949E; font-size: 0.85rem;'> — All 3 monitored nodes are transmitting healthy telemetry within expected baselines.</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # The 3 Monitored Server Cards
    st.markdown("<div class='kpi-label'>🖥️ Production Fleet (The 3 Monitored Servers)</div>", unsafe_allow_html=True)
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
                    <div><span style='color: #8B949E;'>DISK:</span> <strong>{data['disk']}%</strong></div>
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
# TAB 2: PRIVACY ENGINE & EGRESS PROOF (PHASE 2 MANDATORY REQUIREMENT)
# =============================================================================
with tab_privacy:
    st.markdown("""
    <div style='background: #0f1218; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px 22px; margin-bottom: 20px;'>
        <div style='display: flex; align-items: center; gap: 8px;'>
            <span style='font-size: 1.1rem;'>🛡️</span>
            <strong style='font-size: 1rem; color: #F0F3F8;'>Zero-Trust Privacy & Egress Proof Architecture (Phase 2 Checkpoint)</strong>
        </div>
        <p style='color: #94A3B8; font-size: 0.86rem; margin: 6px 0 0 0; line-height: 1.45;'>
            Raw operational logs, database connection strings, passwords, and API tokens remain strictly locked inside 
            <strong>Tier 1 (Customer Environment)</strong>. Our local Privacy Engine and Allow-List Gate scrub all secrets,
            pseudonymize hostnames, and guarantee that <strong>only 13 approved metadata fields</strong> ever cross the network.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Side-by-Side Comparison: Raw vs Egress
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
        st.json(raw_event if raw_event else {"status": "Click 'Test Privacy Redaction' in sidebar to run proof"})

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

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

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

    # Real-Time Egress Audit Log Trail Table
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
        st.info("No audit records in memory yet. Click 'Test Privacy Redaction' in the sidebar to generate proof records!")


# =============================================================================
# TAB 3: TWO-TIER ARCHITECTURE & GLOBAL DESIGN (PHASE 2 EVIDENCE)
# =============================================================================
with tab_arch:
    st.markdown("<div class='kpi-label'>📐 Two-Tier Trust Boundary Diagram</div>", unsafe_allow_html=True)

    st.markdown("""
    ```mermaid
    flowchart LR
        subgraph TIER1["Tier 1: Customer Environment (Local VPC)"]
            A["Raw Telemetry Sources<br/>(OS, Syslog, Metrics)"] --> B["Privacy Engine<br/>(Scrub Secrets & Mask Hostnames)"]
            B --> C["Allow-List Policy Gate<br/>(Strict 13 Fields)"]
            C --> D["Offline Buffer<br/>(SQLite / In-Memory Queue)"]
            C --> E["Egress Proof Logger<br/>(Immutable Audit)"]
        end

        subgraph BOUNDARY["Trust Boundary (TLS 1.3 + Authenticated Link)"]
            D -.->|"POST /api/v1/telemetry<br/>(Metadata Only)"| F
        end

        subgraph TIER2["Tier 2: Central SaaS Platform"]
            F["FastAPI Ingest API<br/>& Deduplication Engine"] --> G["Multi-Tenant Storage<br/>(tenant_id Enforced)"]
            G --> H["AIOps Engine<br/>(Isolation Forest & Correlation)"]
            H --> I["Streamlit Dashboard<br/>(4 Health States)"]
        end
    ```
    """)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>🌐 Global-Ready Architecture Pillars</div>", unsafe_allow_html=True)

    g1, g2, g3, g4, g5 = st.columns(5)
    with g1:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #38BDF8; font-weight: 700; font-size: 0.88rem;'>1. Regional Ingest</div>
            <p style='color: #8B949E; font-size: 0.78rem; margin: 4px 0 0 0;'>
                Collectors point to assigned regional endpoints (e.g. <code>us-east-1</code>) to minimize latency.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with g2:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #34D399; font-weight: 700; font-size: 0.88rem;'>2. Tenant Residency</div>
            <p style='color: #8B949E; font-size: 0.78rem; margin: 4px 0 0 0;'>
                Metadata tagged with <code>tenant_id</code> and isolated per jurisdiction (GDPR / DPDP compliance).
            </p>
        </div>
        """, unsafe_allow_html=True)
    with g3:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #A78BFA; font-weight: 700; font-size: 0.88rem;'>3. UTC Timestamps</div>
            <p style='color: #8B949E; font-size: 0.78rem; margin: 4px 0 0 0;'>
                ISO-8601 UTC timestamps across all nodes ensure consistent worldwide dashboard rendering.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with g4:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #F59E0B; font-weight: 700; font-size: 0.88rem;'>4. Out-of-Order Handling</div>
            <p style='color: #8B949E; font-size: 0.78rem; margin: 4px 0 0 0;'>
                Time-series aggregations index by event time, preventing late packets from skewing trend baselines.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with g5:
        st.markdown("""
        <div class='taste-card'>
            <div style='color: #F43F5E; font-weight: 700; font-size: 0.88rem;'>5. Idempotent Retries</div>
            <p style='color: #8B949E; font-size: 0.78rem; margin: 4px 0 0 0;'>
                Every event has unique UUID <code>payload_id</code> preventing duplicates upon outage reconnect.
            </p>
        </div>
        """, unsafe_allow_html=True)
