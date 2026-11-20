"""
SentinelOps AI - Phase 1 Backend Test Suite.
Verifies telemetry validation, in-memory storage, alert engine, and all REST endpoints.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.main import app
from backend.storage import storage


@pytest.fixture(autouse=True)
def clean_storage():
    """Reset in-memory storage before each test for test isolation."""
    storage.clear()
    yield
    storage.clear()


client = TestClient(app)


# Sample valid payload helper
def make_valid_payload(**kwargs):
    base = {
        "payload_id": "evt_test_001",
        "tenant_id": "tenant_demo",
        "source_id": "node_a81f",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": 45.0,
        "memory": 55.0,
        "disk": 60.0,
        "latency_ms": 32.5,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
        "event_category": "normal",
    }
    base.update(kwargs)
    return base


# 1. Backend starts & root endpoint works
def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["project_name"] == "SentinelOps AI"
    assert json_data["data"]["status"] == "online"


# 2. Health endpoint works
def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["status"] == "HEALTHY"
    assert json_data["telemetry_count"] == 0


# 3. Valid telemetry is accepted
def test_ingest_valid_telemetry():
    payload = make_valid_payload(payload_id="evt_001", source_id="node_1")
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["payload_id"] == "evt_001"
    assert json_data["alerts_generated"] == 0


# 4. Invalid CPU value (> 100) is rejected
def test_reject_invalid_cpu_high():
    payload = make_valid_payload(cpu=105.0)
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["success"] is False
    assert any("cpu" in err["field"] for err in json_data["errors"])


# 5. Invalid CPU value (< 0) is rejected
def test_reject_invalid_cpu_negative():
    payload = make_valid_payload(cpu=-5.0)
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["success"] is False


# 6. Invalid packet loss (> 100) is rejected
def test_reject_invalid_packet_loss():
    payload = make_valid_payload(packet_loss_pct=105.0)
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["success"] is False
    assert any("packet_loss_pct" in err["field"] for err in json_data["errors"])


# 7. Negative latency is rejected
def test_reject_negative_latency():
    payload = make_valid_payload(latency_ms=-10.0)
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["success"] is False
    assert any("latency_ms" in err["field"] for err in json_data["errors"])


# 8. Empty ID is rejected
def test_reject_empty_id():
    payload = make_valid_payload(source_id="   ")
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["success"] is False


# 9. Telemetry retrieval & pagination/limit work
def test_get_telemetry_records():
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="evt_1", source_id="node_1"))
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="evt_2", source_id="node_2"))

    response = client.get("/api/v1/telemetry")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2

    # Latest record should be evt_2 (newest first)
    assert data[0]["payload_id"] == "evt_2"


# 10. Latest telemetry endpoint works
def test_get_latest_telemetry():
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="evt_1", source_id="node_1"))
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="evt_2", source_id="node_2"))

    response = client.get("/api/v1/telemetry/latest")
    assert response.status_code == 200
    assert response.json()["data"]["payload_id"] == "evt_2"

    # Filter latest by source
    resp_source = client.get("/api/v1/telemetry/latest?source_id=node_1")
    assert resp_source.status_code == 200
    assert resp_source.json()["data"]["payload_id"] == "evt_1"


# 11. Source filtering works
def test_get_telemetry_by_source():
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="evt_1", source_id="node_1"))
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="evt_2", source_id="node_2"))

    response = client.get("/api/v1/telemetry/node_1")
    assert response.status_code == 200
    records = response.json()["data"]
    assert len(records) == 1
    assert records[0]["source_id"] == "node_1"


# 12. Threshold alerts are generated when exceeded
def test_alerts_generated_on_threshold():
    spike_payload = make_valid_payload(
        payload_id="evt_spike_01",
        source_id="node_critical",
        cpu=96.5,          # > 90 -> HIGH_CPU
        memory=92.0,       # > 90 -> HIGH_MEMORY
        latency_ms=320.0,  # > 250 -> HIGH_LATENCY
        failed_logins=6,   # >= 5 -> SECURITY_FAILED_LOGINS
    )
    response = client.post("/api/v1/telemetry", json=spike_payload)
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["alerts_generated"] == 4

    # Verify alerts endpoint returns them
    alerts_resp = client.get("/api/v1/alerts")
    assert alerts_resp.status_code == 200
    alerts_data = alerts_resp.json()["data"]
    assert len(alerts_data) == 4

    alert_types = [a["alert_type"] for a in alerts_data]
    assert "HIGH_CPU" in alert_types
    assert "HIGH_MEMORY" in alert_types
    assert "HIGH_LATENCY" in alert_types
    assert "SECURITY_FAILED_LOGINS" in alert_types


# 13. Healthy telemetry produces no critical alerts
def test_healthy_telemetry_produces_no_alerts():
    healthy_payload = make_valid_payload(
        payload_id="evt_healthy_01",
        cpu=30.0,
        memory=40.0,
        disk=50.0,
        latency_ms=25.0,
        packet_loss_pct=0.0,
        error_count=0,
        failed_logins=0,
    )
    response = client.post("/api/v1/telemetry", json=healthy_payload)
    assert response.status_code == 201
    assert response.json()["alerts_generated"] == 0

    alerts_resp = client.get("/api/v1/alerts")
    assert len(alerts_resp.json()["data"]) == 0


# 14. Metrics summary returns accurate fleet counts
def test_metrics_summary():
    # Node 1: Healthy
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="e1", source_id="node_healthy", cpu=30.0))
    # Node 2: Warning (CPU = 78%)
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="e2", source_id="node_warning", cpu=78.0))
    # Node 3: Critical (CPU = 95%)
    client.post("/api/v1/telemetry", json=make_valid_payload(payload_id="e3", source_id="node_crit", cpu=95.0))

    response = client.get("/api/v1/metrics/summary")
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["total_sources"] == 3
    assert data["total_telemetry_events"] == 3
    assert data["healthy_sources"] == 1
    assert data["warning_sources"] == 1
    assert data["critical_sources"] == 1
    assert data["active_alert_count"] == 1  # 1 critical CPU alert from node_crit

