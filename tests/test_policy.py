"""
SentinelOps AI - Tests for Member 1: Allow-List Policy Gate.
"""

import pytest
from collector.policy import AllowListPolicy


def test_policy_valid_normal_payload():
    policy = AllowListPolicy()
    valid_payload = {
        "payload_id": "evt_test_01",
        "tenant_id": "tenant_demo",
        "source_id": "node_a81f",
        "timestamp_utc": "2026-11-20T16:00:00Z",
        "cpu": 45.5,
        "memory": 60.0,
        "disk": 50.0,
        "latency_ms": 25.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
        "event_category": "normal",
    }
    res = policy.evaluate(valid_payload)
    assert res.allowed is True
    assert len(res.violations) == 0
    assert len(res.blocked_fields) == 0
    assert res.sanitized_payload["cpu"] == 45.5


def test_policy_blocks_unauthorized_fields():
    policy = AllowListPolicy()
    payload_with_unauthorized = {
        "payload_id": "evt_test_02",
        "tenant_id": "tenant_demo",
        "source_id": "node_a81f",
        "timestamp_utc": "2026-11-20T16:00:00Z",
        "cpu": 50.0,
        "memory": 50.0,
        "disk": 50.0,
        "latency_ms": 30.0,
        "packet_loss_pct": 0.0,
        "collector_status": "online",
        # Unauthorized fields that must be blocked:
        "raw_system_logs": "Unauthorized raw log data",
        "user_email": "admin@internal.corp",
        "db_password": "SecretPassword",
        "internal_ip": "10.0.0.1",
    }
    res = policy.evaluate(payload_with_unauthorized)
    # The valid core fields are allowed, while unauthorized fields are blocked and stripped
    assert res.allowed is True
    assert set(res.blocked_fields) == {"raw_system_logs", "user_email", "db_password", "internal_ip"}
    assert "raw_system_logs" not in res.sanitized_payload
    assert "db_password" not in res.sanitized_payload
    assert "internal_ip" not in res.sanitized_payload


def test_policy_rejects_missing_required_fields():
    policy = AllowListPolicy()
    incomplete_payload = {
        "payload_id": "evt_test_03",
        "source_id": "node_a81f",
        # Missing cpu, memory, disk, latency_ms, packet_loss_pct, collector_status
    }
    res = policy.evaluate(incomplete_payload)
    assert res.allowed is False
    assert any("cpu" in v for v in res.violations)
    assert any("memory" in v for v in res.violations)


def test_policy_rejects_out_of_bounds_metrics():
    policy = AllowListPolicy()
    invalid_metrics = {
        "payload_id": "evt_test_04",
        "tenant_id": "tenant_demo",
        "source_id": "node_a81f",
        "timestamp_utc": "2026-11-20T16:00:00Z",
        "cpu": 150.0,  # Invalid > 100
        "memory": -5.0,  # Invalid < 0
        "disk": 50.0,
        "latency_ms": -10.0,  # Invalid negative latency
        "packet_loss_pct": 105.0,  # Invalid > 100
        "error_count": -2,  # Invalid negative
        "failed_logins": -1,  # Invalid negative
        "collector_status": "online",
    }
    res = policy.evaluate(invalid_metrics)
    assert res.allowed is False
    assert len(res.violations) >= 5


def test_policy_rejects_empty_ids():
    policy = AllowListPolicy()
    empty_id_payload = {
        "payload_id": "   ",
        "tenant_id": "tenant_demo",
        "source_id": "",
        "timestamp_utc": "2026-11-20T16:00:00Z",
        "cpu": 50.0,
        "memory": 50.0,
        "disk": 50.0,
        "latency_ms": 30.0,
        "packet_loss_pct": 0.0,
        "collector_status": "online",
    }
    res = policy.evaluate(empty_id_payload)
    assert res.allowed is False
    assert any("payload_id" in v for v in res.violations)
    assert any("source_id" in v for v in res.violations)
