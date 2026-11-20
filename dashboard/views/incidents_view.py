"""
SentinelOps AI - Incident Management Workflow View.
Provides incident table, severity & status filtering, detailed AI explanations,
and real-time status transitions: Open -> Investigating -> Resolved.
"""

import streamlit as st
from dashboard.api_client import SaaSClient


def render_incidents_view(client: SaaSClient):
    org_id = client.active_org["id"] if client.active_org else ""
    st.title("🚨 Incident Management")
    st.caption("AI-correlated incidents, evidence summaries, root-cause deductions, and resolution workflow.")

    # Filter Bar
    fc1, fc2, fc3 = st.columns([1, 1, 2])
    with fc1:
        status_filter = st.selectbox(
            "Status Filter:",
            ["all", "open", "investigating", "resolved", "dismissed"],
            index=0,
        )
    with fc2:
        severity_filter = st.selectbox(
            "Severity Filter:",
            ["all", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
            index=0,
        )

    # Fetch incidents with filters
    incidents = client.list_incidents(
        org_id,
        status=status_filter if status_filter != "all" else None,
        severity=severity_filter if severity_filter != "all" else None,
    )

    if not incidents:
        st.info("✅ No incidents matching the selected criteria.")
        return

    st.write(f"Showing **{len(incidents)}** incident(s):")

    # Render each incident as an expandable management card
    for inc in incidents:
        inc_id = inc["id"]
        sev = inc.get("severity", "MEDIUM")
        stat = inc.get("status", "open").upper()
        title = inc.get("title", "Incident")
        source = inc.get("source_id", "Unknown")
        first_seen = str(inc.get("first_detected_at", ""))[:19]
        last_updated = str(inc.get("last_updated_at", ""))[:19]
        desc = inc.get("description", "No description available.")

        badge_color = "#EF4444" if sev == "CRITICAL" else ("#F59E0B" if sev == "HIGH" else "#38BDF8")

        with st.expander(f"[{sev}] {title} — Node: {source} ({stat})", expanded=(stat == "OPEN")):
            ic1, ic2 = st.columns([3, 1])

            with ic1:
                st.markdown(f"""
                <div style='margin-bottom: 12px;'>
                    <span style='background: rgba(239, 68, 68, 0.15); color: {badge_color}; border: 1px solid {badge_color}; padding: 3px 8px; border-radius: 4px; font-weight: bold;'>
                        {sev} SEVERITY
                    </span>
                    <span style='background: #334155; color: #E2E8F0; padding: 3px 8px; border-radius: 4px; margin-left: 8px; font-weight: bold;'>
                        STATUS: {stat}
                    </span>
                </div>
                """, unsafe_allow_html=True)

                st.write(f"**Affected Node:** `{source}`")
                st.write(f"**First Detected:** {first_seen} UTC • **Last Updated:** {last_updated} UTC")

                st.markdown("#### 🔍 AI Root Cause & Remediation:")
                st.markdown(f"```text\n{desc}\n```")

            with ic2:
                st.markdown("#### Incident Workflow")
                if stat != "INVESTIGATING":
                    if st.button("🔍 Investigate", key=f"inv_{inc_id}", use_container_width=True):
                        res = client.update_incident_status(org_id, inc_id, "investigating")
                        if res["success"]:
                            st.success("Incident marked as Investigating.")
                            st.rerun()

                if stat != "RESOLVED":
                    if st.button("✅ Mark Resolved", key=f"res_{inc_id}", use_container_width=True, type="primary"):
                        res = client.update_incident_status(org_id, inc_id, "resolved")
                        if res["success"]:
                            st.success("Incident resolved and closed.")
                            st.rerun()

                if stat != "DISMISSED":
                    if st.button("🚫 Dismiss", key=f"dis_{inc_id}", use_container_width=True):
                        res = client.update_incident_status(org_id, inc_id, "dismissed")
                        if res["success"]:
                            st.info("Incident dismissed.")
                            st.rerun()
