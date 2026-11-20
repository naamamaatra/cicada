"""
Telemetry Data Service for SentinelOps AI Dashboard.
Supports live simulation, scenario injection (Phase 1 demo flow), and FastAPI backend polling.
"""
import random
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests

from shared.models import TelemetryPayload, BasicAlert
from shared.constants import DEFAULT_SERVERS
from dashboard.components.cards import calculate_overall_health, evaluate_metric_health


class TelemetryDataService:
    def __init__(self, backend_url: str = "http://127.0.0.1:8000"):
        self.backend_url = backend_url
        self.active_scenario = "normal"
        self.history = []  # sliding window of telemetry records
        self.alerts = []
        self._init_mock_history()

    def _init_mock_history(self):
        """Populates initial 20 points of healthy history for the 3 servers."""
        base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        for i in range(20):
            ts = (base_time + timedelta(seconds=i * 30)).isoformat()
            for s in DEFAULT_SERVERS:
                item = self._generate_healthy_point(s["source_id"], ts)
                self.history.append(item)

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
        """
        Switches current simulation scenario:
        - 'normal': All 3 servers healthy
        - 'spike_node_a': Severe CPU & RAM spike on node_a81f
        - 'network_degrade_node_c': High latency and packet loss on node_c73d
        - 'db_overload_node_b': DB overload and disk pressure on node_b92c
        """
        self.active_scenario = scenario_name

    def fetch_latest_metrics(self) -> tuple[dict[str, dict], list[dict]]:
        """
        Fetches or simulates the latest metrics for all servers.
        Returns (latest_by_node, active_alerts)
        """
        # Try fetching from FastAPI backend first
        try:
            resp = requests.get(f"{self.backend_url}/api/v1/metrics", timeout=0.8)
            if resp.status_code == 200:
                remote_data = resp.json()
                if remote_data and isinstance(remote_data, list):
                    # Backend reachable and returning data
                    latest_by_node = {}
                    for item in remote_data:
                        latest_by_node[item["source_id"]] = item
                        self.history.append(item)
                    self._check_alerts(latest_by_node)
                    return latest_by_node, self.alerts
        except Exception:
            # Backend not reachable yet; fall back smoothly to simulated generator
            pass

        # Generate tick data based on active scenario
        latest_by_node = {}
        now_ts = datetime.now(timezone.utc).isoformat()

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

            latest_by_node[src] = item
            self.history.append(item)

        # Keep history capped at 120 items
        if len(self.history) > 120:
            self.history = self.history[-120:]

        self._check_alerts(latest_by_node)
        return latest_by_node, self.alerts

    def _check_alerts(self, latest_by_node: dict[str, dict]):
        """Evaluates thresholds to generate basic alerts for Phase 1."""
        new_alerts = []
        for src, data in latest_by_node.items():
            # CPU check
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

            # Memory check
            if data["memory"] > 90.0:
                new_alerts.append({
                    "alert_id": f"alt_mem_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "Memory Utilization",
                    "value": f"{data['memory']}%",
                    "severity": "CRITICAL",
                    "message": f"Memory exhaustion risk ({data['memory']}%) exceeding 90% threshold"
                })

            # Latency check
            if data["latency_ms"] > 250.0:
                new_alerts.append({
                    "alert_id": f"alt_lat_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "Network Latency",
                    "value": f"{data['latency_ms']} ms",
                    "severity": "CRITICAL",
                    "message": f"High response latency ({data['latency_ms']} ms) exceeding 250ms threshold"
                })

            # Packet loss check
            if data["packet_loss_pct"] > 5.0:
                new_alerts.append({
                    "alert_id": f"alt_pkt_{src}_{int(time.time())}",
                    "source_id": src,
                    "metric": "Packet Loss",
                    "value": f"{data['packet_loss_pct']}%",
                    "severity": "CRITICAL",
                    "message": f"Severe packet loss ({data['packet_loss_pct']}%) exceeding 5% threshold"
                })

            # Failed logins check
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

