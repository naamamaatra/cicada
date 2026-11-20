"""
SentinelOps AI - AI & Incident Intelligence Engine (Member 2 Package)

Provides complete end-to-end AI intelligence:
- AnomalyDetector: Static thresholds (Layer 1), Statistical Z-scores (Layer 2), Isolation Forest (Layer 3)
- AlertCorrelator: Temporal, spatial, and semantic incident correlation & deduplication
- RootCauseAnalyzer: Six canonical root-cause inference scenarios with explainability
- RecommendationEngine: Actionable, prioritized, manual-assisted operational recommendations
- IncidentIntelligencePipeline: Full end-to-end pipeline orchestrator for FastAPI backend & Streamlit dashboard
"""

from typing import List, Dict, Any, Optional, Union, Tuple

from shared.models import TelemetryPayload, Alert, Incident, RootCauseHypothesis, Recommendation
from ai.anomaly import AnomalyDetector
from ai.correlation import AlertCorrelator
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
from ai.recommendations import RecommendationEngine


class IncidentIntelligencePipeline:
    """
    Unified end-to-end AI intelligence pipeline orchestrator.
    Seamlessly integrates:
    Sanitized Telemetry -> Anomaly Detection -> Alert Correlation -> Root Cause -> Recommendations
    """

    def __init__(
        self,
        anomaly_detector: Optional[AnomalyDetector] = None,
        correlator: Optional[AlertCorrelator] = None,
        root_cause_analyzer: Optional[RootCauseAnalyzer] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
    ):
        self.detector = anomaly_detector or AnomalyDetector()
        self.correlator = correlator or AlertCorrelator()
        self.analyzer = root_cause_analyzer or RootCauseAnalyzer()
        self.recommendations = recommendation_engine or RecommendationEngine(root_cause_analyzer=self.analyzer)

    def process_telemetry(
        self, payload_input: Union[Dict[str, Any], TelemetryPayload]
    ) -> Tuple[List[Alert], List[Incident]]:
        """
        Executes full intelligence lifecycle on an incoming telemetry payload:
        1. Detects anomalies across all 3 layers.
        2. Correlates detected alerts into incidents (or deduplicates into active incidents).
        3. Diagnoses probable root causes for affected incidents.
        4. Synthesizes prioritized, actionable recommendations.
        5. Returns (alerts_generated, active_or_updated_incidents).
        """
        alerts = self.detector.process_telemetry(payload_input)
        if not alerts:
            return [], []

        incidents = self.correlator.correlate_alerts(alerts)

        for incident in incidents:
            self.analyzer.diagnose_incident(incident)
            self.recommendations.generate_recommendations(incident)

        return alerts, incidents

    def handle_recovery(self, source_id: str, tenant_id: str, is_healthy: bool) -> List[Incident]:
        """
        Signals health recovery to auto-resolve open incidents.
        """
        return self.correlator.check_recovery(source_id=source_id, tenant_id=tenant_id, is_healthy=is_healthy)

    def get_active_incidents(self, tenant_id: Optional[str] = None) -> List[Incident]:
        """Returns all open or investigating incidents."""
        return self.correlator.get_active_incidents(tenant_id=tenant_id)


__all__ = [
    "AnomalyDetector",
    "AlertCorrelator",
    "RootCauseAnalyzer",
    "RecommendationEngine",
    "IncidentIntelligencePipeline",
    "RC_WORKLOAD_OVERLOAD",
    "RC_MEMORY_LEAK",
    "RC_NETWORK_DEGRADATION",
    "RC_DATABASE_BOTTLENECK",
    "RC_SUSPICIOUS_AUTH",
    "RC_COLLECTOR_FAILURE",
    "RC_COMPOUND_PRESSURE",
    "RC_UNSPECIFIED_ANOMALY",
]
