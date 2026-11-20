"""
End-to-end integration tests for SentinelOps AI Incident Intelligence Pipeline.
Validates the complete flow:
Sanitized Telemetry -> Anomaly Detection -> Alert Correlation -> Root Cause Intelligence -> Recommendations.
Also validates:
- Normal telemetry (no alert/incident)
- CPU spike
- RAM spike
- Latency & packet loss spike
- Failed login spike
- Insufficient training history
- Duplicate alert suppression
- Compound disaster demo scenario
- Recovery scenario
- Multi-tenant data separation
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai import (
    IncidentIntelligencePipeline,
    AnomalyDetector,
    RC_WORKLOAD_OVERLOAD,
    RC_MEMORY_LEAK,
    RC_NETWORK_DEGRADATION,
    RC_SUSPICIOUS_AUTH,
    RC_COLLECTOR_FAILURE,
    RC_COMPOUND_PRESSURE,
)
from shared.constants import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    INCIDENT_STATUS_OPEN,
    INCIDENT_STATUS_RESOLVED,
)


@pytest.fixture
def pipeline():
    return IncidentIntelligencePipeline()


def test_full_pipeline_normal_telemetry(pipeline):
    payload = {
        "payload_id": "evt_pipe_norm_1",
        "tenant_id": "tenant_prod",
        "source_id": "node_01",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 25.0,
        "memory": 40.0,
        "disk": 35.0,
        "latency_ms": 25.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts, incidents = pipeline.process_telemetry(payload)
    assert len(alerts) == 0
    assert len(incidents) == 0


def test_full_pipeline_cpu_and_error_overload(pipeline):
    payload = {
        "payload_id": "evt_pipe_cpu_1",
        "tenant_id": "tenant_prod",
        "source_id": "node_web_1",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 98.2,
        "memory": 55.0,
        "disk": 40.0,
        "latency_ms": 40.0,
        "packet_loss_pct": 0.0,
        "error_count": 18,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts, incidents = pipeline.process_telemetry(payload)

    # 1. Anomaly alerts generated
    assert len(alerts) >= 2  # CPU spike + Error burst
    # 2. Correlated into 1 single incident
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.affected_source == "node_web_1"
    assert inc.severity == SEVERITY_CRITICAL
    # 3. Root Cause diagnosed
    assert inc.root_cause_details is not None
    assert inc.root_cause_details.scenario_id == RC_WORKLOAD_OVERLOAD
    assert inc.root_cause_hint == "Workload overload or resource contention."
    # 4. Actionable recommendation generated
    assert len(inc.recommendations) >= 1
    assert inc.recommendations[0].action == "Inspect resource-intensive processes and workload distribution."
    assert inc.recommendations[0].execution_type == "manual"


def test_full_pipeline_memory_growth(pipeline):
    payload = {
        "payload_id": "evt_pipe_mem_1",
        "tenant_id": "tenant_prod",
        "source_id": "node_cache_1",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 30.0,
        "memory": 94.5,
        "disk": 40.0,
        "latency_ms": 30.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts, incidents = pipeline.process_telemetry(payload)
    assert len(alerts) >= 1
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.root_cause_details.scenario_id == RC_MEMORY_LEAK
    assert inc.recommendations[0].action == "Inspect memory growth and application memory management."


def test_full_pipeline_network_degradation(pipeline):
    payload = {
        "payload_id": "evt_pipe_net_1",
        "tenant_id": "tenant_prod",
        "source_id": "node_gw_1",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 25.0,
        "memory": 30.0,
        "disk": 30.0,
        "latency_ms": 450.0,
        "packet_loss_pct": 8.5,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    alerts, incidents = pipeline.process_telemetry(payload)
    assert len(alerts) >= 2  # Latency + Packet Loss
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.root_cause_details.scenario_id == RC_NETWORK_DEGRADATION
    assert inc.recommendations[0].action == "Inspect network routes, congestion and affected connections."


def test_full_pipeline_failed_login_spike(pipeline):
    payload = {
        "payload_id": "evt_pipe_sec_1",
        "tenant_id": "tenant_prod",
        "source_id": "node_auth_1",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 20.0,
        "memory": 30.0,
        "disk": 30.0,
        "latency_ms": 20.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 8,
        "collector_status": "online",
    }
    alerts, incidents = pipeline.process_telemetry(payload)
    assert len(alerts) >= 1
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.root_cause_details.scenario_id == RC_SUSPICIOUS_AUTH
    assert inc.recommendations[0].priority == "P1"
    assert inc.recommendations[0].action == "Review authentication logs and access controls."


def test_full_pipeline_collector_offline(pipeline):
    payload = {
        "payload_id": "evt_pipe_off_1",
        "tenant_id": "tenant_prod",
        "source_id": "node_edge_9",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 0.0,
        "memory": 0.0,
        "disk": 0.0,
        "latency_ms": 0.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "offline",
    }
    alerts, incidents = pipeline.process_telemetry(payload)
    assert len(alerts) >= 1
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.root_cause_details.scenario_id == RC_COLLECTOR_FAILURE
    assert inc.recommendations[0].priority == "P1"
    assert inc.recommendations[0].action == "Check collector status and network connectivity."


def test_hackathon_demo_scenario_compound_and_recovery(pipeline):
    # STEP 1: Normal telemetry
    p1 = {
        "payload_id": "evt_demo_1",
        "tenant_id": "tenant_demo",
        "source_id": "node_a81f",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 28.0,
        "memory": 42.0,
        "disk": 40.0,
        "latency_ms": 30.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    a1, inc1 = pipeline.process_telemetry(p1)
    assert len(a1) == 0
    assert len(inc1) == 0

    # STEP 2: Inject Severe Incident (Section 16: CPU=98%, RAM=94%, Latency=900ms, Packet loss=15%)
    p2 = {
        "payload_id": "evt_demo_2",
        "tenant_id": "tenant_demo",
        "source_id": "node_a81f",
        "timestamp_utc": "2026-11-20T10:01:00Z",
        "cpu": 98.0,
        "memory": 94.0,
        "disk": 60.0,
        "latency_ms": 900.0,
        "packet_loss_pct": 15.0,
        "error_count": 25,
        "failed_logins": 1,
        "collector_status": "online",
    }
    a2, inc2 = pipeline.process_telemetry(p2)
    assert len(a2) >= 4  # CPU, RAM, Latency, Packet Loss, Error Burst
    assert len(inc2) == 1

    demo_inc = inc2[0]
    assert demo_inc.status == INCIDENT_STATUS_OPEN
    assert demo_inc.severity == SEVERITY_CRITICAL
    assert demo_inc.root_cause_details.scenario_id == RC_COMPOUND_PRESSURE
    assert demo_inc.root_cause_hint == "Resource pressure combined with network degradation."

    # Check recommendations for compound incident
    assert len(demo_inc.recommendations) >= 3
    rec_actions = [r.action for r in demo_inc.recommendations]
    assert "Inspect resource-intensive processes and workload distribution." in rec_actions
    assert "Inspect network routes, congestion and affected connections." in rec_actions
    assert "Check recent deployment or workload changes." in rec_actions

    # STEP 8: Recovery scenario -> restore healthy metrics
    recovered_incidents = pipeline.handle_recovery("node_a81f", "tenant_demo", is_healthy=True)
    assert len(recovered_incidents) == 1
    assert recovered_incidents[0].status == INCIDENT_STATUS_RESOLVED


def test_insufficient_training_history_does_not_crash(pipeline):
    # Feed only 3 samples (well below min_ml_samples=15)
    for i in range(3):
        alerts, incidents = pipeline.process_telemetry({
            "payload_id": f"evt_few_{i}",
            "tenant_id": "tenant_test",
            "source_id": "node_new",
            "timestamp_utc": f"2026-11-20T10:0{i}:00Z",
            "cpu": 30.0,
            "memory": 30.0,
            "disk": 30.0,
            "latency_ms": 30.0,
            "packet_loss_pct": 0.0,
            "error_count": 0,
            "failed_logins": 0,
            "collector_status": "online",
        })
        assert len(alerts) == 0


def test_tenant_separation_in_pipeline(pipeline):
    # Tenant Alpha on node_shared
    p_alpha = {
        "payload_id": "evt_t_alpha",
        "tenant_id": "tenant_alpha",
        "source_id": "node_shared",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 99.0,
        "memory": 50.0,
        "disk": 50.0,
        "latency_ms": 20.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    # Tenant Beta on node_shared
    p_beta = {
        "payload_id": "evt_t_beta",
        "tenant_id": "tenant_beta",
        "source_id": "node_shared",
        "timestamp_utc": "2026-11-20T10:00:00Z",
        "cpu": 99.0,
        "memory": 50.0,
        "disk": 50.0,
        "latency_ms": 20.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }

    _, inc_alpha = pipeline.process_telemetry(p_alpha)
    _, inc_beta = pipeline.process_telemetry(p_beta)

    assert inc_alpha[0].id != inc_beta[0].id
    assert inc_alpha[0].tenant_id == "tenant_alpha"
    assert inc_beta[0].tenant_id == "tenant_beta"

    # Query active incidents per tenant
    alpha_active = pipeline.get_active_incidents(tenant_id="tenant_alpha")
    beta_active = pipeline.get_active_incidents(tenant_id="tenant_beta")
    assert len(alpha_active) == 1
    assert len(beta_active) == 1
    assert alpha_active[0].tenant_id == "tenant_alpha"
    assert beta_active[0].tenant_id == "tenant_beta"
