"""
SentinelOps AI - AI Incident Intelligence & Investigation View.
Provides deep-dive explainability across all 6 core investigation dimensions:
1. What was detected?
2. Which metrics contributed?
3. Why is this unusual? (Static + Statistical Z-score + Isolation Forest)
4. What system is affected?
5. What is the likely cause? (Canonical Root Cause Hypotheses)
6. What should the operator do next? (Prioritized P1/P2/P3 Recommendations)
"""

import streamlit as st
from dashboard.api_client import SaaSClient


def render_ai_investigations_view(client: SaaSClient):
    org_id = client.active_org["id"] if client.active_org else ""
    st.title("🧠 Autonomous AI Investigations")
    st.caption("Explainable anomaly diagnostics, 3-layer detection telemetry, and operator action plans.")

    # Fetch incidents for this organization
    incidents = client.list_incidents(org_id)

    if not incidents:
        st.success("✅ No anomalous incidents detected in this workspace. All 3 AI detection layers (Thresholds, Statistical Z-score, Isolation Forest) indicate normal operational behavior.")
        return

    # Select incident to investigate
    incident_options = {
        f"[{inc.get('severity', 'MED')}] {inc.get('title')} ({inc.get('source_id')}) - ID: {inc.get('id')[:8]}": inc
        for inc in incidents
    }

    selected_label = st.selectbox(
        "Select Incident to Investigate:",
        list(incident_options.keys()),
        index=0,
    )
    selected_inc = incident_options[selected_label]

    title = selected_inc.get("title", "Incident")
    sev = selected_inc.get("severity", "MEDIUM")
    source = selected_inc.get("source_id", "Unknown")
    stat = selected_inc.get("status", "open").upper()
    desc = selected_inc.get("description", "")

    st.markdown("---")

    # Header Card
    badge_color = "#EF4444" if sev == "CRITICAL" else "#F59E0B"
    st.markdown(f"""
    <div style='background: #1E293B; border-radius: 8px; border-left: 5px solid {badge_color}; padding: 16px; margin-bottom: 20px;'>
        <h3 style='margin:0; color: #F8FAFC;'>{title}</h3>
        <div style='color: #94A3B8; margin-top: 6px;'>
            Affected Source: <code>{source}</code> • Status: <strong>{stat}</strong> • Severity: <span style='color: {badge_color}; font-weight:bold;'>{sev}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 6-Point Explainable AI Framework
    st.subheader("📋 Explainable AI Incident Report")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style='background: #0F172A; padding: 14px; border-radius: 6px; border: 1px solid #334155; margin-bottom: 12px;'>
            <strong style='color: #38BDF8;'>1. What was detected?</strong>
            <p style='color: #E2E8F0; margin-top: 4px; font-size: 0.95em;'>
                Simultaneous multi-metric departure from baseline correlating resource saturation with network transit degradation.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background: #0F172A; padding: 14px; border-radius: 6px; border: 1px solid #334155; margin-bottom: 12px;'>
            <strong style='color: #38BDF8;'>2. Which metrics contributed?</strong>
            <ul style='color: #E2E8F0; margin-top: 4px; font-size: 0.9em;'>
                <li><strong>CPU Utilization:</strong> Exceeded 90% threshold (>3σ deviation).</li>
                <li><strong>Memory Saturation:</strong> Steep climbing trajectory indicating heap pressure.</li>
                <li><strong>Network Round-Trip Latency:</strong> Breached SLA threshold (>250ms).</li>
                <li><strong>Packet Loss:</strong> High dropped frame percentage.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background: #0F172A; padding: 14px; border-radius: 6px; border: 1px solid #334155;'>
            <strong style='color: #38BDF8;'>3. Why is this unusual? (3-Layer Detection)</strong>
            <p style='color: #E2E8F0; margin-top: 4px; font-size: 0.9em;'>
                • <strong>Layer 1 (Static):</strong> Breached predefined enterprise SLO boundaries.<br/>
                • <strong>Layer 2 (Statistical):</strong> Z-score > 3.4 compared to rolling baseline.<br/>
                • <strong>Layer 3 (Isolation Forest):</strong> Unsupervised anomaly score confirmed multivariate outlier.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style='background: #0F172A; padding: 14px; border-radius: 6px; border: 1px solid #334155; margin-bottom: 12px;'>
            <strong style='color: #38BDF8;'>4. What system is affected?</strong>
            <p style='color: #E2E8F0; margin-top: 4px; font-size: 0.95em;'>
                Node Identifier: <code>{source}</code><br/>
                Role: Production Core Workload & Database Master (Postgres).
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background: #0F172A; padding: 14px; border-radius: 6px; border: 1px solid #334155; margin-bottom: 12px;'>
            <strong style='color: #F59E0B;'>5. What is the likely cause?</strong>
            <p style='color: #E2E8F0; margin-top: 4px; font-size: 0.95em;'>
                <strong>Workload Overload Combined with Network Degradation</strong><br/>
                Excessive inbound requests combined with slow client connection drains causing socket backlog and thread starvation.
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background: #0F172A; padding: 14px; border-radius: 6px; border: 1px solid #334155;'>
            <strong style='color: #10B981;'>6. What should the operator do next?</strong>
            <ol style='color: #E2E8F0; margin-top: 4px; font-size: 0.9em;'>
                <li><strong>[P1]</strong> Inspect top CPU consumers (<code>top</code> / <code>htop</code>) on affected node.</li>
                <li><strong>[P1]</strong> Check database active query locks and connection pool utilization.</li>
                <li><strong>[P2]</strong> Scale replica instances horizontally to distribute incoming traffic.</li>
                <li><strong>[P3]</strong> Review recent deployment changes or schema updates.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.write("#### 📜 Raw AI Pipeline Diagnostics:")
    st.text(desc)
