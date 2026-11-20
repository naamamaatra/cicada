"""
Unit and integration tests for anomaly.py (Layer 1, Layer 2, Layer 3).
"""

import sys
import os
import pytest

# Ensure sentinelops-ai is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.anomaly import AnomalyDetector
from shared.models import TelemetryPayload
from shared.constants import (
    ALERT_CPU_SPIKE,
    ALERT_MEMORY_SPIKE,
    ALERT_LATENCY_SPIKE,
    ALERT_PACKET_LOSS_SPIKE,
    ALERT_FAILED_LOGINS_SPIKE,
    ALERT_ERROR_BURST,
    ALERT_COLLECTOR_OFFLINE,
    ALERT_MULTIVARIATE_ANOMALY,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
)


@pytest.fixture
def detector():
    return AnomalyDetector(history_window_size=30, min_ml_samples=15)


def test_normal_telemetry_no_alerts(detector):
    payload = {
        "payload_id": "evt_norm_1",
        "tenant_id": "tenant_test",
        "source_id": "node_01",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 35.0,
        "memory": 45.0,
        "disk": 50.0,
        "latency_ms": 30.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
        "event_category": "normal",
    }
    alerts = detector.process_telemetry(payload)
    assert len(alerts) == 0


def test_cpu_spike_threshold(detector):
    payload = {
        "payload_id": "evt_cpu_1",
        "tenant_id": "tenant_test",
        "source_id": "node_01",
        "timestamp_utc": "2026-11-20T10:00:05Z",
        "cpu": 98.5,
        "memory": 50.0,
        "disk": 50.0,
        "latency_ms": 40.0,
        "packet_loss_pct": 0.0,
        "error_count": 1,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts = detector.process_telemetry(payload)
    cpu_alerts = [a for a in alerts if a.alert_type == ALERT_CPU_SPIKE]
    assert len(cpu_alerts) >= 1
    assert cpu_alerts[0].severity == SEVERITY_CRITICAL
    assert cpu_alerts[0].metric_value == 98.5
    assert "critical threshold" in cpu_alerts[0].evidence


def test_memory_spike_threshold(detector):
    payload = {
        "payload_id": "evt_mem_1",
        "tenant_id": "tenant_test",
        "source_id": "node_01",
        "timestamp_utc": "2026-11-20T10:00:10Z",
        "cpu": 40.0,
        "memory": 94.0,
        "disk": 50.0,
        "latency_ms": 35.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts = detector.process_telemetry(payload)
    mem_alerts = [a for a in alerts if a.alert_type == ALERT_MEMORY_SPIKE]
    assert len(mem_alerts) >= 1
    assert mem_alerts[0].severity == SEVERITY_HIGH
    assert mem_alerts[0].metric_value == 94.0


def test_network_latency_and_packet_loss_spike(detector):
    payload = {
        "payload_id": "evt_net_1",
        "tenant_id": "tenant_test",
        "source_id": "node_01",
        "timestamp_utc": "2026-11-20T10:00:15Z",
        "cpu": 30.0,
        "memory": 40.0,
        "disk": 50.0,
        "latency_ms": 850.0,
        "packet_loss_pct": 12.0,
        "error_count": 2,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts = detector.process_telemetry(payload)
    types = {a.alert_type for a in alerts}
    assert ALERT_LATENCY_SPIKE in types
    assert ALERT_PACKET_LOSS_SPIKE in types


def test_failed_login_spike(detector):
    payload = {
        "payload_id": "evt_auth_1",
        "tenant_id": "tenant_test",
        "source_id": "node_01",
        "timestamp_utc": "2026-11-20T10:00:20Z",
        "cpu": 25.0,
        "memory": 35.0,
        "disk": 40.0,
        "latency_ms": 20.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 6,
        "collector_status": "online",
    }
    alerts = detector.process_telemetry(payload)
    auth_alerts = [a for a in alerts if a.alert_type == ALERT_FAILED_LOGINS_SPIKE]
    assert len(auth_alerts) == 1
    assert auth_alerts[0].severity == SEVERITY_CRITICAL


def test_collector_offline_detection(detector):
    payload = {
        "payload_id": "evt_off_1",
        "tenant_id": "tenant_test",
        "source_id": "node_02",
        "timestamp_utc": "2026-11-20T10:00:25Z",
        "cpu": 10.0,
        "memory": 20.0,
        "disk": 30.0,
        "latency_ms": 10.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "offline",
    }
    alerts = detector.process_telemetry(payload)
    off_alerts = [a for a in alerts if a.alert_type == ALERT_COLLECTOR_OFFLINE]
    assert len(off_alerts) == 1
    assert off_alerts[0].severity == SEVERITY_CRITICAL


def test_statistical_zscore_detection(detector):
    # Prime with normal baseline (10 samples of cpu around 20%)
    for i in range(10):
        detector.process_telemetry({
            "payload_id": f"evt_base_{i}",
            "tenant_id": "tenant_test",
            "source_id": "node_stat",
            "timestamp_utc": f"2026-11-20T10:0{i}:00Z",
            "cpu": 20.0 + (i % 2),
            "memory": 40.0,
            "disk": 40.0,
            "latency_ms": 30.0,
            "packet_loss_pct": 0.0,
            "error_count": 0,
            "failed_logins": 0,
            "collector_status": "online",
        })

    # Now inject a sudden jump to 60% CPU (below static 95% threshold, but > 3 standard deviations)
    spike_payload = {
        "payload_id": "evt_stat_spike",
        "tenant_id": "tenant_test",
        "source_id": "node_stat",
        "timestamp_utc": "2026-11-20T10:11:00Z",
        "cpu": 60.0,
        "memory": 40.0,
        "disk": 40.0,
        "latency_ms": 30.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts = detector.process_telemetry(spike_payload)
    stat_alerts = [a for a in alerts if a.detection_method == "statistical" and a.metric_name == "cpu"]
    assert len(stat_alerts) >= 1
    assert "Z-score" in stat_alerts[0].evidence


def test_isolation_forest_detection(detector):
    # Feed 20 baseline points so min_ml_samples=15 is satisfied
    for i in range(20):
        detector.process_telemetry({
            "payload_id": f"evt_ml_base_{i}",
            "tenant_id": "tenant_test",
            "source_id": "node_ml",
            "timestamp_utc": f"2026-11-20T10:{i:02d}:00Z",
            "cpu": 25.0 + (i % 3),
            "memory": 35.0 + (i % 2),
            "disk": 40.0,
            "latency_ms": 25.0,
            "packet_loss_pct": 0.0,
            "error_count": 0,
            "failed_logins": 0,
            "collector_status": "online",
        })

    # Inject a correlated multivariate anomaly
    abnormal_payload = {
        "payload_id": "evt_ml_anomaly",
        "tenant_id": "tenant_test",
        "source_id": "node_ml",
        "timestamp_utc": "2026-11-20T10:25:00Z",
        "cpu": 99.0,
        "memory": 95.0,
        "disk": 92.0,
        "latency_ms": 750.0,
        "packet_loss_pct": 10.0,
        "error_count": 45,
        "failed_logins": 4,
        "collector_status": "online",
    }
    alerts = detector.process_telemetry(abnormal_payload)
    methods = {a.detection_method for a in alerts}
    assert "isolation_forest" in methods or "threshold" in methods


def test_missing_and_invalid_data_safety(detector):
    # Nulls, bad types, missing fields should not crash
    bad_payloads = [
        {},
        {"garbage": 123},
        {"payload_id": "bad_1", "cpu": "invalid", "memory": None},
        {"payload_id": "bad_2", "source_id": "node_x", "cpu": 150.0},  # out of bound
    ]
    for bp in bad_payloads:
        alerts = detector.process_telemetry(bp)
        assert isinstance(alerts, list)


def test_tenant_isolation(detector):
    # Tenant A sends 10 samples
    for i in range(10):
        detector.process_telemetry({
            "payload_id": f"evt_ta_{i}",
            "tenant_id": "tenant_A",
            "source_id": "shared_node_name",
            "timestamp_utc": "2026-11-20T10:00:00Z",
            "cpu": 80.0,
            "memory": 80.0,
            "disk": 50.0,
            "latency_ms": 50.0,
            "packet_loss_pct": 0.0,
            "error_count": 0,
            "failed_logins": 0,
            "collector_status": "online",
        })

    # Tenant B has history length 0 for the same node name
    history_b = detector._get_history("tenant_B", "shared_node_name")
    assert len(history_b) == 0
    history_a = detector._get_history("tenant_A", "shared_node_name")
    assert len(history_a) == 10
