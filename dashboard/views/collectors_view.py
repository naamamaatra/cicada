"""
SentinelOps AI - Collectors Fleet Management View.
Enroll collectors, inspect heartbeats, view secure token instructions, and revoke tokens.
"""

from datetime import datetime, timezone
import uuid
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from dashboard.api_client import SaaSClient


def render_collectors_view(client: SaaSClient):
    st.markdown("## 📡 Collector Fleet Management")
    st.markdown(
        "Manage distributed telemetry collectors enrolled in this workspace. "
        "Each collector authenticates using a cryptographically hashed token (`sc_live_...`) "
        "and pushes sanitized infrastructure metrics."
    )

    org = client.active_org
    if not org or not org.get("id"):
        st.warning("⚠️ No active organization selected. Please select a workspace.")
        return

    org_id = org["id"]

    # Action tabs: Fleet Overview & Enroll New Collector
    tab_fleet, tab_enroll, tab_docs = st.tabs(["📋 Collector Fleet", "➕ Enroll Collector", "📖 Setup Guide"])

    # Fetch collectors
    with st.spinner("Fetching enrolled collectors..."):
        collectors = client.list_collectors(org_id)

    with tab_fleet:
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.markdown(f"**Total Collectors Enrolled:** `{len(collectors)}`")
        online_count = sum(1 for c in collectors if c.get("status") == "online")
        c2.metric("Online Agents", online_count)
        revoked_count = sum(1 for c in collectors if c.get("status") == "revoked")
        c3.metric("Revoked Agents", revoked_count)

        if not collectors:
            st.info("ℹ️ No collectors enrolled yet in this workspace. Enroll your first collector below or use the 'Enroll Collector' tab.")
        else:
            # Render table of collectors
            for col in collectors:
                cid = col.get("id", "")
                cname = col.get("name", "Unnamed Collector")
                cstatus = col.get("status", "registered")
                last_seen = col.get("last_seen")
                created_at = col.get("created_at")

                # Format timestamps
                last_seen_str = last_seen[:19].replace("T", " ") if last_seen else "Never (Pending first push)"
                created_str = created_at[:19].replace("T", " ") if created_at else "—"

                # Status color badge
                if cstatus == "online":
                    status_badge = '<span style="background-color:rgba(16,185,129,0.2);color:#10B981;border:1px solid #10B981;padding:2px 8px;border-radius:4px;font-weight:600;font-size:12px;">● ONLINE</span>'
                elif cstatus == "revoked":
                    status_badge = '<span style="background-color:rgba(239,68,68,0.2);color:#EF4444;border:1px solid #EF4444;padding:2px 8px;border-radius:4px;font-weight:600;font-size:12px;">✕ REVOKED</span>'
                else:
                    status_badge = '<span style="background-color:rgba(56,189,248,0.2);color:#38BDF8;border:1px solid #38BDF8;padding:2px 8px;border-radius:4px;font-weight:600;font-size:12px;">○ REGISTERED</span>'

                with st.container():
                    st.markdown(
                        f"""
                        <div style="background-color:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;margin-bottom:12px;">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div>
                                    <span style="font-size:16px;font-weight:700;color:#f8fafc;">🖥️ {cname}</span>
                                    <span style="margin-left:12px;">{status_badge}</span>
                                </div>
                                <code style="font-size:12px;color:#94a3b8;">ID: {cid}</code>
                            </div>
                            <div style="display:flex;gap:30px;margin-top:8px;font-size:13px;color:#94a3b8;">
                                <div><strong>Last Heartbeat:</strong> {last_seen_str}</div>
                                <div><strong>Registered At:</strong> {created_str}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    col_actions_1, col_actions_2, col_actions_3 = st.columns([2, 1, 1])

                    # Test push action
                    if cstatus != "revoked":
                        if col_actions_2.button("📡 Send Test Pulse", key=f"pulse_{cid}"):
                            payload = {
                                "source_id": cname.lower().replace(" ", "-"),
                                "payload_id": f"pulse-{uuid.uuid4().hex[:8]}",
                                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                "metrics": {
                                    "cpu_percent": 34.2,
                                    "memory_percent": 58.1,
                                    "disk_percent": 45.0,
                                    "network_latency_ms": 14.2,
                                    "packet_loss_percent": 0.0,
                                },
                                "privacy": {"sanitized": True, "filter_version": "1.0.0"},
                            }
                            # Send pulse with collector token if registered in session state
                            token = st.session_state.get(f"token_{cid}")
                            res = client.send_telemetry(payload, collector_token=token)
                            if res["success"]:
                                st.success(f"Pulse accepted for `{cname}`!")
                                st.rerun()
                            else:
                                st.error(f"Failed to send pulse: {res.get('error')}")

                        if col_actions_3.button("🚫 Revoke Token", key=f"revoke_{cid}"):
                            res = client.revoke_collector(org_id, cid)
                            if res["success"]:
                                st.warning(f"Collector `{cname}` revoked.")
                                st.rerun()
                            else:
                                st.error(f"Revocation failed: {res.get('error')}")

    with tab_enroll:
        st.markdown("### ➕ Enroll New Collector Node")
        st.markdown(
            "Generate a cryptographically random live secret (`sc_live_...`). "
            "The backend hashes this token with SHA-256 and discards the plaintext. "
            "**Copy the token immediately**, as it will never be displayed again."
        )

        with st.form("enroll_collector_form"):
            new_col_name = st.text_input("Collector / Node Name", value="", placeholder="e.g. edge-agent-prod-01")
            submitted = st.form_submit_button("🔑 Generate Collector Token")

            if submitted:
                if not new_col_name.strip():
                    st.error("Please enter a collector name.")
                else:
                    res = client.register_collector(org_id, new_col_name.strip())
                    if res["success"]:
                        data = res["data"]
                        raw_token = data.get("raw_token")
                        cid = data.get("id")
                        st.session_state[f"token_{cid}"] = raw_token
                        st.session_state["just_enrolled"] = data
                        st.success(f"Collector `{new_col_name}` successfully enrolled!")
                    else:
                        st.error(f"Enrollment failed: {res.get('error')}")

        if "just_enrolled" in st.session_state:
            enrolled = st.session_state["just_enrolled"]
            raw_token = enrolled.get("raw_token", "")
            cid = enrolled.get("id", "")
            cname = enrolled.get("name", "")

            st.markdown(
                f"""
                <div style="background-color:rgba(16,185,129,0.1);border:1px solid #10B981;border-radius:8px;padding:16px;margin-top:16px;">
                    <div style="color:#10B981;font-weight:700;font-size:16px;">✅ Collector Enrolled: {cname}</div>
                    <p style="color:#94a3b8;margin-top:4px;font-size:13px;">Save this secret token. It is only shown once!</p>
                    <code style="display:block;background-color:#0f172a;color:#38bdf8;padding:10px;border-radius:6px;font-size:14px;word-break:break-all;">
                        {raw_token}
                    </code>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("#### Quick Integration Snippet:")
            st.code(
                f"""# Export token on target host:
export SENTINEL_COLLECTOR_TOKEN="{raw_token}"

# Run SentinelOps Collector Agent:
python -m collector.agent --backend-url "{client.base_url}" --collector-id "{cid}"
""",
                language="bash",
            )

    with tab_docs:
        st.markdown("### 📖 Collector Deployment Architecture")
        st.markdown(
            """
            #### How SentinelOps Collectors Work:
            1. **Local Privacy Enforcement:**
               The collector runs on your server or edge node. It captures raw CPU, memory, disk, network, and syslog data.
            2. **Deterministic Masking & Allow-Listing:**
               Before any byte leaves localhost, the `PrivacyEngine` strips authorization headers, sanitizes IPv4/IPv6 IPs, hashes sensitive IDs, and drops non-allowlisted properties.
            3. **Secure Telemetry Ingestion:**
               The sanitized payload is pushed to `/api/v1/telemetry` over HTTPS with header `X-Collector-Token: sc_live_...`.
            4. **Tenant Scoping:**
               The backend verifies the SHA-256 token hash, matches the collector to your organization, records the pulse, and routes metrics to the AI anomaly detection engine.
            """
        )
