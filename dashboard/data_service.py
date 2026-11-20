"""
Telemetry & Privacy Data Service for SentinelOps AI Dashboard (Phase 1 & Phase 2).
Synchronized with Member 1's Collector & Privacy Engine and Member 4's FastAPI Backend:
- Handles Multi-Server Infrastructure Monitoring (Phase 1)
- Drives Privacy Redaction & Egress Audit Testing (Phase 2)
- Integrates with LocalCollector and REST APIs
"""
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
import requests

from shared.models import TelemetryPayload, BasicAlert
from shared.constants import DEFAULT_SERVERS
from dashboard.components.cards import calculate_overall_health, evaluate_metric_health
from collector.collector import LocalCollector
from collector.egress_audit import EgressAuditLogger, EgressAuditRecord


class TelemetryDataService:
    def __init__(self, backend_url: str = "http://127.0.0.1:8000"):
        self.backend_url = backend_url
        self.active_scenario = "normal"
        self.history: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.backend_connected = False

        # Phase 2 Collector & Privacy Engine instance
        self.collector = LocalCollector(api_url=f"{self.backend_url}/api/v1/telemetry")
        self.last_privacy_demo_result: Dict[str, Any] = {}

        self._init_mock_history()
        # Seed an initial privacy demo record so Phase 2 tab immediately shows proof
        self._init_privacy_baseline()

    def _init_mock_history(self):
        """Populates initial 20 points of healthy history for the 3 servers."""
        base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        for i in range(20):
            ts = (base_time + timedelta(seconds=i * 30)).isoformat()
            for s in DEFAULT_SERVERS:
                item = self._generate_healthy_point(s["source_id"], ts)
                self.history.append(item)

    def _init_privacy_baseline(self):
        """Runs an initial privacy redaction demo to prime the audit state."""
        try:
            self.last_privacy_demo_result = self.collector.run_privacy_demo()
        except Exception:
            pass

    def _generate_healthy_point(self, source_id: str, ts: str = None) -> dict:
        if ts is None:
            ts = datetime.now(timezone.utc).isoformat()
        return {
            "payload_id": f"evt_{random.randint(10000, 99999)}",
            "tenant_id": "tenant_demo",
            "source_id": source_id,
            "timestamp_utc": ts,
            "cpu": round(random.uniform(22.0, 42.0), 1),
            "memory": round(random.uniform(38.0, 55.0), 1),
            "disk": round(random.uniform(45.0, 62.0), 1),
            "latency_ms": round(random.uniform(18.0, 42.0), 1),
            "packet_loss_pct": 0.0 if random.random() > 0.1 else 0.1,
            "error_count": random.choice([0, 0, 0, 1]),
            "failed_logins": 0,
            "collector_status": "online",
            "event_category": "normal_telemetry"
        }

    def set_scenario(self, scenario_name: str):
        """Switches current simulation scenario for Phase 1 demo."""
        self.active_scenario = scenario_name

    def _generate_current_payloads(self) -> dict[str, dict]:
        """Generates current telemetry for all servers based on active scenario."""
        now_ts = datetime.now(timezone.utc).isoformat()
        current = {}

        for s in DEFAULT_SERVERS:
            src = s["source_id"]
            if self.active_scenario == "spike_node_a" and src == "node_a81f":
                item = {
                    "payload_id": f"evt_{random.randint(10000, 99999)}",
                    "tenant_id": "tenant_demo",
                    "source_id": src,
                    "timestamp_utc": now_ts,
                    "cpu": round(random.uniform(94.0, 99.2), 1),
                    "memory": round(random.uniform(91.0, 96.5), 1),
                    "disk": 68.0,
                    "latency_ms": round(random.uniform(320.0, 480.0), 1),
                    "packet_loss_pct": round(random.uniform(4.0, 8.5), 1),
                    "error_count": random.randint(18, 35),
                    "failed_logins": 2,
                    "collector_status": "online",
                    "event_category": "resource_exhaustion"
                }
            elif self.active_scenario == "network_degrade_node_c" and src == "node_c73d":
                item = {
                    "payload_id": f"evt_{random.randint(10000, 99999)}",
                    "tenant_id": "tenant_demo",
                    "source_id": src,
                    "timestamp_utc": now_ts,
                    "cpu": round(random.uniform(45.0, 60.0), 1),
                    "memory": round(random.uniform(50.0, 62.0), 1),
                    "disk": 52.0,
                    "latency_ms": round(random.uniform(750.0, 1150.0), 1),
                    "packet_loss_pct": round(random.uniform(12.0, 22.0), 1),
                    "error_count": random.randint(25, 48),
                    "failed_logins": 0,
                    "collector_status": "online",
                    "event_category": "network_degradation"
                }
            elif self.active_scenario == "db_overload_node_b" and src == "node_b92c":
                item = {
                    "payload_id": f"evt_{random.randint(10000, 99999)}",
                    "tenant_id": "tenant_demo",
                    "source_id": src,
                    "timestamp_utc": now_ts,
                    "cpu": round(random.uniform(88.0, 96.0), 1),
                    "memory": round(random.uniform(85.0, 94.0), 1),
                    "disk": round(random.uniform(94.0, 98.5), 1),
                    "latency_ms": round(random.uniform(210.0, 340.0), 1),
                    "packet_loss_pct": 1.2,
                    "error_count": random.randint(12, 28),
                    "failed_logins": random.randint(8, 20),
                    "collector_status": "online",
                    "event_category": "database_bottleneck"
                }
            else:
                item = self._generate_healthy_point(src, now_ts)

            current[src] = item

        return current

    def fetch_latest_metrics(self) -> tuple[dict[str, dict], list[dict]]:
        """
        Fetches latest metrics.
        If FastAPI Backend is reachable:
        1. Submits scenario telemetry via POST /api/v1/telemetry
        2. Retrieves stored metrics from GET /api/v1/metrics
        3. Retrieves active alerts from GET /api/v1/alerts
        """
        generated = self._generate_current_payloads()

        # Check if backend is reachable
        backend_healthy = False
        try:
            h_resp = requests.get(f"{self.backend_url}/api/v1/health", timeout=0.6)
            backend_healthy = (h_resp.status_code == 200)
        except Exception:
            backend_healthy = False

        if backend_healthy:
            self.backend_connected = True
            try:
                # 1. Forward scenario data to backend API
                for payload in generated.values():
                    requests.post(f"{self.backend_url}/api/v1/telemetry", json=payload, timeout=0.5)

                # 2. Retrieve latest metrics from backend
                m_resp = requests.get(f"{self.backend_url}/api/v1/metrics", timeout=0.6)
                if m_resp.status_code == 200:
                    body = m_resp.json()
                    records = body.get("data", []) if isinstance(body, dict) else body
                    latest_by_node = {}
                    for rec in records:
                        latest_by_node[rec["source_id"]] = rec
                        self.history.append(rec)

                    # 3. Retrieve backend-generated alerts
                    a_resp = requests.get(f"{self.backend_url}/api/v1/alerts", timeout=0.6)
                    if a_resp.status_code == 200:
                        a_body = a_resp.json()
                        backend_alerts = a_body.get("data", []) if isinstance(a_body, dict) else a_body
                        formatted_alerts = []
                        for ba in backend_alerts:
                            formatted_alerts.append({
                                "alert_id": ba.get("alert_id", "alt_0"),
                                "source_id": ba.get("source_id", "node"),
                                "metric": ba.get("alert_type", "METRIC"),
                                "value": f"{ba.get('metric_value', '')}",
                                "severity": ba.get("severity", "WARNING"),
                                "message": ba.get("message", "Alert triggered")
                            })
                        self.alerts = formatted_alerts

                    self._trim_history()
                    return latest_by_node, self.alerts
            except Exception:
                pass

        # Standalone Engine Fallback Mode
        self.backend_connected = False
        latest_by_node = generated
        for item in generated.values():
            self.history.append(item)
        self._check_alerts(latest_by_node)
        self._trim_history()
        return latest_by_node, self.alerts

    # --- PHASE 2: PRIVACY & EGRESS AUDIT METHODS ---

    def run_privacy_test(self, scenario: str = "cpu_spike") -> Dict[str, Any]:
        """
        Executes a real-time Privacy Engine & Allow-List Policy test:
        1. Generates a raw un-redacted event containing passwords, API keys, and real internal hostnames.
        2. Pipes it through the PrivacyEngine and AllowListPolicy.
        3. Captures the safe payload and logs an EgressAuditRecord.
        """
        raw_event = self.collector.generator.generate_raw_event_with_secrets(
            server_index=random.choice([0, 1, 2]),
            scenario=scenario
        )
        res = self.collector.process_and_send(raw_event)
        latest_audit = self.collector.audit_logger.get_latest()

        self.last_privacy_demo_result = {
            "original_raw_event": raw_event,
            "pipeline_result": res,
            "egress_audit_proof": latest_audit.model_dump() if latest_audit else None,
        }
        return self.last_privacy_demo_result

    def get_egress_audit_records(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Returns recent egress audit records for the Phase 2 audit trail table."""
        records = self.collector.audit_logger.get_all(limit=limit)
        return [r.model_dump() for r in records]

    def _trim_history(self):
        if len(self.history) > 120:
            self.history = self.history[-120:]

    def _check_alerts(self, latest_by_node: dict[str, dict]):
        """Local threshold alert evaluator for fallback mode."""
        new_alerts = []
        for src, data in latest_by_node.items():
            if data["cpu"] > 90.0:
                new_alerts.append({
                    "alert_id": f"alt_cpu_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "CPU Utilization",
                    "value": f"{data['cpu']}%",
                    "severity": "CRITICAL",
                    "message": f"Critical CPU saturation ({data['cpu']}%) exceeding 90% threshold"
                })
            elif data["cpu"] > 70.0:
                new_alerts.append({
                    "alert_id": f"alt_cpu_w_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "CPU Utilization",
                    "value": f"{data['cpu']}%",
                    "severity": "WARNING",
                    "message": f"Elevated CPU usage ({data['cpu']}%)"
                })

            if data["memory"] > 90.0:
                new_alerts.append({
                    "alert_id": f"alt_mem_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "Memory Utilization",
                    "value": f"{data['memory']}%",
                    "severity": "CRITICAL",
                    "message": f"Memory exhaustion risk ({data['memory']}%) exceeding 90% threshold"
                })

            if data["latency_ms"] > 250.0:
                new_alerts.append({
                    "alert_id": f"alt_lat_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "Network Latency",
                    "value": f"{data['latency_ms']} ms",
                    "severity": "CRITICAL",
                    "message": f"High response latency ({data['latency_ms']} ms) exceeding 250ms threshold"
                })

            if data["packet_loss_pct"] > 5.0:
                new_alerts.append({
                    "alert_id": f"alt_pkt_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "Packet Loss",
                    "value": f"{data['packet_loss_pct']}%",
                    "severity": "CRITICAL",
                    "message": f"Severe packet loss ({data['packet_loss_pct']}%) exceeding 5% threshold"
                })

            if data.get("failed_logins", 0) >= 5:
                new_alerts.append({
                    "alert_id": f"alt_sec_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "Failed Authentication",
                    "value": f"{data['failed_logins']} attempts",
                    "severity": "CRITICAL",
                    "message": f"Potential brute-force attack detected ({data['failed_logins']} failed logins)"
                })

        self.alerts = new_alerts

    def get_history_df(self) -> pd.DataFrame:
        if not self.history:
            return pd.DataFrame()
        return pd.DataFrame(self.history)
