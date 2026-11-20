"""
Shared constants and threshold configurations for SentinelOps AI.
"""

# Thresholds for Health Evaluation (Section 14 of Project Plan)
THRESHOLDS = {
    "cpu": {
        "excellent_max": 50.0,
        "good_max": 70.0,
        "fair_max": 90.0
    },
    "memory": {
        "excellent_max": 60.0,
        "good_max": 75.0,
        "fair_max": 90.0
    },
    "latency_ms": {
        "excellent_max": 50.0,
        "good_max": 100.0,
        "fair_max": 250.0
    },
    "packet_loss_pct": {
        "excellent_max": 0.0,
        "good_max": 1.0,
        "fair_max": 5.0
    },
    "disk": {
        "excellent_max": 70.0,
        "good_max": 85.0,
        "fair_max": 95.0
    }
}

# The 4 Product Health States
HEALTH_STATES = ["EXCELLENT", "GOOD", "FAIR", "POOR"]

# Default simulated servers
DEFAULT_SERVERS = [
    {"source_id": "node_a81f", "role": "App Server (Production-Web)", "region": "us-east-1"},
    {"source_id": "node_b92c", "role": "Database Master (Postgres)", "region": "us-east-1"},
    {"source_id": "node_c73d", "role": "API Ingress & Gateway", "region": "us-east-1"},
]
