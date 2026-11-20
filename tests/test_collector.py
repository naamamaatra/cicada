"""
SentinelOps AI - Integration Tests for Member 1: Collector & Privacy Pipeline.
Tests communication, alert triggering on backend, privacy sanitization, and offline buffering.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.storage import storage
from collector.collector import LocalCollector


@pytest.fixture(autouse=True)
def clean_storage():
    """Reset in-memory storage before each test."""
    storage.clear()
    yield
    storage.clear()


def test_collector_privacy_pipeline_with_secrets():
    """
    Test full privacy pipeline:
    Raw event with real hostname + fake secrets -> sanitized -> allow-listed -> backend ingest.
    """
    client = TestClient(app)
    collector = LocalCollector()

    raw_event = collector.generator.generate_raw_event_with_secrets(server_index=0, scenario="normal")

    # Mock requests.post to delegate to FastAPI TestClient
    def mock_post(url, json=None, **kwargs):
        resp = client.post("/api/v1/telemetry", json=json)
        # Adapt test client response to requests-like interface
        mock_resp = MagicMock()
        mock_resp.status_code = resp.status_code
        mock_resp.json.return_value = resp.json()
        mock_resp.text = resp.text
        return mock_resp

    with patch("requests.post", side_effect=mock_post):
        result = collector.process_and_send(raw_event)

    assert result["success"] is True
    assert result["status"] == "SENT"

    # Egress proof verification:
    audit = collector.audit_logger.get_latest()
    assert audit is not None
    assert audit.policy_verdict == "PASS"
    assert audit.source_id == "node_a81f"  # Real hostname 'prod-app-srv-01...' pseudonymized to 'node_a81f'
    assert "db_password" in audit.blocked_fields
    assert "raw_system_logs" in audit.blocked_fields
    assert "db_password" not in audit.safe_payload
    assert "raw_system_logs" not in audit.safe_payload


def test_collector_fleet_normal_phase1():
    """
    Phase 1 Baseline Test:
    Send 3 healthy servers -> all 3 stored in backend with 0 alerts.
    """
    client = TestClient(app)
    collector = LocalCollector()

    def mock_post(url, json=None, **kwargs):
        resp = client.post("/api/v1/telemetry", json=json)
        mock_resp = MagicMock()
        mock_resp.status_code = resp.status_code
        mock_resp.json.return_value = resp.json()
        mock_resp.text = resp.text
        return mock_resp

    with patch("requests.post", side_effect=mock_post):
        fleet_results = collector.send_fleet_normal()

    assert len(fleet_results) == 3
    for res in fleet_results:
        assert res["success"] is True
        assert res["status"] == "SENT"
        assert res["alerts_generated"] == 0

    assert storage.total_telemetry_count() == 3
    assert storage.total_alerts_count() == 0


def test_collector_inject_failure_triggers_alert():
    """
    Phase 1 Failure Flow Test:
    Inject CPU spike (>95%) on node_a81f -> triggers HIGH_CPU alert in backend.
    """
    client = TestClient(app)
    collector = LocalCollector()

    def mock_post(url, json=None, **kwargs):
        resp = client.post("/api/v1/telemetry", json=json)
        mock_resp = MagicMock()
        mock_resp.status_code = resp.status_code
        mock_resp.json.return_value = resp.json()
        mock_resp.text = resp.text
        return mock_resp

    with patch("requests.post", side_effect=mock_post):
        failure_res = collector.inject_failure(source_id="node_a81f", scenario="cpu_spike")

    assert failure_res["success"] is True
    assert failure_res["alerts_generated"] >= 1
    alerts = failure_res["alerts"]
    assert any(a["alert_type"] == "HIGH_CPU" for a in alerts)
    assert any(a["severity"] == "CRITICAL" for a in alerts)


def test_collector_offline_buffering_and_recovery():
    """
    Phase 1 / Phase 4 Reliability Test:
    When backend is down, events are buffered locally.
    When backend is restored, buffer flush delivers events with no loss or duplicates.
    """
    import requests as req
    collector = LocalCollector()

    # Step 1: Backend is down (ConnectionError)
    def mock_connection_error(*args, **kwargs):
        raise req.exceptions.ConnectionError("Failed to connect to backend")

    with patch("requests.post", side_effect=mock_connection_error):
        normal_event = collector.generator.generate_normal(source_id="node_a81f")
        res1 = collector.process_and_send(normal_event)

    assert res1["status"] == "BUFFERED"
    assert collector.buffer.pending_count() == 1

    # Step 2: Backend is restored
    client = TestClient(app)

    def mock_recovered_post(url, json=None, **kwargs):
        resp = client.post("/api/v1/telemetry", json=json)
        mock_resp = MagicMock()
        mock_resp.status_code = resp.status_code
        mock_resp.json.return_value = resp.json()
        return mock_resp

    with patch("requests.post", side_effect=mock_recovered_post):
        flush_res = collector.flush_buffer()

    assert flush_res["status"] == "FLUSHED"
    assert flush_res["flushed_count"] == 1
    assert collector.buffer.pending_count() == 0
    assert storage.total_telemetry_count() == 1


def test_collector_demo_phase1_flow():
    """
    Run full run_phase1_demo() with mock backend.
    Verifies normal fleet + simulated failure + alert + audit.
    """
    client = TestClient(app)
    collector = LocalCollector()

    def mock_post(url, json=None, **kwargs):
        resp = client.post("/api/v1/telemetry", json=json)
        mock_resp = MagicMock()
        mock_resp.status_code = resp.status_code
        mock_resp.json.return_value = resp.json()
        mock_resp.text = resp.text
        return mock_resp

    with patch("requests.post", side_effect=mock_post):
        demo_res = collector.run_phase1_demo()

    assert len(demo_res["fleet_results"]) == 3
    assert demo_res["failure_result"]["alerts_generated"] >= 1
    assert demo_res["latest_audit"] is not None
    assert demo_res["latest_audit"]["policy_verdict"] == "PASS"

