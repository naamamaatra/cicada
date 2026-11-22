"""
SentinelOps AI - Live Privacy Lab View.
Interactive live demonstration calling the REAL backend Privacy Engine and Allow-List Policy.
Visualizes the 8-step privacy lifecycle and side-by-side field transformation.
"""

import streamlit as st
import json
import pandas as pd
from dashboard.api_client import SaaSClient

DEFAULT_TEST_SAMPLE = {
    "hostname": "prod-db-master-01.internal.corp",
    "cpu": 92.5,
    "memory": 88.3,
    "disk": 65.0,
    "password": "ProductionSuperSecretKey_2026!",
    "api_key": "sec_live_998877665544332211aabbcc",
    "database_url": "postgres://master_admin:root_secret_pw@10.240.10.20:5432/finance_db",
    "latency_ms": 420.0,
    "packet_loss_pct": 1.5,
    "error_count": 12,
    "failed_logins": 1,
    "collector_status": "online",
    "raw_trace": "SELECT credit_card_num, balance FROM customer_vault WHERE user_id=40129",
    "internal_kernel_stack": "panic: thread 0x00f12a kernel memory fault at 0xdeadbeef",
    "tenant_id": "tenant_demo",
    "payload_id": "evt_privacy_demo_01",
    "timestamp_utc": "2026-11-21T03:00:00Z"
}


def render_privacy_lab_view(client: SaaSClient):
    st.title("🛡️ Live Privacy Lab & Egress Proof")
    st.caption("Interactive demonstration running SentinelOps AI's real Python Privacy Engine & Allow-List Policy Gate.")

    st.markdown("""
    <div style='background: #1E293B; border-radius: 8px; border-left: 4px solid #10B981; padding: 14px; margin-bottom: 20px;'>
        <strong style='color: #10B981;'>Core Privacy Guarantee:</strong>
        <span style='color: #E2E8F0; font-size: 0.95em;'>
            Your raw server logs, passwords, tokens, connection strings, and stack traces <strong>NEVER</strong> escape your local boundary. 
            Only sanitized, allow-listed metrics can egress to the cloud backend.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 8-Step Lifecycle Diagram
    st.subheader("The 8-Step Privacy Lifecycle")
    st.markdown("""
    <div style='display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 16px;'>
        <div style='background: #0F172A; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 1</div>
            <strong style='font-size: 0.85em; color: #38BDF8;'>Raw Capture</strong>
        </div>
        <div style='background: #0F172A; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 2</div>
            <strong style='font-size: 0.85em; color: #38BDF8;'>Field Scan</strong>
        </div>
        <div style='background: #0F172A; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 3</div>
            <strong style='font-size: 0.85em; color: #EF4444;'>Redact Secrets</strong>
        </div>
        <div style='background: #0F172A; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 4</div>
            <strong style='font-size: 0.85em; color: #F59E0B;'>Pseudonymize</strong>
        </div>
        <div style='background: #0F172A; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 5</div>
            <strong style='font-size: 0.85em; color: #38BDF8;'>Allow-List Gate</strong>
        </div>
        <div style='background: #0F172A; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 6</div>
            <strong style='font-size: 0.85em; color: #10B981;'>Safe Payload</strong>
        </div>
        <div style='background: #0F172A; border: 1px solid #334155; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 7</div>
            <strong style='font-size: 0.85em; color: #38BDF8;'>Egress Audit</strong>
        </div>
        <div style='background: #0F172A; border: 1px solid #10B981; padding: 8px 12px; border-radius: 6px; min-width: 110px; text-align: center;'>
            <div style='font-size: 0.75em; color: #94A3B8;'>STEP 8</div>
            <strong style='font-size: 0.85em; color: #10B981;'>Final Verdict</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Interactive JSON Editor / Preloaded Test Case
    st.subheader("Raw Local Event Input")
    raw_text = st.text_area(
        "Edit or inspect the sample event (contains fake sensitive credentials):",
        value=json.dumps(DEFAULT_TEST_SAMPLE, indent=2),
        height=220,
    )

    if st.button("⚡ Execute Live Privacy Scan & Allow-List Enforcement", type="primary", use_container_width=True):
        try:
            parsed_sample = json.loads(raw_text)
        except Exception as e:
            st.error(f"Invalid JSON format: {e}")
            return

        with st.spinner("Executing real PrivacyEngine and AllowListPolicy on backend..."):
            res = client.inspect_privacy(parsed_sample)

        if not res["success"]:
            st.error(res["error"])
            return

        data = res["data"]
        stats = data.get("statistics", {})

        st.markdown("---")

        # Metric Statistics Cards
        st.subheader("Scan Results & Statistics")
        stat1, stat2, stat3, stat4, stat5 = st.columns(5)
        with stat1:
            st.metric("Total Fields Analyzed", stats.get("total_fields", 0))
        with stat2:
            st.metric("Secrets Redacted", stats.get("secrets_redacted", 0), delta="Secured", delta_color="normal")
        with stat3:
            st.metric("Hostnames Pseudonymized", stats.get("hostnames_pseudonymized", 0), delta="SHA-256")
        with stat4:
            st.metric("Unauthorized Fields Blocked", stats.get("fields_blocked", 0), delta="Stripped", delta_color="inverse")
        with stat5:
            st.metric("Approved for Egress", stats.get("fields_allowed", 0), delta="Permitted", delta_color="normal")

        # Side-by-Side Comparison
        st.markdown("---")
        st.subheader("Side-by-Side Transformation: Raw vs Safe Outbound Payload")

        col_raw, col_safe = st.columns(2)
        with col_raw:
            st.markdown("#### 🔴 Raw Local Data (Before Privacy Engine)")
            st.caption("Contains sensitive credentials, passwords, raw stack traces, and internal hostnames:")
            st.json(data["raw_input"])

        with col_safe:
            st.markdown("#### 🟢 Sanitized Outbound Payload (Approved for Egress)")
            st.caption("Clean Section 7 schema: Hostname is pseudonymized, all secrets & unauthorized fields dropped:")
            st.json(data["sanitized_output"])

        # Field-by-Field Decision Table
        st.markdown("---")
        st.subheader("Field-by-Field Security Decisions")

        actions = data.get("field_actions", [])
        if actions:
            action_rows = []
            for a in actions:
                status_badge = a['action']
                if "REDACTED" in status_badge:
                    badge_html = "<span style='color: #EF4444; font-weight: bold;'>REDACTED & BLOCKED</span>"
                elif "BLOCKED" in status_badge:
                    badge_html = "<span style='color: #F59E0B; font-weight: bold;'>BLOCKED</span>"
                else:
                    badge_html = "<span style='color: #10B981; font-weight: bold;'>ALLOWED</span>"

                action_rows.append({
                    "Field": f"`{a['field']}`",
                    "Security Action": badge_html,
                    "Reason": a['reason'],
                })

            st.write(pd.DataFrame(action_rows).to_html(escape=False, index=False), unsafe_allow_html=True)
