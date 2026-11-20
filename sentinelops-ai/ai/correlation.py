"""
SentinelOps AI - Alert Correlation Engine (correlation.py)
Groups related alerts into consolidated incidents based on:
- Same source ID (node/host)
- Time proximity (configurable window, e.g. 300s)
- Metric relationships and symptom clustering
- Multi-tenant boundary preservation
"""

from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timezone
import uuid

from shared.models import Alert, Incident
from shared.constants import (
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    INCIDENT_STATUS_OPEN,
    INCIDENT_STATUS_INVESTIGATING,
    INCIDENT_STATUS_RESOLVED,
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
)

SEVERITY_RANKS = {
    SEVERITY_LOW: 1,
    SEVERITY_MEDIUM: 2,
    SEVERITY_HIGH: 3,
    SEVERITY_CRITICAL: 4,
}


def _parse_iso(ts_str: str) -> datetime:
    """Parse ISO timestamp with fallback to current UTC."""
    try:
        # Replace 'Z' with UTC offset if needed
        clean_ts = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_ts)
    except Exception:
        return datetime.now(timezone.utc)


class AlertCorrelator:
    """
    Intelligent event correlation engine.
    Deduplicates and merges alerts into actionable incidents.
    """

    # Functional alert clusters
    CLUSTER_RESOURCE = {
        ALERT_CPU_SPIKE,
        ALERT_MEMORY_SPIKE,
        ALERT_DISK_SPIKE,
        ALERT_ERROR_BURST,
        ALERT_MULTIVARIATE_ANOMALY,
    }
    CLUSTER_NETWORK = {
        ALERT_LATENCY_SPIKE,
        ALERT_PACKET_LOSS_SPIKE,
    }
    CLUSTER_SECURITY = {
        ALERT_FAILED_LOGINS_SPIKE,
    }
    CLUSTER_AVAILABILITY = {
        ALERT_COLLECTOR_OFFLINE,
    }
    CLUSTER_DATABASE = {
        ALERT_DB_TIMEOUT,
    }

    def __init__(self, time_window_seconds: int = 300):
        self.time_window_seconds = time_window_seconds
        # Active incidents stored as incident_id -> Incident
        self._incidents: Dict[str, Incident] = {}

    def _get_cluster_name(self, alert_type: str) -> str:
        if alert_type in self.CLUSTER_RESOURCE:
            return "resource"
        if alert_type in self.CLUSTER_NETWORK:
            return "network"
        if alert_type in self.CLUSTER_SECURITY:
            return "security"
        if alert_type in self.CLUSTER_AVAILABILITY:
            return "availability"
        if alert_type in self.CLUSTER_DATABASE:
            return "database"
        return "general"

    def _generate_title(self, cluster: str, source_id: str, alert_types: Set[str]) -> str:
        if cluster == "resource":
            if ALERT_CPU_SPIKE in alert_types and ALERT_ERROR_BURST in alert_types:
                return f"Severe Resource Contention & Error Surge on {source_id}"
            if ALERT_CPU_SPIKE in alert_types and ALERT_MEMORY_SPIKE in alert_types:
                return f"System Resource Saturation (CPU + Memory) on {source_id}"
            return f"Resource Pressure Detected on {source_id}"
        elif cluster == "network":
            return f"Network Latency & Connectivity Degradation on {source_id}"
        elif cluster == "security":
            return f"Authentication Storm / Brute-Force Activity on {source_id}"
        elif cluster == "availability":
            return f"Collector Node Unreachable / Outage on {source_id}"
        elif cluster == "database":
            return f"Database Query Timeout & Latency on {source_id}"
        return f"Operational Incident on {source_id}"

    def correlate_alert(self, alert: Alert) -> Incident:
        """
        Correlates a single alert against existing open incidents, or spawns a new incident.
        """
        alert_cluster = self._get_cluster_name(alert.alert_type)
        alert_time = _parse_iso(alert.timestamp)

        # Look for matching active incident for the same (tenant_id, source_id)
        candidate: Optional[Incident] = None
        for inc in self._incidents.values():
            if inc.status != INCIDENT_STATUS_OPEN:
                continue
            if inc.tenant_id != alert.tenant_id or inc.affected_source != alert.source_id:
                continue

            # Check time window proximity
            inc_updated = _parse_iso(inc.updated_at)
            time_diff = abs((alert_time - inc_updated).total_seconds())
            if time_diff > self.time_window_seconds:
                continue

            # Check cluster compatibility
            inc_alert_types = {a.alert_type for a in inc.alerts}
            inc_clusters = {self._get_cluster_name(at) for at in inc_alert_types}

            # Merge if same cluster, or if resource + network compound incident
            if (alert_cluster in inc_clusters) or (
                alert_cluster in ["resource", "network"] and any(c in ["resource", "network"] for c in inc_clusters)
            ):
                candidate = inc
                break

        now_iso = alert_time.isoformat()

        if candidate is not None:
            # Check for duplicate alert prevention
            duplicate = any(
                a.id == alert.id
                or (a.alert_type == alert.alert_type and a.metric_value == alert.metric_value and a.payload_id == alert.payload_id)
                for a in candidate.alerts
            )
            if not duplicate:
                candidate.alerts.append(alert)
                candidate.alert_ids.append(alert.id)
                if alert.evidence not in candidate.evidence_summary:
                    candidate.evidence_summary.append(alert.evidence)

                # Escalate severity if incoming alert is more severe
                if SEVERITY_RANKS.get(alert.severity, 1) > SEVERITY_RANKS.get(candidate.severity, 1):
                    candidate.severity = alert.severity

                candidate.updated_at = now_iso
                # Update title to reflect multi-symptom scope
                all_types = {a.alert_type for a in candidate.alerts}
                candidate.title = self._generate_title(alert_cluster, candidate.affected_source, all_types)

            return candidate

        # No existing candidate found -> create new Incident
        new_id = f"inc_{uuid.uuid4().hex[:8]}"
        all_types = {alert.alert_type}
        title = self._generate_title(alert_cluster, alert.source_id, all_types)

        new_incident = Incident(
            id=new_id,
            title=title,
            severity=alert.severity,
            affected_source=alert.source_id,
            tenant_id=alert.tenant_id,
            alert_ids=[alert.id],
            alerts=[alert],
            evidence_summary=[alert.evidence],
            status=INCIDENT_STATUS_OPEN,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self._incidents[new_id] = new_incident
        return new_incident

    def correlate_alerts(self, alerts: List[Alert]) -> List[Incident]:
        """
        Batch correlate a list of alerts.
        """
        affected_incidents: Dict[str, Incident] = {}
        for alert in alerts:
            inc = self.correlate_alert(alert)
            affected_incidents[inc.id] = inc
        return list(affected_incidents.values())

    def get_active_incidents(self, tenant_id: Optional[str] = None) -> List[Incident]:
        """Returns all open/active incidents, optionally filtered by tenant."""
        results = [
            inc for inc in self._incidents.values()
            if inc.status in [INCIDENT_STATUS_OPEN, INCIDENT_STATUS_INVESTIGATING]
        ]
        if tenant_id:
            results = [inc for inc in results if inc.tenant_id == tenant_id]
        return results

    def resolve_incident(self, incident_id: str) -> Optional[Incident]:
        """Manually or automatically mark an incident as RESOLVED."""
        if incident_id in self._incidents:
            self._incidents[incident_id].status = INCIDENT_STATUS_RESOLVED
            self._incidents[incident_id].updated_at = datetime.now(timezone.utc).isoformat()
            return self._incidents[incident_id]
        return None

    def check_recovery(self, source_id: str, tenant_id: str, is_healthy: bool) -> List[Incident]:
        """
        Auto-recovery: When a node's telemetry returns to EXCELLENT/GOOD state,
        transition any active open incidents on that node to RESOLVED.
        """
        resolved_list: List[Incident] = []
        if not is_healthy:
            return resolved_list

        for inc in self.get_active_incidents(tenant_id=tenant_id):
            if inc.affected_source == source_id:
                inc.status = INCIDENT_STATUS_RESOLVED
                inc.updated_at = datetime.now(timezone.utc).isoformat()
                resolved_list.append(inc)
        return resolved_list

    def clear(self) -> None:
        """Clear all registered incidents (for testing or reset)."""
        self._incidents.clear()
