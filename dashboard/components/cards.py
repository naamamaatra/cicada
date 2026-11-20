"""
Health calculation and status helpers for SentinelOps AI.
"""

def evaluate_metric_health(value: float, metric_type: str) -> str:
    """
    Evaluates individual metric according to hackathon thresholds.
    Returns: 'EXCELLENT', 'GOOD', 'FAIR', or 'POOR'
    """
    if metric_type == "cpu":
        if value <= 50:
            return "EXCELLENT"
        elif value <= 70:
            return "GOOD"
        elif value <= 90:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type in ("memory", "ram"):
        if value <= 60:
            return "EXCELLENT"
        elif value <= 75:
            return "GOOD"
        elif value <= 90:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type == "latency_ms":
        if value <= 50:
            return "EXCELLENT"
        elif value <= 100:
            return "GOOD"
        elif value <= 250:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type in ("packet_loss_pct", "packet_loss"):
        if value == 0:
            return "EXCELLENT"
        elif value <= 1.0:
            return "GOOD"
        elif value <= 5.0:
            return "FAIR"
        else:
            return "POOR"

    elif metric_type == "disk":
        if value <= 70:
            return "EXCELLENT"
        elif value <= 85:
            return "GOOD"
        elif value <= 95:
            return "FAIR"
        else:
            return "POOR"

    return "GOOD"


def calculate_overall_health(node_data: dict) -> str:
    """
    Calculates overall node health by evaluating the worst-case metric.
    """
    cpu_health = evaluate_metric_health(node_data.get("cpu", 0), "cpu")
    mem_health = evaluate_metric_health(node_data.get("memory", 0), "memory")
    lat_health = evaluate_metric_health(node_data.get("latency_ms", 0), "latency_ms")
    loss_health = evaluate_metric_health(node_data.get("packet_loss_pct", 0), "packet_loss_pct")
    disk_health = evaluate_metric_health(node_data.get("disk", 0), "disk")

    hierarchy = ["POOR", "FAIR", "GOOD", "EXCELLENT"]
    for state in hierarchy:
        if state in (cpu_health, mem_health, lat_health, loss_health, disk_health):
            return state
    return "EXCELLENT"


HEALTH_COLORS = {
    "EXCELLENT": "#10B981",  # Vibrant Emerald Green
    "GOOD": "#3B82F6",       # Blue
    "FAIR": "#F59E0B",       # Amber / Orange
    "POOR": "#EF4444"        # Red
}

HEALTH_BADGES = {
    "EXCELLENT": "🟢 EXCELLENT",
    "GOOD": "🔵 GOOD",
    "FAIR": "🟡 FAIR",
    "POOR": "🔴 POOR"
}

