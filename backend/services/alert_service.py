"""
SentinelOps AI - Basic Alert Engine & Health Service for Phase 1.
Implements deterministic threshold-based alerting and health scoring.
Kept decoupled so Member 2 (AI Engine) can extend or plug in during Phase 3.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict
from backend.schemas import TelemetryPayload, Alert, MetricsSummary
from backend.storage import InMemoryStorage


# Configurable Phase 1 Thresholds
THRESHOLDS = {
    "cpu_critical": 90.0,
    "cpu_warning": 75.0,
    "memory_critical": 90.0,
    "memory_warning": 75.0,
    "disk_critical": 90.0,
    "disk_warning": 75.0,
    "latency_critical_ms": 250.0,
    "latency_warning_ms": 150.0,
    "packet_loss_critical_pct": 5.0,
    "packet_loss_warning_pct": 2.0,
    "failed_logins_spike": 5,
    "error_count_spike": 20,
}


def evaluate_telemetry_alerts(payload: TelemetryPayload) -> List[Alert]:
    """
    Evaluate incoming telemetry against Phase 1 threshold rules.
    Returns a list of triggered Alert objects.
    """
    alerts: List[Alert] = []
    now = datetime.now(timezone.utc)

    # 1. CPU Threshold
    if payload.cpu > THRESHOLDS["cpu_critical"]:
        alerts.append(
            Alert(
                alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                payload_id=payload.payload_id,
                source_id=payload.source_id,
                alert_type="HIGH_CPU",
                severity="CRITICAL",
                message=f"CPU utilization at {payload.cpu:.1f}% exceeds threshold of {THRESHOLDS['cpu_critical']}%",
                metric_value=payload.cpu,
                threshold=THRESHOLDS["cpu_critical"],
                timestamp_utc=now,
            )
        )

    # 2. Memory Threshold
    if payload.memory > THRESHOLDS["memory_critical"]:
        alerts.append(
            Alert(
                alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                payload_id=payload.payload_id,
                source_id=payload.source_id,
                alert_type="HIGH_MEMORY",
                severity="CRITICAL",
                message=f"Memory utilization at {payload.memory:.1f}% exceeds threshold of {THRESHOLDS['memory_critical']}%",
                metric_value=payload.memory,
                threshold=THRESHOLDS["memory_critical"],
                timestamp_utc=now,
            )
        )

    # 3. Disk Threshold
    if payload.disk > THRESHOLDS["disk_critical"]:
        alerts.append(
            Alert(
                alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                payload_id=payload.payload_id,
                source_id=payload.source_id,
                alert_type="HIGH_DISK",
                severity="CRITICAL",
                message=f"Disk utilization at {payload.disk:.1f}% exceeds threshold of {THRESHOLDS['disk_critical']}%",
                metric_value=payload.disk,
                threshold=THRESHOLDS["disk_critical"],
                timestamp_utc=now,
            )
        )

    # 4. Latency Threshold
    if payload.latency_ms > THRESHOLDS["latency_critical_ms"]:
        alerts.append(
            Alert(
                alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                payload_id=payload.payload_id,
                source_id=payload.source_id,
                alert_type="HIGH_LATENCY",
                severity="CRITICAL",
                message=f"Network latency at {payload.latency_ms:.1f}ms exceeds threshold of {THRESHOLDS['latency_critical_ms']}ms",
                metric_value=payload.latency_ms,
                threshold=THRESHOLDS["latency_critical_ms"],
                timestamp_utc=now,
            )
        )

    # 5. Packet Loss Threshold
    if payload.packet_loss_pct > THRESHOLDS["packet_loss_critical_pct"]:
        alerts.append(
            Alert(
                alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                payload_id=payload.payload_id,
                source_id=payload.source_id,
                alert_type="HIGH_PACKET_LOSS",
                severity="CRITICAL",
                message=f"Packet loss at {payload.packet_loss_pct:.1f}% exceeds threshold of {THRESHOLDS['packet_loss_critical_pct']}%",
                metric_value=payload.packet_loss_pct,
                threshold=THRESHOLDS["packet_loss_critical_pct"],
                timestamp_utc=now,
            )
        )

    # 6. Failed Logins Security Spike
    if payload.failed_logins >= THRESHOLDS["failed_logins_spike"]:
        alerts.append(
            Alert(
                alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                payload_id=payload.payload_id,
                source_id=payload.source_id,
                alert_type="SECURITY_FAILED_LOGINS",
                severity="CRITICAL",
                message=f"Security alert: {payload.failed_logins} failed logins detected (threshold >= {THRESHOLDS['failed_logins_spike']})",
                metric_value=float(payload.failed_logins),
                threshold=float(THRESHOLDS["failed_logins_spike"]),
                timestamp_utc=now,
            )
        )

    # 7. Error Count Spike
    if payload.error_count >= THRESHOLDS["error_count_spike"]:
        alerts.append(
            Alert(
                alert_id=f"alt_{uuid.uuid4().hex[:8]}",
                payload_id=payload.payload_id,
                source_id=payload.source_id,
                alert_type="HIGH_ERROR_COUNT",
                severity="CRITICAL",
                message=f"Application error count at {payload.error_count} exceeds threshold >= {THRESHOLDS['error_count_spike']}",
                metric_value=float(payload.error_count),
                threshold=float(THRESHOLDS["error_count_spike"]),
                timestamp_utc=now,
            )
        )

    return alerts


def classify_four_state_health(payload: TelemetryPayload) -> str:
    """
    Hackathon Section 4 Four-State Health Classification:
    - POOR: critical degradation, severe breach (CPU>90, MEM>90, DISK>95, LAT>250, LOSS>5, failed logins>=5, errors>=20)
    - FAIR: elevated metrics / warnings (CPU>70, MEM>75, DISK>85, LAT>100, LOSS>1)
    - GOOD: normal operational deviations (CPU>50, MEM>60, DISK>70, LAT>50)
    - EXCELLENT: healthy baselines
    """
    # Check POOR (Critical) conditions
    if (
        payload.cpu > THRESHOLDS["cpu_critical"]
        or payload.memory > THRESHOLDS["memory_critical"]
        or payload.disk > 95.0
        or payload.latency_ms > THRESHOLDS["latency_critical_ms"]
        or payload.packet_loss_pct > THRESHOLDS["packet_loss_critical_pct"]
        or payload.failed_logins >= THRESHOLDS["failed_logins_spike"]
        or payload.error_count >= THRESHOLDS["error_count_spike"]
    ):
        return "POOR"

    # Check FAIR (Warning) conditions
    if (
        payload.cpu > 70.0
        or payload.memory > 75.0
        or payload.disk > 85.0
        or payload.latency_ms > 100.0
        or payload.packet_loss_pct > 1.0
    ):
        return "FAIR"

    # Check GOOD conditions
    if (
        payload.cpu > 50.0
        or payload.memory > 60.0
        or payload.disk > 70.0
        or payload.latency_ms > 50.0
    ):
        return "GOOD"

    return "EXCELLENT"


def classify_health(payload: TelemetryPayload) -> str:
    """
    Classify the health state of a node based on its telemetry:
    - CRITICAL
    - WARNING
    - HEALTHY
    """
    # Check CRITICAL conditions first
    if (
        payload.cpu > THRESHOLDS["cpu_critical"]
        or payload.memory > THRESHOLDS["memory_critical"]
        or payload.disk > THRESHOLDS["disk_critical"]
        or payload.latency_ms > THRESHOLDS["latency_critical_ms"]
        or payload.packet_loss_pct > THRESHOLDS["packet_loss_critical_pct"]
        or payload.failed_logins >= THRESHOLDS["failed_logins_spike"]
        or payload.error_count >= THRESHOLDS["error_count_spike"]
    ):
        return "CRITICAL"

    # Check WARNING conditions
    if (
        payload.cpu > THRESHOLDS["cpu_warning"]
        or payload.memory > THRESHOLDS["memory_warning"]
        or payload.disk > THRESHOLDS["disk_warning"]
        or payload.latency_ms > THRESHOLDS["latency_warning_ms"]
        or payload.packet_loss_pct > THRESHOLDS["packet_loss_warning_pct"]
    ):
        return "WARNING"

    return "HEALTHY"


def calculate_metrics_summary(storage: InMemoryStorage) -> MetricsSummary:
    """
    Calculate high-level health and metric counters across all monitored sources.
    Includes both 3-state operational summary and Section 4 four-state breakdown.
    """
    latest_per_source = storage.get_latest_per_source()
    total_sources = len(latest_per_source)
    total_events = storage.total_telemetry_count()
    active_alerts = storage.total_alerts_count()

    healthy_count = 0
    warning_count = 0
    critical_count = 0

    four_state_counts = {"EXCELLENT": 0, "GOOD": 0, "FAIR": 0, "POOR": 0}

    for source_id, payload in latest_per_source.items():
        state = classify_health(payload)
        if state == "CRITICAL":
            critical_count += 1
        elif state == "WARNING":
            warning_count += 1
        else:
            healthy_count += 1

        four_state = classify_four_state_health(payload)
        four_state_counts[four_state] = four_state_counts.get(four_state, 0) + 1

    return MetricsSummary(
        total_sources=total_sources,
        total_telemetry_events=total_events,
        healthy_sources=healthy_count,
        warning_sources=warning_count,
        critical_sources=critical_count,
        active_alert_count=active_alerts,
        four_state_breakdown=four_state_counts,
    )

