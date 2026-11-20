"""
Unit tests for recommendations.py (Recommendation Engine).
Verifies predefined recommendations for all 6 scenarios, compound scenarios,
priority assignments, manual execution type, and incident linking.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.recommendations import RecommendationEngine
from ai.root_cause import (
    RootCauseAnalyzer,
    RC_WORKLOAD_OVERLOAD,
    RC_MEMORY_LEAK,
    RC_NETWORK_DEGRADATION,
    RC_DATABASE_BOTTLENECK,
    RC_SUSPICIOUS_AUTH,
    RC_COLLECTOR_FAILURE,
    RC_COMPOUND_PRESSURE,
)
from shared.models import Alert, Incident, Recommendation, RootCauseHypothesis
from shared.constants import (
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    ALERT_CPU_SPIKE,
    ALERT_MEMORY_SPIKE,
    ALERT_LATENCY_SPIKE,
    ALERT_PACKET_LOSS_SPIKE,
    ALERT_FAILED_LOGINS_SPIKE,
    ALERT_ERROR_BURST,
    ALERT_COLLECTOR_OFFLINE,
    ALERT_DB_TIMEOUT,
)


@pytest.fixture
def engine():
    return RecommendationEngine()


def _make_incident(scenario_id: str, severity: str = SEVERITY_HIGH) -> Incident:
    hyp = RootCauseHypothesis(
        scenario_id=scenario_id,
        possible_cause="Test possible cause",
        confidence=0.9,
        evidence=["Test evidence"],
        contributing_symptoms=["test_symptom"],
    )
    return Incident(
        id="inc_test_123",
        title="Test Incident Title",
        severity=severity,
        affected_source="node_srv_42",
        tenant_id="tenant_alpha",
        alert_ids=["alt_1"],
        alerts=[],
        root_cause_hint=hyp.possible_cause,
        root_cause_details=hyp,
        created_at="2026-11-20T10:00:00Z",
        updated_at="2026-11-20T10:00:00Z",
    )


def test_recommendation_cpu_overload(engine):
    inc = _make_incident(RC_WORKLOAD_OVERLOAD, SEVERITY_HIGH)
    recs = engine.generate_recommendations(inc)
    assert len(recs) == 1
    assert recs[0].incident_id == "inc_test_123"
    assert recs[0].action == "Inspect resource-intensive processes and workload distribution."
    assert recs[0].execution_type == "manual"
    assert recs[0].priority == "P2"
    assert "node_srv_42" in recs[0].rationale
    assert len(recs[0].description) > 0


def test_recommendation_memory_growth(engine):
    inc = _make_incident(RC_MEMORY_LEAK, SEVERITY_HIGH)
    recs = engine.generate_recommendations(inc)
    assert len(recs) == 1
    assert recs[0].action == "Inspect memory growth and application memory management."
    assert recs[0].execution_type == "manual"


def test_recommendation_network_degradation(engine):
    inc = _make_incident(RC_NETWORK_DEGRADATION, SEVERITY_HIGH)
    recs = engine.generate_recommendations(inc)
    assert len(recs) == 1
    assert recs[0].action == "Inspect network routes, congestion and affected connections."
    assert recs[0].execution_type == "manual"


def test_recommendation_database_timeouts(engine):
    inc = _make_incident(RC_DATABASE_BOTTLENECK, SEVERITY_HIGH)
    recs = engine.generate_recommendations(inc)
    assert len(recs) == 1
    assert recs[0].action == "Inspect query performance and connection usage."
    assert recs[0].execution_type == "manual"


def test_recommendation_failed_logins(engine):
    inc = _make_incident(RC_SUSPICIOUS_AUTH, SEVERITY_CRITICAL)
    recs = engine.generate_recommendations(inc)
    assert len(recs) == 1
    assert recs[0].action == "Review authentication logs and access controls."
    assert recs[0].priority == "P1"
    assert recs[0].execution_type == "manual"


def test_recommendation_missing_heartbeat(engine):
    inc = _make_incident(RC_COLLECTOR_FAILURE, SEVERITY_CRITICAL)
    recs = engine.generate_recommendations(inc)
    assert len(recs) == 1
    assert recs[0].action == "Check collector status and network connectivity."
    assert recs[0].priority == "P1"
    assert recs[0].execution_type == "manual"


def test_compound_scenario_recommendations(engine):
    inc = _make_incident(RC_COMPOUND_PRESSURE, SEVERITY_CRITICAL)
    recs = engine.generate_recommendations(inc)
    # Compound scenario gives multiple actionable recommendations
    assert len(recs) >= 3
    actions = [r.action for r in recs]
    assert "Inspect resource-intensive processes and workload distribution." in actions
    assert "Inspect network routes, congestion and affected connections." in actions
    assert "Check recent deployment or workload changes." in actions
    for r in recs:
        assert r.execution_type == "manual"
        assert r.incident_id == inc.id


def test_automatic_root_cause_diagnosis_if_missing(engine):
    # Incident without prior root_cause_details
    inc = Incident(
        id="inc_auto_diag",
        title="Incident without RC",
        severity=SEVERITY_HIGH,
        affected_source="node_auto",
        tenant_id="tenant_demo",
        alert_ids=["a_mem"],
        alerts=[
            Alert(
                id="a_mem",
                alert_type=ALERT_MEMORY_SPIKE,
                severity=SEVERITY_HIGH,
                source_id="node_auto",
                evidence="Memory reached 92%",
                detection_method="threshold",
                timestamp="2026-11-20T10:00:00Z",
            )
        ],
        created_at="2026-11-20T10:00:00Z",
        updated_at="2026-11-20T10:00:00Z",
    )
    recs = engine.generate_recommendations(inc)
    assert inc.root_cause_details is not None
    assert inc.root_cause_details.scenario_id == RC_MEMORY_LEAK
    assert len(recs) == 1
    assert recs[0].action == "Inspect memory growth and application memory management."
    assert inc.recommendations == recs


def test_standalone_generator(engine):
    recs = engine.generate_for_scenario(
        scenario_id=RC_WORKLOAD_OVERLOAD,
        incident_id="inc_standalone",
        source_id="node_x",
        severity=SEVERITY_CRITICAL,
    )
    assert len(recs) == 1
    assert recs[0].priority == "P1"
    assert recs[0].incident_id == "inc_standalone"
