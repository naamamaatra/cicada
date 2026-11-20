"""
SentinelOps AI - Root Cause Intelligence Engine (root_cause.py)
Implements 6 core root-cause inference scenarios defined in the project plan:
1. CPU HIGH + ERROR COUNT HIGH -> Workload overload or resource contention
2. MEMORY INCREASING -> Memory leak or excessive resource usage
3. LATENCY HIGH + PACKET LOSS HIGH -> Network congestion or connectivity degradation
4. DATABASE TIMEOUTS -> Database bottleneck, connection exhaustion or slow queries
5. FAILED LOGIN SPIKE -> Suspicious authentication activity
6. COLLECTOR HEARTBEAT MISSING -> Collector failure or network connectivity issue

Plus compound multi-symptom deduction, explainable evidence generation, and hypothesis confidence scoring.
"""

from typing import List, Dict, Any, Optional, Set, Union
from shared.models import Alert, Incident, RootCauseHypothesis, TelemetryPayload
from shared.constants import (
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    ALERT_CPU_SPIKE,
    ALERT_MEMORY_SPIKE,
    ALERT_DISK_SPIKE,
    ALERT_LATENCY_SPIKE,
    ALERT_PACKET_LOSS_SPIKE,
    ALERT_FAILED_LOGINS_SPIKE,
    ALERT_ERROR_BURST,
    ALERT_COLLECTOR_OFFLINE,
    ALERT_MULTIVARIATE_ANOMALY,
    ALERT_DB_TIMEOUT,
    RC_WORKLOAD_OVERLOAD,
    RC_MEMORY_LEAK,
    RC_NETWORK_DEGRADATION,
    RC_DATABASE_BOTTLENECK,
    RC_SUSPICIOUS_AUTH,
    RC_COLLECTOR_FAILURE,
)

RC_COMPOUND_PRESSURE = "COMPOUND_RESOURCE_NETWORK_PRESSURE"
RC_UNSPECIFIED_ANOMALY = "UNSPECIFIED_ANOMALY"


class RootCauseAnalyzer:
    """
    Infers explainable root cause hypotheses from alerts, incidents, or telemetry metrics.
    Produces probabilistic possible causes with transparent evidence and symptom trails.
    """

    # Human-readable possible cause statements (Probabilistic, not absolute assertions)
    SCENARIO_CAUSES: Dict[str, str] = {
        RC_WORKLOAD_OVERLOAD: "Workload overload or resource contention.",
        RC_MEMORY_LEAK: "Memory leak or excessive resource usage.",
        RC_NETWORK_DEGRADATION: "Network congestion or connectivity degradation.",
        RC_DATABASE_BOTTLENECK: "Database bottleneck, connection exhaustion or slow queries.",
        RC_SUSPICIOUS_AUTH: "Suspicious authentication activity.",
        RC_COLLECTOR_FAILURE: "Collector failure or network connectivity issue.",
        RC_COMPOUND_PRESSURE: "Resource pressure combined with network degradation.",
        RC_UNSPECIFIED_ANOMALY: "Unspecified operational anomaly requiring manual inspection.",
    }

    def __init__(self, default_confidence: float = 0.85):
        self.default_confidence = default_confidence

    def _extract_symptoms(self, alerts: List[Alert]) -> Dict[str, Any]:
        """Extracts symptom flags, metric peaks, and evidence lists from alerts."""
        symptoms: Set[str] = set()
        evidence_list: List[str] = []
        alert_types: Set[str] = {a.alert_type for a in alerts}

        has_cpu = False
        has_errors = False
        has_memory = False
        has_latency = False
        has_packet_loss = False
        has_failed_logins = False
        has_collector_offline = False
        has_db_timeout = False

        for a in alerts:
            evidence_list.append(a.evidence)

            if a.alert_type == ALERT_CPU_SPIKE:
                has_cpu = True
                symptoms.add("high_cpu_utilization")
            elif a.alert_type == ALERT_ERROR_BURST:
                has_errors = True
                symptoms.add("elevated_error_count")
            elif a.alert_type == ALERT_MEMORY_SPIKE:
                has_memory = True
                symptoms.add("high_memory_utilization")
            elif a.alert_type == ALERT_LATENCY_SPIKE:
                has_latency = True
                symptoms.add("high_network_latency")
            elif a.alert_type == ALERT_PACKET_LOSS_SPIKE:
                has_packet_loss = True
                symptoms.add("high_packet_loss")
            elif a.alert_type == ALERT_FAILED_LOGINS_SPIKE:
                has_failed_logins = True
                symptoms.add("repeated_failed_logins")
            elif a.alert_type == ALERT_COLLECTOR_OFFLINE:
                has_collector_offline = True
                symptoms.add("collector_offline")
            elif a.alert_type == ALERT_DB_TIMEOUT:
                has_db_timeout = True
                symptoms.add("database_timeout")
            elif a.alert_type == ALERT_MULTIVARIATE_ANOMALY:
                symptoms.add("multivariate_anomaly")
                if a.metric_name == "cpu":
                    has_cpu = True
                elif a.metric_name == "memory":
                    has_memory = True
                elif a.metric_name == "latency_ms":
                    has_latency = True

        return {
            "alert_types": alert_types,
            "symptoms": sorted(list(symptoms)),
            "evidence": evidence_list,
            "has_cpu": has_cpu,
            "has_errors": has_errors,
            "has_memory": has_memory,
            "has_latency": has_latency,
            "has_packet_loss": has_packet_loss,
            "has_failed_logins": has_failed_logins,
            "has_collector_offline": has_collector_offline,
            "has_db_timeout": has_db_timeout,
        }

    def diagnose_alerts(self, alerts: List[Alert]) -> RootCauseHypothesis:
        """
        Diagnoses root cause from a list of alerts.
        Evaluates the 6 canonical scenarios and compound incident patterns.
        """
        if not alerts:
            return RootCauseHypothesis(
                scenario_id=RC_UNSPECIFIED_ANOMALY,
                possible_cause="No active alerts to evaluate.",
                confidence=0.0,
                evidence=["Zero alerts provided for root cause analysis."],
                contributing_symptoms=[],
            )

        info = self._extract_symptoms(alerts)
        symptoms = info["symptoms"]
        evidence = info["evidence"]

        # 1. Collector Offline (Priority 1: System Unavailability)
        if info["has_collector_offline"]:
            return RootCauseHypothesis(
                scenario_id=RC_COLLECTOR_FAILURE,
                possible_cause=self.SCENARIO_CAUSES[RC_COLLECTOR_FAILURE],
                confidence=0.98,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 2. Failed Login Spike (Security Incident)
        if info["has_failed_logins"]:
            return RootCauseHypothesis(
                scenario_id=RC_SUSPICIOUS_AUTH,
                possible_cause=self.SCENARIO_CAUSES[RC_SUSPICIOUS_AUTH],
                confidence=0.95,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 3. Database Timeout
        if info["has_db_timeout"]:
            return RootCauseHypothesis(
                scenario_id=RC_DATABASE_BOTTLENECK,
                possible_cause=self.SCENARIO_CAUSES[RC_DATABASE_BOTTLENECK],
                confidence=0.92,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 4. Compound Scenario: High Resource Pressure + Network Degradation (Demo Step 2/Step 7)
        if (info["has_cpu"] or info["has_memory"]) and (info["has_latency"] or info["has_packet_loss"]):
            return RootCauseHypothesis(
                scenario_id=RC_COMPOUND_PRESSURE,
                possible_cause=self.SCENARIO_CAUSES[RC_COMPOUND_PRESSURE],
                confidence=0.94,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 5. Scenario 1: CPU HIGH + ERROR COUNT HIGH (Workload Overload)
        if info["has_cpu"] and info["has_errors"]:
            return RootCauseHypothesis(
                scenario_id=RC_WORKLOAD_OVERLOAD,
                possible_cause=self.SCENARIO_CAUSES[RC_WORKLOAD_OVERLOAD],
                confidence=0.92,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 6. Scenario 3: LATENCY HIGH + PACKET LOSS HIGH (Network Degradation)
        if info["has_latency"] and info["has_packet_loss"]:
            return RootCauseHypothesis(
                scenario_id=RC_NETWORK_DEGRADATION,
                possible_cause=self.SCENARIO_CAUSES[RC_NETWORK_DEGRADATION],
                confidence=0.93,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 7. Scenario 2: MEMORY INCREASING / HIGH (Memory Leak)
        if info["has_memory"]:
            return RootCauseHypothesis(
                scenario_id=RC_MEMORY_LEAK,
                possible_cause=self.SCENARIO_CAUSES[RC_MEMORY_LEAK],
                confidence=0.88,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 8. Single Symptom Fallbacks
        if info["has_cpu"]:
            return RootCauseHypothesis(
                scenario_id=RC_WORKLOAD_OVERLOAD,
                possible_cause=self.SCENARIO_CAUSES[RC_WORKLOAD_OVERLOAD],
                confidence=0.82,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        if info["has_latency"] or info["has_packet_loss"]:
            return RootCauseHypothesis(
                scenario_id=RC_NETWORK_DEGRADATION,
                possible_cause=self.SCENARIO_CAUSES[RC_NETWORK_DEGRADATION],
                confidence=0.82,
                evidence=evidence,
                contributing_symptoms=symptoms,
            )

        # 9. Generic / Fallback Anomaly
        return RootCauseHypothesis(
            scenario_id=RC_UNSPECIFIED_ANOMALY,
            possible_cause=self.SCENARIO_CAUSES[RC_UNSPECIFIED_ANOMALY],
            confidence=0.60,
            evidence=evidence,
            contributing_symptoms=symptoms,
        )

    def diagnose_incident(self, incident: Incident) -> RootCauseHypothesis:
        """
        Diagnoses the root cause for an entire incident and enriches the incident in-place.
        """
        hypothesis = self.diagnose_alerts(incident.alerts)
        incident.root_cause_hint = hypothesis.possible_cause
        incident.root_cause_details = hypothesis
        return hypothesis

    def diagnose_telemetry(self, telemetry: Union[Dict[str, Any], TelemetryPayload]) -> RootCauseHypothesis:
        """
        Directly evaluates raw or sanitized telemetry values against the 6 root-cause scenarios.
        Convenient for quick health evaluations.
        """
        if isinstance(telemetry, dict):
            cpu = float(telemetry.get("cpu", 0.0) or 0.0)
            mem = float(telemetry.get("memory", 0.0) or 0.0)
            lat = float(telemetry.get("latency_ms", 0.0) or 0.0)
            loss = float(telemetry.get("packet_loss_pct", 0.0) or 0.0)
            err = int(telemetry.get("error_count", 0) or 0)
            auth = int(telemetry.get("failed_logins", 0) or 0)
            status = str(telemetry.get("collector_status", "online") or "online").lower()
            source = str(telemetry.get("source_id", "node_unknown"))
        else:
            cpu = telemetry.cpu
            mem = telemetry.memory
            lat = telemetry.latency_ms
            loss = telemetry.packet_loss_pct
            err = telemetry.error_count
            auth = telemetry.failed_logins
            status = telemetry.collector_status.lower()
            source = telemetry.source_id

        # Collector Offline
        if status == "offline":
            return RootCauseHypothesis(
                scenario_id=RC_COLLECTOR_FAILURE,
                possible_cause=self.SCENARIO_CAUSES[RC_COLLECTOR_FAILURE],
                confidence=0.98,
                evidence=[f"Collector on node '{source}' reported status 'offline'."],
                contributing_symptoms=["collector_offline"],
            )

        # Failed Logins Spike
        if auth >= 3:
            return RootCauseHypothesis(
                scenario_id=RC_SUSPICIOUS_AUTH,
                possible_cause=self.SCENARIO_CAUSES[RC_SUSPICIOUS_AUTH],
                confidence=0.95,
                evidence=[f"Repeated authentication failures detected: {auth} failed logins on {source}."],
                contributing_symptoms=["repeated_failed_logins"],
            )

        # Compound Resource + Network
        if (cpu > 85.0 or mem > 85.0) and (lat > 250.0 or loss > 5.0):
            return RootCauseHypothesis(
                scenario_id=RC_COMPOUND_PRESSURE,
                possible_cause=self.SCENARIO_CAUSES[RC_COMPOUND_PRESSURE],
                confidence=0.94,
                evidence=[
                    f"CPU: {cpu:.1f}%, RAM: {mem:.1f}%, Latency: {lat:.1f}ms, Packet Loss: {loss:.1f}% on {source}."
                ],
                contributing_symptoms=["high_resource_pressure", "network_degradation"],
            )

        # Scenario 1: CPU + Errors
        if cpu > 85.0 and err >= 10:
            return RootCauseHypothesis(
                scenario_id=RC_WORKLOAD_OVERLOAD,
                possible_cause=self.SCENARIO_CAUSES[RC_WORKLOAD_OVERLOAD],
                confidence=0.92,
                evidence=[f"CPU utilization at {cpu:.1f}% with error count {err} on {source}."],
                contributing_symptoms=["high_cpu_utilization", "elevated_error_count"],
            )

        # Scenario 3: Latency + Packet Loss
        if lat > 250.0 and loss > 5.0:
            return RootCauseHypothesis(
                scenario_id=RC_NETWORK_DEGRADATION,
                possible_cause=self.SCENARIO_CAUSES[RC_NETWORK_DEGRADATION],
                confidence=0.93,
                evidence=[f"Network latency at {lat:.1f}ms and packet loss at {loss:.1f}% on {source}."],
                contributing_symptoms=["high_network_latency", "high_packet_loss"],
            )

        # Scenario 2: High Memory
        if mem > 90.0:
            return RootCauseHypothesis(
                scenario_id=RC_MEMORY_LEAK,
                possible_cause=self.SCENARIO_CAUSES[RC_MEMORY_LEAK],
                confidence=0.88,
                evidence=[f"Memory utilization at {mem:.1f}% on {source}."],
                contributing_symptoms=["high_memory_utilization"],
            )

        # Unspecified / Healthy
        return RootCauseHypothesis(
            scenario_id=RC_UNSPECIFIED_ANOMALY,
            possible_cause="Metrics within operational boundaries or minor non-correlated deviation.",
            confidence=0.50,
            evidence=[f"Current metrics on {source}: CPU={cpu:.1f}%, RAM={mem:.1f}%, Latency={lat:.1f}ms."],
            contributing_symptoms=[],
        )
