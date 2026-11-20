"""
Unit tests for correlation.py (Alert Correlation Engine).
"""

import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.correlation import AlertCorrelator
from shared.models import Alert
from shared.constants import (
    ALERT_CPU_SPIKE,
    ALERT_MEMORY_SPIKE,
    ALERT_LATENCY_SPIKE,
    ALERT_PACKET_LOSS_SPIKE,
    ALERT_FAILED_LOGINS_SPIKE,
    ALERT_COLLECTOR_OFFLINE,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    INCIDENT_STATUS_OPEN,
    INCIDENT_STATUS_RESOLVED,
)


@pytest.fixture
def correlator():
    return AlertCorrelator(time_window_seconds=300)


def test_correlate_related_resource_alerts(correlator):
    # Alert 1: CPU spike
    alert1 = Alert(
        id="alt_1",
        alert_type=ALERT_CPU_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="node_prod_1",
        tenant_id="tenant_alpha",
        evidence="CPU reached 96%",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:00Z",
    )
    # Alert 2: Memory spike on same node 10 seconds later
    alert2 = Alert(
        id="alt_2",
        alert_type=ALERT_MEMORY_SPIKE,
        severity=SEVERITY_CRITICAL,
        source_id="node_prod_1",
        tenant_id="tenant_alpha",
        evidence="Memory reached 95%",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:10Z",
    )

    inc1 = correlator.correlate_alert(alert1)
    inc2 = correlator.correlate_alert(alert2)

    # Must be merged into single incident
    assert inc1.id == inc2.id
    assert len(inc2.alerts) == 2
    assert inc2.severity == SEVERITY_CRITICAL  # Escalated to CRITICAL
    assert "alt_1" in inc2.alert_ids
    assert "alt_2" in inc2.alert_ids
    assert len(inc2.evidence_summary) == 2


def test_unrelated_sources_do_not_merge(correlator):
    alert_node_1 = Alert(
        id="alt_node1",
        alert_type=ALERT_CPU_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="node_01",
        tenant_id="tenant_alpha",
        evidence="CPU high on node 1",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:00Z",
    )
    alert_node_2 = Alert(
        id="alt_node2",
        alert_type=ALERT_CPU_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="node_02",
        tenant_id="tenant_alpha",
        evidence="CPU high on node 2",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:05Z",
    )

    inc1 = correlator.correlate_alert(alert_node_1)
    inc2 = correlator.correlate_alert(alert_node_2)

    assert inc1.id != inc2.id
    assert inc1.affected_source == "node_01"
    assert inc2.affected_source == "node_02"


def test_duplicate_alert_suppression(correlator):
    alert = Alert(
        id="alt_dup",
        alert_type=ALERT_LATENCY_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="node_01",
        tenant_id="tenant_alpha",
        payload_id="payload_100",
        metric_value=300.0,
        evidence="Latency high",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:00Z",
    )

    inc1 = correlator.correlate_alert(alert)
    inc2 = correlator.correlate_alert(alert)  # send identical alert again

    assert inc1.id == inc2.id
    assert len(inc1.alerts) == 1  # Not duplicated


def test_time_window_separation(correlator):
    # Alert 1 at 10:00:00
    alert1 = Alert(
        id="alt_old",
        alert_type=ALERT_CPU_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="node_01",
        tenant_id="tenant_alpha",
        evidence="Old spike",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:00Z",
    )
    # Alert 2 at 10:15:00 (15 minutes later, exceeding 300s window)
    alert2 = Alert(
        id="alt_new",
        alert_type=ALERT_CPU_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="node_01",
        tenant_id="tenant_alpha",
        evidence="New spike after long gap",
        detection_method="threshold",
        timestamp="2026-11-20T10:15:00Z",
    )

    inc1 = correlator.correlate_alert(alert1)
    inc2 = correlator.correlate_alert(alert2)

    assert inc1.id != inc2.id


def test_tenant_separation(correlator):
    alert_t1 = Alert(
        id="alt_t1",
        alert_type=ALERT_CPU_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="shared_name",
        tenant_id="tenant_1",
        evidence="Spike in tenant 1",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:00Z",
    )
    alert_t2 = Alert(
        id="alt_t2",
        alert_type=ALERT_CPU_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="shared_name",
        tenant_id="tenant_2",
        evidence="Spike in tenant 2",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:05Z",
    )

    inc1 = correlator.correlate_alert(alert_t1)
    inc2 = correlator.correlate_alert(alert_t2)

    assert inc1.id != inc2.id
    assert inc1.tenant_id == "tenant_1"
    assert inc2.tenant_id == "tenant_2"


def test_auto_recovery_and_manual_resolve(correlator):
    alert = Alert(
        id="alt_rec",
        alert_type=ALERT_FAILED_LOGINS_SPIKE,
        severity=SEVERITY_HIGH,
        source_id="node_auth",
        tenant_id="tenant_alpha",
        evidence="Auth failure spike",
        detection_method="threshold",
        timestamp="2026-11-20T10:00:00Z",
    )
    inc = correlator.correlate_alert(alert)
    assert inc.status == INCIDENT_STATUS_OPEN

    # Node returns to healthy state -> check_recovery
    resolved = correlator.check_recovery("node_auth", "tenant_alpha", is_healthy=True)
    assert len(resolved) == 1
    assert resolved[0].id == inc.id
    assert resolved[0].status == INCIDENT_STATUS_RESOLVED
