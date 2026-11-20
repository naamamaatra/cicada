"""
SentinelOps AI - Shared Constants & Configurations.
Reference thresholds, health states, default infrastructure nodes, and allow-lists.
Agreed across Member 1 (Collector), Member 2 (AI), Member 3 (Dashboard), and Member 4 (Backend).
"""

# Thresholds for Health Evaluation (Section 14 of Project Plan)
THRESHOLDS = {
    "cpu": {
        "excellent_max": 50.0,
        "good_max": 70.0,
        "fair_max": 90.0,
        "critical": 90.0,
        "warning": 75.0,
    },
    "memory": {
        "excellent_max": 60.0,
        "good_max": 75.0,
        "fair_max": 90.0,
        "critical": 90.0,
        "warning": 75.0,
    },
    "disk": {
        "excellent_max": 70.0,
        "good_max": 85.0,
        "fair_max": 95.0,
        "critical": 90.0,
        "warning": 75.0,
    },
    "latency_ms": {
        "excellent_max": 50.0,
        "good_max": 100.0,
        "fair_max": 250.0,
        "critical": 250.0,
        "warning": 150.0,
    },
    "packet_loss_pct": {
        "excellent_max": 0.0,
        "good_max": 1.0,
        "fair_max": 5.0,
        "critical": 5.0,
        "warning": 2.0,
    },
    "failed_logins": {
        "critical": 5,
    },
    "error_count": {
        "critical": 20,
    },
}

# The 4 Product Health States
HEALTH_STATES = ["EXCELLENT", "GOOD", "FAIR", "POOR"]

# Default 3 Monitored Simulated Servers (Phase 1 Baseline)
DEFAULT_SERVERS = [
    {
        "source_id": "node_a81f",
        "role": "App Server (Production-Web)",
        "region": "us-east-1",
        "real_hostname": "prod-app-srv-01.internal.corp",
        "base_ip": "10.240.10.15",
    },
    {
        "source_id": "node_b92c",
        "role": "Database Master (Postgres)",
        "region": "us-east-1",
        "real_hostname": "prod-db-master-01.internal.corp",
        "base_ip": "10.240.10.20",
    },
    {
        "source_id": "node_c73d",
        "role": "API Ingress & Gateway",
        "region": "us-east-1",
        "real_hostname": "prod-ingress-gw-01.internal.corp",
        "base_ip": "10.240.10.30",
    },
]

# Strict Allow-List of Transmittable Telemetry Fields (Section 7 & 10)
ALLOWED_TELEMETRY_FIELDS = {
    "payload_id",
    "tenant_id",
    "source_id",
    "timestamp_utc",
    "cpu",
    "memory",
    "disk",
    "latency_ms",
    "packet_loss_pct",
    "error_count",
    "failed_logins",
    "collector_status",
    "event_category",
}
