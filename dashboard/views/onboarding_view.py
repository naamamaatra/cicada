"""
SentinelOps AI - Guided Onboarding Wizard.
Provides a clear Next/Back step-by-step setup:
Step 1: Workspace & Privacy Architecture
Step 2: Enroll Infrastructure Collector & Secret Token
Step 3: Transmit Telemetry & Verify Connection
Step 4: Launch SaaS Workspace
"""

import streamlit as st
from datetime import datetime, timezone
from dashboard.api_client import SaaSClient


def render_onboarding_view(client: SaaSClient):
    if "onboarding_step" not in st.session_state:
        st.session_state["onboarding_step"] = 1

    current_step = st.session_state["onboarding_step"]
    org_id = client.active_org["id"] if client.active_org else "org_default"
    org_name = client.active_org.get("name", "My Organization") if client.active_org else "My Organization"

    # Step Progress Indicator
    st.markdown(f"""
    <div style='margin-bottom: 24px; padding: 12px 20px; background: #1E293B; border-radius: 8px; border: 1px solid #334155;'>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span style='font-weight: 700; color: #38BDF8;'>🚀 GUIDED ONBOARDING: STEP {current_step} OF 4</span>
            <span style='color: #94A3B8; font-size: 0.9em;'>Workspace: <strong>{org_name}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # STEP 1: Privacy Architecture Overview
    # -------------------------------------------------------------------------
    if current_step == 1:
        st.subheader("1. Welcome to Privacy-First Observability")
        st.write(
            "SentinelOps AI is architected on a fundamental privacy principle: "
            "**Raw system logs, passwords, API tokens, and credentials NEVER leave your local infrastructure.**"
        )

        st.markdown("""
        <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin: 20px 0;'>
            <div style='background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #10B981;'>
                <strong style='color: #10B981;'>1. Local Agent Scan</strong><br/>
                <span style='color: #94A3B8; font-size: 0.9em;'>Collects metrics locally while scanning for 12+ sensitive credential patterns.</span>
            </div>
            <div style='background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #38BDF8;'>
                <strong style='color: #38BDF8;'>2. Allow-List Policy</strong><br/>
                <span style='color: #94A3B8; font-size: 0.9em;'>Enforces strict boundary. Only the 13 approved telemetry metrics are permitted for egress.</span>
            </div>
            <div style='background: rgba(15, 23, 42, 0.6); padding: 16px; border-radius: 8px; border-left: 4px solid #F59E0B;'>
                <strong style='color: #F59E0B;'>3. Autonomous AI</strong><br/>
                <span style='color: #94A3B8; font-size: 0.9em;'>Isolation Forest + Z-score anomaly correlation discovers incidents and root causes.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_b, col_n = st.columns([1, 1])
        with col_n:
            if st.button("Next: Enroll Collector Agent →", use_container_width=True, type="primary"):
                st.session_state["onboarding_step"] = 2
                st.rerun()

    # -------------------------------------------------------------------------
    # STEP 2: Enroll First Collector
    # -------------------------------------------------------------------------
    elif current_step == 2:
        st.subheader("2. Register Your First Infrastructure Collector")
        st.write("Generate a high-entropy enrollment token to connect your first node or cluster:")

        col_name = st.text_input("Collector Name", value="primary-k8s-cluster", placeholder="e.g. prod-app-server-01")

        if "enrolled_token" not in st.session_state:
            if st.button("🔑 Generate Collector Enrollment Token", type="primary"):
                with st.spinner("Generating secure token and registering collector..."):
                    res = client.register_collector(org_id, col_name)
                    if res["success"]:
                        st.session_state["enrolled_token"] = res["data"]["raw_token"]
                        st.session_state["enrolled_id"] = res["data"]["id"]
                        st.success("Collector registered successfully!")
                        st.rerun()
                    else:
                        st.error(res["error"])

        if "enrolled_token" in st.session_state:
            token_val = st.session_state["enrolled_token"]
            st.warning("⚠️ **IMPORTANT**: Save this secret token now. For security, it will never be displayed again.")
            st.code(token_val, language="bash")

            st.write("#### Collector Shell Environment Command:")
            st.code(f"""export SENTINELOPS_API="http://127.0.0.1:8000"\nexport SENTINELOPS_COLLECTOR_TOKEN="{token_val}"\npython -m collector.collector""", language="bash")

        col_b, col_n = st.columns([1, 1])
        with col_b:
            if st.button("← Back to Architecture"):
                st.session_state["onboarding_step"] = 1
                st.rerun()
        with col_n:
            if st.button("Next: Verify Connection & Transmit →", type="primary"):
                st.session_state["onboarding_step"] = 3
                st.rerun()

    # -------------------------------------------------------------------------
    # STEP 3: Verify Connection & Transmit Sample Telemetry
    # -------------------------------------------------------------------------
    elif current_step == 3:
        st.subheader("3. Verify Collector Heartbeat & Ingestion")
        st.write("Test your authenticated collector by transmitting a verified telemetry packet:")

        raw_token = st.session_state.get("enrolled_token")

        if st.button("📡 Transmit Test Telemetry Packet", type="primary", use_container_width=True):
            test_packet = {
                "payload_id": f"evt_onboard_{int(datetime.now().timestamp())}",
                "tenant_id": org_id,
                "source_id": "node_onboarding_test",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "cpu": 32.5,
                "memory": 48.0,
                "disk": 55.0,
                "latency_ms": 22.0,
                "packet_loss_pct": 0.0,
                "error_count": 0,
                "failed_logins": 0,
                "collector_status": "online",
                "event_category": "onboarding_verification",
            }
            with st.spinner("Transmitting packet to /api/v1/telemetry..."):
                resp = client.send_telemetry(test_packet, collector_token=raw_token)
                if resp["success"]:
                    st.session_state["test_packet_sent"] = True
                    st.success("✅ Connection Verified! Backend accepted telemetry and recorded heartbeat.")
                else:
                    st.error(f"Transmission error: {resp.get('error')}")

        if st.session_state.get("test_packet_sent"):
            st.markdown("""
            <div style='background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 8px; padding: 14px; margin-top: 15px;'>
                <strong style='color: #10B981;'>🎉 Ingestion Pipeline Verified!</strong><br/>
                <span style='color: #E2E8F0; font-size: 0.9em;'>Your workspace is receiving real telemetry, anomaly detection is online, and tenant isolation is active.</span>
            </div>
            """, unsafe_allow_html=True)

        col_b, col_n = st.columns([1, 1])
        with col_b:
            if st.button("← Back to Collector Token"):
                st.session_state["onboarding_step"] = 2
                st.rerun()
        with col_n:
            if st.button("Next: Complete Setup & Launch Workspace →", type="primary"):
                st.session_state["onboarding_step"] = 4
                st.rerun()

    # -------------------------------------------------------------------------
    # STEP 4: Complete Setup
    # -------------------------------------------------------------------------
    elif current_step == 4:
        st.subheader("4. Setup Complete — Welcome to SentinelOps AI")
        st.write(f"Your organization **{org_name}** is fully operational.")

        st.markdown("""
        ### What you can explore now:
        - **Overview**: Real-time tenant health, KPI metrics, and operational counters.
        - **Infrastructure**: Telemetry charts and health indicators across all enrolled nodes.
        - **Incidents**: Correlated AI incident reports with lifecycle transitions (Open → Investigating → Resolved).
        - **AI Investigations**: Explainable root-cause deduction and prioritized remediation action plans.
        - **Privacy Lab**: Interactive live sanitization showing credential redaction and allow-list enforcement.
        - **Collectors**: Agent status, heartbeats, and credential revocation.
        """)

        if st.button("🚀 Enter SentinelOps Workspace", use_container_width=True, type="primary"):
            st.session_state["current_page"] = "Overview"
            st.session_state["onboarding_completed"] = True
            st.rerun()
