"""
SentinelOps AI — Privacy-First Observability & Autonomous Incident Intelligence SaaS.
SaaS Platform View Entry Point (Milestone 5).
"""

import streamlit as st
from dashboard.api_client import SaaSClient
from dashboard.views import (
    render_auth_view,
    render_onboarding_view,
    render_overview_view,
    render_infrastructure_view,
    render_incidents_view,
    render_ai_investigations_view,
    render_privacy_lab_view,
    render_collectors_view,
    render_settings_view,
)


def get_saas_client() -> SaaSClient:
    """Retrieve or initialize SaaSClient in session state."""
    if "saas_client" not in st.session_state:
        st.session_state["saas_client"] = SaaSClient()
    client = st.session_state["saas_client"]

    # Re-sync tokens if present in session state
    if "auth_token" in st.session_state and not client.token:
        client.token = st.session_state["auth_token"]
        client.user = st.session_state.get("user")
        client.active_org = st.session_state.get("active_org")

    return client


def render_saas_platform():
    client = get_saas_client()

    # Check backend connectivity
    is_backend_online = client.check_health()

    # 1. AUTHENTICATION ROUTE
    if not client.token:
        render_auth_view(client)
        return

    # Keep session state in sync with client
    st.session_state["auth_token"] = client.token
    st.session_state["user"] = client.user
    st.session_state["active_org"] = client.active_org

    # 2. GUIDED ONBOARDING ROUTE
    if st.session_state.get("in_onboarding", False):
        c_nav1, c_nav2 = st.columns([4, 1])
        c_nav1.markdown("### 🚀 Guided Workspace Onboarding")
        if c_nav2.button("✕ Exit to Dashboard", key="exit_onboarding_top"):
            st.session_state["in_onboarding"] = False
            st.session_state["onboarding_completed"] = True
            st.rerun()

        render_onboarding_view(client)
        return

    # 3. TOP ENTERPRISE HEADER
    with st.container():
        h1, h2, h3, h4 = st.columns([3, 2, 2, 1])
        with h1:
            st.markdown(
                """
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:24px;">🛡️</span>
                    <div>
                        <span style="font-size:18px;font-weight:800;letter-spacing:-0.5px;color:#f8fafc;">SentinelOps</span>
                        <span style="font-size:14px;color:#38bdf8;font-weight:600;margin-left:4px;">AI SaaS</span>
                        <div style="font-size:11px;color:#64748b;">Autonomous Incident Intelligence</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with h2:
            org_name = client.active_org.get("name", "Active Workspace") if client.active_org else "Workspace"
            org_id = client.active_org.get("id", "")[:8] if client.active_org else ""
            st.markdown(
                f"""
                <div style="background-color:#1e293b;border:1px solid #334155;border-radius:6px;padding:6px 12px;font-size:12px;">
                    <div style="color:#64748b;">ACTIVE WORKSPACE</div>
                    <div style="font-weight:700;color:#38bdf8;">🏢 {org_name} <span style="color:#64748b;font-weight:400;">({org_id}...)</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with h3:
            user_email = client.user.get("email", "operator") if client.user else "operator"
            st.markdown(
                f"""
                <div style="background-color:#1e293b;border:1px solid #334155;border-radius:6px;padding:6px 12px;font-size:12px;">
                    <div style="color:#64748b;">AUTHENTICATED OPERATOR</div>
                    <div style="font-weight:700;color:#10b981;">👤 {user_email}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with h4:
            if st.button("🚪 Sign Out", key="top_sign_out"):
                client.logout()
                st.session_state.clear()
                st.rerun()

    # Backend health indicator
    if not is_backend_online:
        st.error("⚠️ Backend API is currently unreachable at http://127.0.0.1:8000. Ensure the FastAPI backend is running.")

    # 4. PRIMARY PRODUCT NAVIGATION
    pages = [
        "📊 Overview",
        "🖥️ Infrastructure",
        "🚨 Incidents",
        "🧠 AI Investigations",
        "🛡️ Privacy Lab",
        "📡 Collectors",
        "⚙️ Settings",
    ]

    selected_page = st.radio(
        label="Navigation",
        options=pages,
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border:none;border-top:1px solid #1e293b;margin:12px 0 20px 0;'/>", unsafe_allow_html=True)

    # 5. VIEW ROUTING
    if selected_page == "📊 Overview":
        render_overview_view(client)
    elif selected_page == "🖥️ Infrastructure":
        render_infrastructure_view(client)
    elif selected_page == "🚨 Incidents":
        render_incidents_view(client)
    elif selected_page == "🧠 AI Investigations":
        render_ai_investigations_view(client)
    elif selected_page == "🛡️ Privacy Lab":
        render_privacy_lab_view(client)
    elif selected_page == "📡 Collectors":
        render_collectors_view(client)
    elif selected_page == "⚙️ Settings":
        render_settings_view(client)
