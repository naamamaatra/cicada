"""
SentinelOps AI - Workspace & Settings View.
Manage organization profile, team members, audit trails, and multi-tenant workspaces.
"""

from datetime import datetime, timezone
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from dashboard.api_client import SaaSClient


def render_settings_view(client: SaaSClient):
    st.markdown("## ⚙️ Workspace Settings & Team")
    st.markdown("Manage organization details, team roles, tenant workspaces, and view audit trail records.")

    org = client.active_org
    if not org or not org.get("id"):
        st.warning("⚠️ No active workspace selected.")
        return

    org_id = org["id"]

    tab_org, tab_team, tab_audit, tab_workspaces = st.tabs([
        "🏢 Organization Details",
        "👥 Team & RBAC",
        "📜 Audit Trail",
        "🗂️ Workspaces",
    ])

    # 1. Organization Details
    with tab_org:
        st.markdown("### Workspace Metadata")
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Organization Name", value=org.get("name", "Default"), disabled=True)
            st.text_input("Organization ID", value=org_id, disabled=True)
        with c2:
            st.text_input("Slug", value=org.get("slug", org.get("name", "").lower()), disabled=True)
            st.text_input("Current User Role", value=org.get("role", "Owner").upper(), disabled=True)

        st.markdown(
            """
            <div style="background-color:#1e293b;border:1px solid #334155;border-radius:8px;padding:16px;margin-top:16px;">
                <h4 style="color:#f8fafc;margin-bottom:8px;">🔒 Tenant Boundary Guarantee</h4>
                <p style="color:#94a3b8;font-size:13px;margin:0;">
                    All telemetry, collectors, incidents, and audit logs are strictly partitioned by
                    <code>organization_id</code>. Multi-tenant isolation is enforced at the database level
                    with foreign keys and verified by FastAPI dependency injection.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Team & RBAC
    with tab_team:
        st.markdown("### Workspace Members & Roles")
        with st.spinner("Loading team members..."):
            members = client.list_members(org_id)

        if not members:
            # Fallback to current user if backend doesn't return list
            user = client.user or {}
            members = [{
                "email": user.get("email", "operator@sentinelops.ai"),
                "full_name": user.get("full_name", "Primary Operator"),
                "role": "owner",
                "created_at": "Just now",
            }]

        mem_data = []
        for m in members:
            mem_data.append({
                "Full Name": m.get("full_name", "—"),
                "Email": m.get("email", "—"),
                "Role": m.get("role", "member").upper(),
                "Joined At": str(m.get("created_at", "—"))[:19].replace("T", " "),
            })

        st.dataframe(pd.DataFrame(mem_data), use_container_width=True)

        st.markdown("#### Role Hierarchy & Permissions")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown(
                """
                <div style="background-color:#1e293b;border:1px solid #334155;border-radius:6px;padding:12px;">
                    <strong style="color:#ef4444;">👑 OWNER</strong>
                    <p style="color:#94a3b8;font-size:12px;margin-top:4px;">
                        Full administrative access, billing, workspace deletion, collector enrollment.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(
                """
                <div style="background-color:#1e293b;border:1px solid #334155;border-radius:6px;padding:12px;">
                    <strong style="color:#f59e0b;">🛡️ ADMIN</strong>
                    <p style="color:#94a3b8;font-size:12px;margin-top:4px;">
                        Enroll/revoke collectors, manage team members, resolve incidents.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r3:
            st.markdown(
                """
                <div style="background-color:#1e293b;border:1px solid #334155;border-radius:6px;padding:12px;">
                    <strong style="color:#38bdf8;">🔧 MEMBER</strong>
                    <p style="color:#94a3b8;font-size:12px;margin-top:4px;">
                        View infrastructure, investigate incidents, inspect privacy engine.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with r4:
            st.markdown(
                """
                <div style="background-color:#1e293b;border:1px solid #334155;border-radius:6px;padding:12px;">
                    <strong style="color:#94a3b8;">👁️ VIEWER</strong>
                    <p style="color:#94a3b8;font-size:12px;margin-top:4px;">
                        Read-only access to metrics and dashboards. Cannot alter incident state.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 3. Audit Trail
    with tab_audit:
        st.markdown("### Immutable Workspace Audit Trail")
        st.markdown("Chronological record of security and administrative operations executed in this tenant.")

        with st.spinner("Loading audit logs..."):
            logs = client.list_audit_logs(org_id, limit=50)

        if not logs:
            st.info("No audit entries recorded yet for this workspace.")
        else:
            log_rows = []
            for item in logs:
                meta = item.get("safe_metadata", {})
                meta_str = ", ".join(f"{k}={v}" for k, v in meta.items()) if isinstance(meta, dict) else str(meta)
                log_rows.append({
                    "Timestamp": str(item.get("timestamp", "—"))[:19].replace("T", " "),
                    "Action": item.get("action", "—"),
                    "Resource Type": item.get("resource_type", "—"),
                    "Resource ID": item.get("resource_id", "—") or "—",
                    "Details": meta_str or "—",
                })
            st.dataframe(pd.DataFrame(log_rows), use_container_width=True)

    # 4. Workspaces & Tenant Switching
    with tab_workspaces:
        st.markdown("### Tenant Workspaces")
        all_orgs = client.list_orgs()

        if all_orgs:
            st.markdown("#### Switch Active Workspace")
            org_options = {f"{o['name']} ({o['id'][:8]}...)": o for o in all_orgs}
            current_choice = next(
                (k for k, v in org_options.items() if v["id"] == org_id),
                list(org_options.keys())[0],
            )
            selected_choice = st.selectbox("Select Workspace", list(org_options.keys()), index=list(org_options.keys()).index(current_choice))

            if st.button("🔄 Switch Workspace"):
                selected_org = org_options[selected_choice]
                client.set_active_org(selected_org)
                st.session_state["active_org"] = selected_org
                st.success(f"Switched to workspace `{selected_org['name']}`!")
                st.rerun()

        st.markdown("---")
        st.markdown("#### ➕ Create New Workspace")
        with st.form("create_workspace_form"):
            new_org_name = st.text_input("New Workspace Name", placeholder="e.g. Acme Production Cluster")
            new_org_slug = st.text_input("Workspace Slug (Optional)", placeholder="e.g. acme-prod")
            created = st.form_submit_button("Create Workspace")

            if created:
                if not new_org_name.strip():
                    st.error("Please provide an organization name.")
                else:
                    res = client.create_org(new_org_name.strip(), new_org_slug.strip() or None)
                    if res["success"]:
                        new_org = res["data"]
                        client.set_active_org(new_org)
                        st.session_state["active_org"] = new_org
                        st.success(f"Created and switched to workspace `{new_org['name']}`!")
                        st.rerun()
                    else:
                        st.error(f"Workspace creation failed: {res.get('error')}")
