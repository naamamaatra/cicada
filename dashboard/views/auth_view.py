"""
SentinelOps AI - Authentication & Workspace Onboarding View.
Handles User Registration, Login, and Fast-Track Demo Sign-In.
"""

import streamlit as st
from dashboard.api_client import SaaSClient


def render_auth_view(client: SaaSClient):
    st.markdown("""
    <div style='text-align: center; margin-bottom: 24px;'>
        <h1 style='color: #38BDF8; font-size: 2.2em; margin-bottom: 4px;'>🛡️ SentinelOps AI</h1>
        <p style='color: #94A3B8; font-size: 1.1em;'>Privacy-First Infrastructure Observability & Autonomous Incident Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    c1, col, c2 = st.columns([1, 2, 1])
    with col:
        mode = st.radio("Access SentinelOps Workspace:", ["Sign In", "Create New Account"], horizontal=True)

        if mode == "Sign In":
            with st.form("signin_form"):
                st.subheader("Welcome Back")
                email = st.text_input("Work Email", placeholder="operator@sentinelops.ai")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In to Workspace", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        with st.spinner("Authenticating with SentinelOps Security Gateway..."):
                            res = client.login(email.strip(), password)
                            if res["success"]:
                                st.session_state["client"] = client
                                st.session_state["authenticated"] = True
                                st.session_state["current_page"] = "Overview"
                                st.success("Authenticated successfully! Loading workspace...")
                                st.rerun()
                            else:
                                st.error(res["error"])

            st.markdown("---")
            st.markdown("#### ⚡ Hackathon Quick Evaluation")
            st.caption("Judge or Evaluator? Click below to instantly auto-provision a verified workspace:")
            if st.button("🚀 One-Click Demo Sign In", use_container_width=True):
                with st.spinner("Provisioning demo tenant workspace..."):
                    reg_res = client.register(
                        email="judge@sentinelops.ai",
                        password="Password123!",
                        full_name="Hackathon Evaluator",
                        organization_name="Sentinel Production Fleet",
                    )
                    if not reg_res["success"]:
                        # Already exists, login
                        client.login("judge@sentinelops.ai", "Password123!")

                    st.session_state["client"] = client
                    st.session_state["authenticated"] = True
                    st.session_state["current_page"] = "Overview"
                    st.rerun()

        else:  # Create Account
            with st.form("register_form"):
                st.subheader("Create Your Organization Account")
                full_name = st.text_input("Full Name", placeholder="Alex Vance")
                email = st.text_input("Work Email", placeholder="alex@acmecorp.com")
                org_name = st.text_input("Organization / Workspace Name", placeholder="Acme Cloud Systems")
                password = st.text_input("Password (min 8 chars)", type="password", placeholder="••••••••")
                register_submitted = st.form_submit_button("Register & Create Workspace", use_container_width=True, type="primary")

                if register_submitted:
                    if not full_name or not email or not password or len(password) < 8:
                        st.error("Please fill in all fields (password must be at least 8 characters).")
                    else:
                        with st.spinner("Creating tenant organization & security identity..."):
                            res = client.register(email.strip(), password, full_name.strip(), org_name.strip())
                            if res["success"]:
                                st.session_state["client"] = client
                                st.session_state["authenticated"] = True
                                st.session_state["current_page"] = "Onboarding"
                                st.session_state["onboarding_step"] = 1
                                st.success("Organization created! Launching onboarding wizard...")
                                st.rerun()
                            else:
                                st.error(res["error"])
