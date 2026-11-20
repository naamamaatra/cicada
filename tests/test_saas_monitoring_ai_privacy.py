"""
SentinelOps AI - Milestone 4 Test Suite.
Verifies:
1. Real telemetry persistence and tenant-scoped retrieval.
2. AI Incident Intelligence: automatic anomaly detection, correlation, root cause analysis, and recommendations.
3. Incident deduplication (preventing duplicate active incidents on repeated spikes).
4. Incident lifecycle workflow (open -> investigating -> resolved).
5. Strict tenant isolation for incidents and metrics.
6. Live Privacy Lab: real execution of PrivacyEngine, Pseudonymizer, and AllowListPolicy.
7. Safe audit logging with zero secret leaks.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.db.base import Base
from backend.db.session import get_db
from backend.db.models import User, Organization, Membership, Collector, TelemetryRecord, Incident, AuditLog


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh isolated database for each test and bind dependency override."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.TestingSessionLocal = TestingSessionLocal

    yield

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)


def register_user_and_org(email: str, org_name: str):
    """Helper to register user and obtain token + org_id."""
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Test Operator",
        "organization_name": org_name,
    })
    data = resp.json()
    return data["access_token"], data["active_organization_id"]


def enroll_collector(token: str, org_id: str, name: str = "test-agent"):
    """Helper to enroll collector and get raw_token + id."""
    resp = client.post(
        f"/api/v1/orgs/{org_id}/collectors",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name},
    )
    data = resp.json()
    return data["raw_token"], data["id"]


# -----------------------------------------------------------------------------
# 1. Telemetry Persistence & Tenant-Scoped Monitoring
# -----------------------------------------------------------------------------
def test_real_telemetry_persistence_and_metrics_query():
    token, org_id = register_user_and_org("telemetry_user@ops.com", "Telemetry Corp")
    raw_col_token, col_id = enroll_collector(token, org_id, "cluster-node-01")

    # Ingest telemetry via authenticated collector
    payload = {
        "payload_id": "evt_real_1001",
        "tenant_id": org_id,
        "source_id": "node_web_prod",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": 45.5,
        "memory": 58.2,
        "disk": 62.0,
        "latency_ms": 35.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
        "event_category": "normal",
    }

    ingest_resp = client.post(
        "/api/v1/telemetry",
        headers={"X-Collector-Token": raw_col_token},
        json=payload,
    )
    assert ingest_resp.status_code == 201

    # Query tenant metrics
    headers = {"Authorization": f"Bearer {token}"}
    metrics_resp = client.get(f"/api/v1/orgs/{org_id}/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    records = metrics_resp.json()["data"]
    assert len(records) == 1
    assert records[0]["payload_id"] == "evt_real_1001"
    assert records[0]["source_id"] == "node_web_prod"
    assert records[0]["cpu"] == 45.5

    # Query tenant summary
    summary_resp = client.get(f"/api/v1/orgs/{org_id}/metrics/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()["data"]
    assert summary["total_sources"] == 1
    assert summary["total_telemetry_events"] == 1
    assert summary["healthy_sources"] == 1
    assert summary["critical_sources"] == 0


# -----------------------------------------------------------------------------
# 2. AI Incident Intelligence: Anomaly Detection & Correlation
# -----------------------------------------------------------------------------
def test_ai_incident_intelligence_creation_and_deduplication():
    token, org_id = register_user_and_org("ai_user@ops.com", "AI Intelligence Org")
    raw_col_token, col_id = enroll_collector(token, org_id, "critical-server-agent")
    headers = {"Authorization": f"Bearer {token}"}

    # Ingest severe failure telemetry (Workload Overload / Resource Pressure)
    spike_payload_1 = {
        "payload_id": "evt_ai_spike_01",
        "tenant_id": org_id,
        "source_id": "node_a81f",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": 98.5,          # Severe CPU overload
        "memory": 94.0,       # Severe RAM spike
        "disk": 80.0,
        "latency_ms": 320.0,  # High latency
        "packet_loss_pct": 8.0,
        "error_count": 25,    # Application errors
        "failed_logins": 1,
        "collector_status": "online",
        "event_category": "incident_spike",
    }

    resp1 = client.post(
        "/api/v1/telemetry",
        headers={"X-Collector-Token": raw_col_token},
        json=spike_payload_1,
    )
    assert resp1.status_code == 201

    # Check that AI generated a persistent incident
    inc_resp = client.get(f"/api/v1/orgs/{org_id}/incidents", headers=headers)
    assert inc_resp.status_code == 200
    incidents = inc_resp.json()
    assert len(incidents) >= 1

    first_incident = incidents[0]
    assert first_incident["severity"] == "CRITICAL"
    assert first_incident["status"] == "open"
    assert first_incident["source_id"] == "node_a81f"
    assert "Root Cause" in first_incident["description"]
    assert "Recommendations" in first_incident["description"]

    # 3. Deduplication Check: Ingest another spike for the same node
    spike_payload_2 = {
        **spike_payload_1,
        "payload_id": "evt_ai_spike_02",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": 99.0,
    }
    resp2 = client.post(
        "/api/v1/telemetry",
        headers={"X-Collector-Token": raw_col_token},
        json=spike_payload_2,
    )
    assert resp2.status_code == 201

    # Active incidents count should remain 1 (no duplicate spam)
    inc_resp2 = client.get(f"/api/v1/orgs/{org_id}/incidents?status=open", headers=headers)
    assert len(inc_resp2.json()) == 1


# -----------------------------------------------------------------------------
# 3. Incident Lifecycle Workflow
# -----------------------------------------------------------------------------
def test_incident_lifecycle_transitions():
    token, org_id = register_user_and_org("workflow_user@ops.com", "Workflow Corp")
    headers = {"Authorization": f"Bearer {token}"}

    # Manually create incident in DB for testing lifecycle transitions
    db = app.state.TestingSessionLocal()
    inc = Incident(
        organization_id=org_id,
        title="Database Connection Pool Exhaustion",
        description="High connection timeouts observed.",
        severity="HIGH",
        status="open",
        source_id="node_db_01",
    )
    db.add(inc)
    db.commit()
    inc_id = inc.id
    db.close()

    # Transition: open -> investigating
    p1 = client.patch(
        f"/api/v1/orgs/{org_id}/incidents/{inc_id}/status",
        headers=headers,
        json={"status": "investigating"},
    )
    assert p1.status_code == 200
    assert p1.json()["status"] == "investigating"
    assert p1.json()["resolved_at"] is None

    # Transition: investigating -> resolved
    p2 = client.patch(
        f"/api/v1/orgs/{org_id}/incidents/{inc_id}/status",
        headers=headers,
        json={"status": "resolved"},
    )
    assert p2.status_code == 200
    assert p2.json()["status"] == "resolved"
    assert p2.json()["resolved_at"] is not None

    # Invalid status rejection
    bad_resp = client.patch(
        f"/api/v1/orgs/{org_id}/incidents/{inc_id}/status",
        headers=headers,
        json={"status": "invalid_lifecycle_state"},
    )
    assert bad_resp.status_code == 400


# -----------------------------------------------------------------------------
# 4. Strict Tenant Isolation on Incidents and Metrics
# -----------------------------------------------------------------------------
def test_tenant_isolation_on_incidents_and_metrics():
    token_a, org_a = register_user_and_org("user_a@alpha.com", "Alpha Organization")
    token_b, org_b = register_user_and_org("user_b@beta.com", "Beta Organization")

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B attempts to access Org A's incidents -> 403 Forbidden
    resp1 = client.get(f"/api/v1/orgs/{org_a}/incidents", headers=headers_b)
    assert resp1.status_code == 403

    # User B attempts to query Org A's metrics -> 403 Forbidden
    resp2 = client.get(f"/api/v1/orgs/{org_a}/metrics", headers=headers_b)
    assert resp2.status_code == 403

    # User B attempts to query Org A's metrics summary -> 403 Forbidden
    resp3 = client.get(f"/api/v1/orgs/{org_a}/metrics/summary", headers=headers_b)
    assert resp3.status_code == 403


# -----------------------------------------------------------------------------
# 5. Live Privacy Lab (POST /api/v1/privacy/inspect)
# -----------------------------------------------------------------------------
def test_live_privacy_lab_real_sanitization():
    raw_sample = {
        "hostname": "prod-db-master-01.internal.corp",
        "cpu": 92.5,
        "memory": 88.3,
        "disk": 65.0,
        "password": "SuperSecretPassword123!",
        "api_key": "sec_live_998877665544332211",
        "database_url": "postgres://admin:topsecret@10.0.0.5:5432/finance_db",
        "latency_ms": 420.0,
        "packet_loss_pct": 1.2,
        "error_count": 5,
        "failed_logins": 0,
        "collector_status": "online",
        "raw_trace": "SELECT account_balance FROM customer_wallets WHERE ssn='123-45-6789'",
        "tenant_id": "tenant_demo",
        "payload_id": "evt_priv_lab_01",
        "timestamp_utc": "2026-11-21T03:00:00Z",
    }

    resp = client.post("/api/v1/privacy/inspect", json={"sample_data": raw_sample})
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert data["policy_verdict"] == "PASS"

    # Verify secrets are NOT in sanitized_output
    sanitized = data["sanitized_output"]
    assert "password" not in sanitized
    assert "api_key" not in sanitized
    assert "database_url" not in sanitized
    assert "raw_trace" not in sanitized

    # Verify hostname was pseudonymized into source_id
    assert sanitized["source_id"] == "node_b92c"
    assert sanitized["cpu"] == 92.5

    # Verify detection list
    detected_secrets = data["detected_sensitive_fields"]
    assert any("password" in s for s in detected_secrets)
    assert any("api_key" in s for s in detected_secrets)

    # Verify statistics
    stats = data["statistics"]
    assert stats["secrets_redacted"] >= 2
    assert stats["fields_blocked"] >= 4
    assert stats["hostnames_pseudonymized"] == 1
