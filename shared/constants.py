"""
SentinelOps AI - Shared Constants & Configurations.
Reference thresholds, health states, default infrastructure nodes, and allow-lists.
Agreed across Member 1 (Collector), Member 2 (AI), Member 3 (Dashboard), and Member 4 (Backend).
"""

# Health States (Product 4-State Health Evaluation)
HEALTH_EXCELLENT = "EXCELLENT"
HEALTH_GOOD = "GOOD"
HEALTH_FAIR = "FAIR"
HEALTH_POOR = "POOR"

HEALTH_STATES = [HEALTH_EXCELLENT, HEALTH_GOOD, HEALTH_FAIR, HEALTH_POOR]

# Severity Levels
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

SEVERITY_LEVELS = [SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL]

# Static Thresholds (Layer 1 Detection)
THRESHOLD_CPU_PERCENT = 95.0
THRESHOLD_MEMORY_PERCENT = 90.0
THRESHOLD_DISK_PERCENT = 90.0
THRESHOLD_LATENCY_MS = 250.0
THRESHOLD_PACKET_LOSS_PCT = 5.0
THRESHOLD_FAILED_LOGINS = 3
THRESHOLD_ERROR_COUNT = 10

# Baseline / Health Score Thresholds (Section 14)
HEALTH_CPU_EXCELLENT = 50.0
HEALTH_CPU_GOOD = 70.0
HEALTH_CPU_FAIR = 90.0

HEALTH_RAM_EXCELLENT = 60.0
HEALTH_RAM_GOOD = 75.0
HEALTH_RAM_FAIR = 90.0

HEALTH_LATENCY_EXCELLENT = 50.0
HEALTH_LATENCY_GOOD = 100.0
HEALTH_LATENCY_FAIR = 250.0

HEALTH_PACKET_LOSS_EXCELLENT = 0.0
HEALTH_PACKET_LOSS_GOOD = 1.0
HEALTH_PACKET_LOSS_FAIR = 5.0

# Alert Types
ALERT_CPU_SPIKE = "CPU_SPIKE"
ALERT_MEMORY_SPIKE = "MEMORY_SPIKE"
ALERT_DISK_SPIKE = "DISK_SPIKE"
ALERT_LATENCY_SPIKE = "LATENCY_SPIKE"
ALERT_PACKET_LOSS_SPIKE = "PACKET_LOSS_SPIKE"
ALERT_FAILED_LOGINS_SPIKE = "FAILED_LOGINS_SPIKE"
ALERT_ERROR_BURST = "ERROR_BURST"
ALERT_MULTIVARIATE_ANOMALY = "MULTIVARIATE_ANOMALY"
ALERT_COLLECTOR_OFFLINE = "COLLECTOR_OFFLINE"
ALERT_DB_TIMEOUT = "DATABASE_TIMEOUT"

# Incident Statuses
INCIDENT_STATUS_OPEN = "OPEN"
INCIDENT_STATUS_INVESTIGATING = "INVESTIGATING"
INCIDENT_STATUS_MITIGATED = "MITIGATED"
INCIDENT_STATUS_RESOLVED = "RESOLVED"

# Root Cause Scenarios (Project Plan Section 9)
RC_WORKLOAD_OVERLOAD = "WORKLOAD_OVERLOAD"
RC_MEMORY_LEAK = "MEMORY_LEAK"
RC_NETWORK_DEGRADATION = "NETWORK_DEGRADATION"
RC_DATABASE_BOTTLENECK = "DATABASE_BOTTLENECK"
RC_SUSPICIOUS_AUTH = "SUSPICIOUS_AUTH"
RC_COLLECTOR_FAILURE = "COLLECTOR_FAILURE"

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
