"""
Unit tests for root_cause.py (Root Cause Intelligence Engine).
Tests all 6 canonical scenarios defined in project plan + compound scenario.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.root_cause import (
    RootCauseAnalyzer,
    RC_WORKLOAD_OVERLOAD,
    RC_MEMORY_LEAK,
    RC_NETWORK_DEGRADATION,
    RC_DATABASE_BOTTLENECK,
    RC_SUSPICIOUS_AUTH,
    RC_COLLECTOR_FAILURE,
    RC_COMPOUND_PRESSURE,
    RC_UNSPECIFIED_ANOMALY,
)
from shared.models import Alert, Incident, RootCauseHypothesis, TelemetryPayload
from shared.constants import (
    ALERT_CPU_SPIKE,
    ALERT_MEMORY_SPIKE,
    ALERT_LATENCY_SPIKE,
    ALERT_PACKET_LOSS_SPIKE,
    ALERT_FAILED_LOGINS_SPIKE,
    ALERT_ERROR_BURST,
    ALERT_COLLECTOR_OFFLINE,
    ALERT_DB_TIMEOUT,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
)


@pytest.fixture
def analyzer():
    return RootCauseAnalyzer()


def test_scenario_1_cpu_high_and_error_count_high(analyzer):
    alerts = [
        Alert(
            id="alt_cpu",
            alert_type=ALERT_CPU_SPIKE,
            severity=SEVERITY_CRITICAL,
            source_id="node_app_01",
            tenant_id="tenant_1",
            evidence="CPU reached 98%",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        ),
        Alert(
            id="alt_err",
            alert_type=ALERT_ERROR_BURST,
            severity=SEVERITY_HIGH,
            source_id="node_app_01",
            tenant_id="tenant_1",
            evidence="Application error count reached 45",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:05Z",
        ),
    ]

    hypothesis = analyzer.diagnose_alerts(alerts)
    assert hypothesis.scenario_id == RC_WORKLOAD_OVERLOAD
    assert hypothesis.possible_cause == "Workload overload or resource contention."
    assert hypothesis.confidence >= 0.90
    assert "high_cpu_utilization" in hypothesis.contributing_symptoms
    assert "elevated_error_count" in hypothesis.contributing_symptoms


def test_scenario_2_memory_increasing(analyzer):
    alerts = [
        Alert(
            id="alt_mem",
            alert_type=ALERT_MEMORY_SPIKE,
            severity=SEVERITY_HIGH,
            source_id="node_app_02",
            tenant_id="tenant_1",
            evidence="Memory utilization at 94% exceeded threshold of 90%",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        )
    ]

    hypothesis = analyzer.diagnose_alerts(alerts)
    assert hypothesis.scenario_id == RC_MEMORY_LEAK
    assert hypothesis.possible_cause == "Memory leak or excessive resource usage."
    assert hypothesis.confidence >= 0.85
    assert "high_memory_utilization" in hypothesis.contributing_symptoms


def test_scenario_3_latency_high_and_packet_loss_high(analyzer):
    alerts = [
        Alert(
            id="alt_lat",
            alert_type=ALERT_LATENCY_SPIKE,
            severity=SEVERITY_HIGH,
            source_id="node_net_01",
            tenant_id="tenant_1",
            evidence="Network latency at 850ms",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        ),
        Alert(
            id="alt_loss",
            alert_type=ALERT_PACKET_LOSS_SPIKE,
            severity=SEVERITY_HIGH,
            source_id="node_net_01",
            tenant_id="tenant_1",
            evidence="Packet loss at 12%",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:05Z",
        ),
    ]

    hypothesis = analyzer.diagnose_alerts(alerts)
    assert hypothesis.scenario_id == RC_NETWORK_DEGRADATION
    assert hypothesis.possible_cause == "Network congestion or connectivity degradation."
    assert hypothesis.confidence >= 0.90
    assert "high_network_latency" in hypothesis.contributing_symptoms
    assert "high_packet_loss" in hypothesis.contributing_symptoms


def test_scenario_4_database_timeouts(analyzer):
    alerts = [
        Alert(
            id="alt_db",
            alert_type=ALERT_DB_TIMEOUT,
            severity=SEVERITY_HIGH,
            source_id="node_db_01",
            tenant_id="tenant_1",
            evidence="Database query timeout on pool connection 12",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        )
    ]

    hypothesis = analyzer.diagnose_alerts(alerts)
    assert hypothesis.scenario_id == RC_DATABASE_BOTTLENECK
    assert hypothesis.possible_cause == "Database bottleneck, connection exhaustion or slow queries."
    assert hypothesis.confidence >= 0.90


def test_scenario_5_failed_login_spike(analyzer):
    alerts = [
        Alert(
            id="alt_auth",
            alert_type=ALERT_FAILED_LOGINS_SPIKE,
            severity=SEVERITY_CRITICAL,
            source_id="node_auth_01",
            tenant_id="tenant_1",
            evidence="Repeated authentication failures detected: 7 failed logins",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        )
    ]

    hypothesis = analyzer.diagnose_alerts(alerts)
    assert hypothesis.scenario_id == RC_SUSPICIOUS_AUTH
    assert hypothesis.possible_cause == "Suspicious authentication activity."
    assert hypothesis.confidence >= 0.90


def test_scenario_6_collector_heartbeat_missing(analyzer):
    alerts = [
        Alert(
            id="alt_col",
            alert_type=ALERT_COLLECTOR_OFFLINE,
            severity=SEVERITY_CRITICAL,
            source_id="node_edge_01",
            tenant_id="tenant_1",
            evidence="Collector on node 'node_edge_01' reported status 'offline'",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        )
    ]

    hypothesis = analyzer.diagnose_alerts(alerts)
    assert hypothesis.scenario_id == RC_COLLECTOR_FAILURE
    assert hypothesis.possible_cause == "Collector failure or network connectivity issue."
    assert hypothesis.confidence >= 0.95


def test_compound_resource_and_network_pressure(analyzer):
    # Hackathon Demo Scenario Step 2 & 7:
    # CPU 98%, RAM 94%, Latency 900ms, Packet Loss 15%
    alerts = [
        Alert(
            id="alt_c1",
            alert_type=ALERT_CPU_SPIKE,
            severity=SEVERITY_CRITICAL,
            source_id="node_demo",
            tenant_id="tenant_demo",
            evidence="CPU at 98%",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        ),
        Alert(
            id="alt_c2",
            alert_type=ALERT_LATENCY_SPIKE,
            severity=SEVERITY_CRITICAL,
            source_id="node_demo",
            tenant_id="tenant_demo",
            evidence="Latency at 900ms",
            detection_method="threshold",
            timestamp="2026-11-20T10:00:00Z",
        ),
    ]

    hypothesis = analyzer.diagnose_alerts(alerts)
    assert hypothesis.scenario_id == RC_COMPOUND_PRESSURE
    assert hypothesis.possible_cause == "Resource pressure combined with network degradation."


def test_diagnose_incident_in_place(analyzer):
    incident = Incident(
        id="inc_diag_test",
        title="Test Incident",
        severity=SEVERITY_HIGH,
        affected_source="node_test",
        tenant_id="tenant_test",
        alert_ids=["a1", "a2"],
        alerts=[
            Alert(
                id="a1",
                alert_type=ALERT_CPU_SPIKE,
                severity=SEVERITY_HIGH,
                source_id="node_test",
                evidence="CPU at 96%",
                detection_method="threshold",
                timestamp="2026-11-20T10:00:00Z",
            ),
            Alert(
                id="a2",
                alert_type=ALERT_ERROR_BURST,
                severity=SEVERITY_HIGH,
                source_id="node_test",
                evidence="Errors at 25",
                detection_method="threshold",
                timestamp="2026-11-20T10:00:00Z",
            ),
        ],
        created_at="2026-11-20T10:00:00Z",
        updated_at="2026-11-20T10:00:00Z",
    )

    hypothesis = analyzer.diagnose_incident(incident)
    assert incident.root_cause_hint == hypothesis.possible_cause
    assert incident.root_cause_details is not None
    assert incident.root_cause_details.scenario_id == RC_WORKLOAD_OVERLOAD


def test_diagnose_telemetry_directly(analyzer):
    raw_payload = {
        "payload_id": "evt_raw_1",
        "source_id": "node_direct",
        "cpu": 92.0,
        "memory": 40.0,
        "latency_ms": 30.0,
        "packet_loss_pct": 0.0,
        "error_count": 22,
        "failed_logins": 0,
        "collector_status": "online",
    }
    hyp = analyzer.diagnose_telemetry(raw_payload)
    assert hyp.scenario_id == RC_WORKLOAD_OVERLOAD


def test_empty_alerts_graceful_handling(analyzer):
    hyp = analyzer.diagnose_alerts([])
    assert hyp.scenario_id == RC_UNSPECIFIED_ANOMALY
    assert hyp.confidence == 0.0
