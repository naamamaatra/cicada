"""
SentinelOps AI - Recommendation Engine (recommendations.py)
Generates explainable, prioritized, and actionable operational recommendations
based on root-cause hypotheses, detected anomalies, and incident contexts.

Predefined Recommendations (per Project Plan Section 9):
- CPU overload: Inspect resource-intensive processes and workload distribution.
- Memory growth: Inspect memory growth and application memory management.
- Network degradation: Inspect network routes, congestion and affected connections.
- Database timeouts: Inspect query performance and connection usage.
- Failed login spike: Review authentication logs and access controls.
- Missing heartbeat: Check collector status and network connectivity.

Strictly adheres to privacy-first, human-in-the-loop assisted operations:
All recommendations are marked with execution_type="manual" (never unattended).
"""

from typing import List, Dict, Any, Optional
import uuid

from shared.models import Incident, Recommendation, RootCauseHypothesis
from shared.constants import (
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    RC_WORKLOAD_OVERLOAD,
    RC_MEMORY_LEAK,
    RC_NETWORK_DEGRADATION,
    RC_DATABASE_BOTTLENECK,
    RC_SUSPICIOUS_AUTH,
    RC_COLLECTOR_FAILURE,
)
from ai.root_cause import RootCauseAnalyzer, RC_COMPOUND_PRESSURE, RC_UNSPECIFIED_ANOMALY


class RecommendationEngine:
    """
    Engine that translates root cause hypotheses into concrete, prioritized investigation steps.
    """

    # Structured knowledge base mapping scenarios to actionable guidance
    RECOMMENDATION_TEMPLATES: Dict[str, Dict[str, Any]] = {
        RC_WORKLOAD_OVERLOAD: {
            "action": "Inspect resource-intensive processes and workload distribution.",
            "description": (
                "1. Run top / htop / Process Explorer on the affected node to identify top CPU-consuming processes.\n"
                "2. Review application thread dump and worker concurrency limits.\n"
                "3. Check for recent surge in request arrival rates or asynchronous task queues.\n"
                "4. Distribute traffic across healthy replica nodes or scale compute resources."
            ),
            "rationale_template": "High CPU utilization and application error bursts suggest compute resource exhaustion on node '{source_id}'.",
        },
        RC_MEMORY_LEAK: {
            "action": "Inspect memory growth and application memory management.",
            "description": (
                "1. Profile memory allocation with heap dump analysis (e.g. tracemalloc, pprof, VisualVM).\n"
                "2. Check Garbage Collection (GC) pause times and heap fragmentation.\n"
                "3. Review unclosed file descriptors, cached objects, and global state retention in recent deployments.\n"
                "4. Gracefully cycle affected worker process or restart application service."
            ),
            "rationale_template": "Steadily rising or saturated RAM usage on node '{source_id}' indicates possible memory leak or cache bloat.",
        },
        RC_NETWORK_DEGRADATION: {
            "action": "Inspect network routes, congestion and affected connections.",
            "description": (
                "1. Inspect traceroute and ping latency across gateway, switches, and transit hops.\n"
                "2. Check interface packet drops, CRC error counters, and MTU configuration.\n"
                "3. Verify active socket connections (`netstat -anp` or `ss -s`) for socket exhaustion.\n"
                "4. Failover traffic to secondary network route or availability zone."
            ),
            "rationale_template": "Elevated latency and packet loss detected on node '{source_id}' indicate network path or NIC degradation.",
        },
        RC_DATABASE_BOTTLENECK: {
            "action": "Inspect query performance and connection usage.",
            "description": (
                "1. Check database slow query log and lock wait graphs.\n"
                "2. Review connection pool metrics (active vs idle connections vs max limits).\n"
                "3. Verify indexing on recently updated queries and schema migrations.\n"
                "4. Terminate long-running locking queries and increase pool size if warranted."
            ),
            "rationale_template": "Database timeout alerts on node '{source_id}' point to connection exhaustion or blocking queries.",
        },
        RC_SUSPICIOUS_AUTH: {
            "action": "Review authentication logs and access controls.",
            "description": (
                "1. Inspect authentication logs for burst patterns, source IP clusters, and targeted accounts.\n"
                "2. Verify if automated credential stuffing or brute-force attack is underway.\n"
                "3. Temporarily rate-limit or IP-block suspicious inbound source subnets.\n"
                "4. Confirm multi-factor authentication (MFA) enforcement and rotate potentially exposed credentials."
            ),
            "rationale_template": "Spike in repeated failed logins on node '{source_id}' indicates unauthorized access attempt.",
        },
        RC_COLLECTOR_FAILURE: {
            "action": "Check collector status and network connectivity.",
            "description": (
                "1. Verify collector process status (`systemctl status sentinelops-collector` or supervisor).\n"
                "2. Check local collector logs for permission errors, outbound network blocks, or local buffer overflows.\n"
                "3. Ensure egress port to regional ingest endpoint is reachable.\n"
                "4. Restart the collector service and confirm heartbeat resumption."
            ),
            "rationale_template": "Missing heartbeat signals or offline status indicate collector agent crash or local host isolation on node '{source_id}'.",
        },
    }

    def __init__(self, root_cause_analyzer: Optional[RootCauseAnalyzer] = None):
        self.root_cause_analyzer = root_cause_analyzer or RootCauseAnalyzer()

    def _determine_priority(self, severity: str, scenario_id: str) -> str:
        """Assigns P1 (Urgent), P2 (High), or P3 (Medium) based on severity and impact."""
        if severity == SEVERITY_CRITICAL or scenario_id in [RC_COLLECTOR_FAILURE, RC_SUSPICIOUS_AUTH]:
            return "P1"
        if severity == SEVERITY_HIGH:
            return "P2"
        return "P3"

    def generate_recommendations(self, incident: Incident) -> List[Recommendation]:
        """
        Generates prioritized recommendations for an incident.
        Enriches incident.recommendations in-place and returns the list.
        """
        # Ensure root cause is diagnosed
        if not incident.root_cause_details:
            self.root_cause_analyzer.diagnose_incident(incident)

        hypothesis = incident.root_cause_details
        scenario_id = hypothesis.scenario_id if hypothesis else RC_UNSPECIFIED_ANOMALY
        source_id = incident.affected_source
        severity = incident.severity

        recommendations: List[Recommendation] = []

        # Handle Compound Scenario: Resource + Network (Demo Scenario Step 7)
        if scenario_id == RC_COMPOUND_PRESSURE:
            # 1. Resource recommendation
            rec_cpu = Recommendation(
                id=f"rec_{uuid.uuid4().hex[:8]}",
                incident_id=incident.id,
                priority="P1",
                action="Inspect resource-intensive processes and workload distribution.",
                description=(
                    "1. Identify top CPU/memory consuming processes on host.\n"
                    "2. Examine application thread pools and request concurrency.\n"
                    "3. Scale application replicas or shed background workloads."
                ),
                rationale=f"High compute and memory saturation detected on {source_id}.",
                execution_type="manual",
            )
            recommendations.append(rec_cpu)

            # 2. Network recommendation
            rec_net = Recommendation(
                id=f"rec_{uuid.uuid4().hex[:8]}",
                incident_id=incident.id,
                priority="P1",
                action="Inspect network routes, congestion and affected connections.",
                description=(
                    "1. Inspect gateway latency and switch interface packet drops.\n"
                    "2. Check network interface saturation and socket buffer sizes.\n"
                    "3. Reroute traffic to alternative network path."
                ),
                rationale=f"Severe network latency and packet loss compounding compute pressure on {source_id}.",
                execution_type="manual",
            )
            recommendations.append(rec_net)

            # 3. Workload change review
            rec_deploy = Recommendation(
                id=f"rec_{uuid.uuid4().hex[:8]}",
                incident_id=incident.id,
                priority="P2",
                action="Check recent deployment or workload changes.",
                description=(
                    "1. Correlate incident start timestamp with recent deployment pipelines.\n"
                    "2. Review configuration changes applied to {source_id} in the last hour.\n"
                    "3. Prepare rollback plan if regression is identified."
                ),
                rationale=f"Multiple compounding symptoms on {source_id} often originate from recent code release or configuration update.",
                execution_type="manual",
            )
            recommendations.append(rec_deploy)

        elif scenario_id in self.RECOMMENDATION_TEMPLATES:
            tmpl = self.RECOMMENDATION_TEMPLATES[scenario_id]
            priority = self._determine_priority(severity, scenario_id)
            rec = Recommendation(
                id=f"rec_{uuid.uuid4().hex[:8]}",
                incident_id=incident.id,
                priority=priority,
                action=tmpl["action"],
                description=tmpl["description"],
                rationale=tmpl["rationale_template"].format(source_id=source_id),
                execution_type="manual",
            )
            recommendations.append(rec)

        else:
            # Unspecified / Generic
            rec = Recommendation(
                id=f"rec_{uuid.uuid4().hex[:8]}",
                incident_id=incident.id,
                priority="P3",
                action="Inspect affected node metrics and diagnostic logs locally.",
                description=(
                    "1. Inspect local node health and metric timelines.\n"
                    "2. Review local collector status and recent operating system events.\n"
                    "3. Confirm if metric deviation is expected planned activity."
                ),
                rationale=f"Unusual metric pattern observed on {source_id}.",
                execution_type="manual",
            )
            recommendations.append(rec)

        # Update incident in-place
        incident.recommendations = recommendations
        return recommendations

    def generate_for_scenario(
        self,
        scenario_id: str,
        incident_id: str = "inc_demo",
        source_id: str = "node_demo",
        severity: str = SEVERITY_HIGH,
    ) -> List[Recommendation]:
        """
        Standalone generator for a given scenario without needing a full Incident instance.
        """
        priority = self._determine_priority(severity, scenario_id)
        if scenario_id in self.RECOMMENDATION_TEMPLATES:
            tmpl = self.RECOMMENDATION_TEMPLATES[scenario_id]
            return [
                Recommendation(
                    id=f"rec_{uuid.uuid4().hex[:8]}",
                    incident_id=incident_id,
                    priority=priority,
                    action=tmpl["action"],
                    description=tmpl["description"],
                    rationale=tmpl["rationale_template"].format(source_id=source_id),
                    execution_type="manual",
                )
            ]
        return [
            Recommendation(
                id=f"rec_{uuid.uuid4().hex[:8]}",
                incident_id=incident_id,
                priority=priority,
                action="Inspect affected node metrics and diagnostic logs locally.",
                description="Review local telemetry and recent server activities.",
                rationale=f"Operational anomaly on {source_id}.",
                execution_type="manual",
            )
        ]
