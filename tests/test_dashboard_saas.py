"""
SentinelOps AI - Tests for SaaS Dashboard API Client and Views (Milestone 5).
Verifies HTTP client request formation, auth state handling, and view module imports.
"""

import pytest
from unittest.mock import patch, MagicMock
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


def test_saas_client_init_and_headers():
    client = SaaSClient("http://localhost:8000")
    assert client.base_url == "http://localhost:8000"
    assert client.token is None
    assert client.user is None
    assert client.active_org is None

    # Without token
    headers = client._headers()
    assert headers["Content-Type"] == "application/json"
    assert "Authorization" not in headers

    # With JWT token
    client.token = "fake-jwt-token"
    headers_with_jwt = client._headers()
    assert headers_with_jwt["Authorization"] == "Bearer fake-jwt-token"

    # With collector token
    headers_with_col = client._headers(collector_token="sc_live_test123")
    assert headers_with_col["X-Collector-Token"] == "sc_live_test123"


@patch("requests.get")
def test_saas_client_check_health(mock_get):
    client = SaaSClient()

    # Success case
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    assert client.check_health() is True

    # Error case
    mock_get.side_effect = Exception("Connection refused")
    assert client.check_health() is False


@patch("requests.post")
def test_saas_client_register(mock_post):
    client = SaaSClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "access_token": "token-123",
        "user": {"id": "usr-1", "email": "test@sentinelops.ai", "full_name": "Test User"},
        "active_organization_id": "org-1",
    }
    mock_post.return_value = mock_resp

    res = client.register("test@sentinelops.ai", "SecretPass123!", "Test User", "Test Org")
    assert res["success"] is True
    assert client.token == "token-123"
    assert client.active_org["id"] == "org-1"


@patch("requests.post")
def test_saas_client_login(mock_post):
    client = SaaSClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "token-login",
        "user": {"id": "usr-2", "email": "user@sentinelops.ai"},
        "active_organization_id": "org-2",
    }
    mock_post.return_value = mock_resp

    res = client.login("user@sentinelops.ai", "SecretPass123!")
    assert res["success"] is True
    assert client.token == "token-login"
    assert client.user["email"] == "user@sentinelops.ai"

    client.logout()
    assert client.token is None
    assert client.user is None


@patch("requests.get")
def test_saas_client_orgs_and_members(mock_get):
    client = SaaSClient()
    client.token = "token-123"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"id": "org-1", "name": "Primary Org", "role": "owner"}]
    mock_get.return_value = mock_resp

    orgs = client.list_orgs()
    assert len(orgs) == 1
    assert orgs[0]["name"] == "Primary Org"

    members = client.list_members("org-1")
    assert len(members) == 1


@patch("requests.get")
@patch("requests.post")
@patch("requests.delete")
def test_saas_client_collectors(mock_delete, mock_post, mock_get):
    client = SaaSClient()
    client.token = "token-123"

    # List
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [{"id": "col-1", "name": "agent-1", "status": "online"}]
    cols = client.list_collectors("org-1")
    assert len(cols) == 1
    assert cols[0]["name"] == "agent-1"

    # Register
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {"id": "col-2", "name": "agent-2", "raw_token": "sc_live_xyz"}
    res_reg = client.register_collector("org-1", "agent-2")
    assert res_reg["success"] is True
    assert res_reg["data"]["raw_token"] == "sc_live_xyz"

    # Revoke
    mock_delete.return_value.status_code = 200
    res_del = client.revoke_collector("org-1", "col-2")
    assert res_del["success"] is True


@patch("requests.get")
@patch("requests.patch")
def test_saas_client_incidents(mock_patch, mock_get):
    client = SaaSClient()
    client.token = "token-123"

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {"id": "inc-1", "title": "High CPU Anomaly", "severity": "HIGH", "status": "open"}
    ]
    incidents = client.list_incidents("org-1")
    assert len(incidents) == 1
    assert incidents[0]["title"] == "High CPU Anomaly"

    mock_patch.return_value.status_code = 200
    mock_patch.return_value.json.return_value = {"id": "inc-1", "status": "resolved"}
    res_patch = client.update_incident_status("org-1", "inc-1", "resolved")
    assert res_patch["success"] is True
    assert res_patch["data"]["status"] == "resolved"


@patch("requests.post")
def test_saas_client_privacy_inspect(mock_post):
    client = SaaSClient()
    client.token = "token-123"

    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "status": "success",
        "egress_payload": {"metrics": {"cpu_percent": 45.0}},
        "statistics": {"total_dropped_fields": 2},
    }

    res = client.inspect_privacy({"token": "secret", "metrics": {"cpu_percent": 45.0}})
    assert res["success"] is True
    assert res["data"]["statistics"]["total_dropped_fields"] == 2


def test_views_are_importable():
    """Verify all dashboard view modules are callable functions."""
    assert callable(render_auth_view)
    assert callable(render_onboarding_view)
    assert callable(render_overview_view)
    assert callable(render_infrastructure_view)
    assert callable(render_incidents_view)
    assert callable(render_ai_investigations_view)
    assert callable(render_privacy_lab_view)
    assert callable(render_collectors_view)
    assert callable(render_settings_view)
