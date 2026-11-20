"""
SentinelOps AI - Anomaly Detection Engine (anomaly.py)
Implements 3 detection layers:
1. Static Threshold Detection (Layer 1)
2. Statistical / Z-Score Detection (Layer 2)
3. Machine Learning - Isolation Forest Detection (Layer 3)

Designed for multi-tenant isolation, explainability, and fault tolerance.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from collections import deque
from datetime import datetime, timezone
import uuid
import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from shared.models import TelemetryPayload, Alert
from shared.constants import (
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
    THRESHOLD_CPU_PERCENT,
    THRESHOLD_MEMORY_PERCENT,
    THRESHOLD_DISK_PERCENT,
    THRESHOLD_LATENCY_MS,
    THRESHOLD_PACKET_LOSS_PCT,
    THRESHOLD_FAILED_LOGINS,
    THRESHOLD_ERROR_COUNT,
    ALERT_CPU_SPIKE,
    ALERT_MEMORY_SPIKE,
    ALERT_DISK_SPIKE,
    ALERT_LATENCY_SPIKE,
    ALERT_PACKET_LOSS_SPIKE,
    ALERT_FAILED_LOGINS_SPIKE,
    ALERT_ERROR_BURST,
    ALERT_MULTIVARIATE_ANOMALY,
    ALERT_COLLECTOR_OFFLINE,
)


class AnomalyDetector:
    """
    Multi-layered anomaly detection engine for infrastructure and security telemetry.
    """

    FEATURE_NAMES = [
        "cpu",
        "memory",
        "disk",
        "latency_ms",
        "packet_loss_pct",
        "error_count",
        "failed_logins",
    ]

    def __init__(
        self,
        history_window_size: int = 50,
        min_ml_samples: int = 15,
        z_score_threshold: float = 3.0,
        iforest_contamination: float = 0.05,
    ):
        self.history_window_size = history_window_size
        self.min_ml_samples = min_ml_samples
        self.z_score_threshold = z_score_threshold
        self.iforest_contamination = iforest_contamination

        # Sliding window history partitioned by (tenant_id, source_id)
        # Prevents any cross-tenant or cross-node contamination
        self._history: Dict[Tuple[str, str], deque] = {}

        # Optional cached fitted models per (tenant_id, source_id)
        self._models: Dict[Tuple[str, str], Any] = {}

    def _get_history(self, tenant_id: str, source_id: str) -> deque:
        key = (tenant_id, source_id)
        if key not in self._history:
            self._history[key] = deque(maxlen=self.history_window_size)
        return self._history[key]

    def _to_payload(self, raw: Union[Dict[str, Any], TelemetryPayload]) -> Optional[TelemetryPayload]:
        """Validates and coerces raw dict or TelemetryPayload."""
        if isinstance(raw, TelemetryPayload):
            return raw
        if not isinstance(raw, dict):
            return None

        try:
            # Clean and sanitize incoming numeric values
            cleaned = dict(raw)
            for num_field in ["cpu", "memory", "disk", "latency_ms", "packet_loss_pct"]:
                if num_field in cleaned and cleaned[num_field] is not None:
                    try:
                        cleaned[num_field] = float(cleaned[num_field])
                    except (ValueError, TypeError):
                        cleaned[num_field] = 0.0

            for int_field in ["error_count", "failed_logins"]:
                if int_field in cleaned and cleaned[int_field] is not None:
                    try:
                        cleaned[int_field] = int(cleaned[int_field])
                    except (ValueError, TypeError):
                        cleaned[int_field] = 0

            return TelemetryPayload(**cleaned)
        except Exception:
            return None

    def process_telemetry(
        self, payload_input: Union[Dict[str, Any], TelemetryPayload]
    ) -> List[Alert]:
        """
        Main processing method for incoming telemetry.
        Runs Layer 1 (Thresholds), Layer 2 (Statistical), and Layer 3 (Isolation Forest).
        Returns a list of explainable Alert objects.
        """
        payload = self._to_payload(payload_input)
        if payload is None:
            return []

        alerts: List[Alert] = []

        # Layer 1: Static Threshold Detection
        threshold_alerts = self.detect_thresholds(payload)
        alerts.extend(threshold_alerts)

        # Layer 2: Statistical Detection (Z-score & sudden changes)
        statistical_alerts = self.detect_statistical(payload)
        alerts.extend(statistical_alerts)

        # Layer 3: ML Isolation Forest Detection (Multivariate patterns)
        ml_alerts = self.detect_isolation_forest(payload)
        alerts.extend(ml_alerts)

        # Update sliding history with current feature vector
        history = self._get_history(payload.tenant_id, payload.source_id)
        vector = [getattr(payload, f) for f in self.FEATURE_NAMES]
        history.append(vector)

        return alerts

    def detect_thresholds(self, payload: TelemetryPayload) -> List[Alert]:
        """
        Layer 1: Deterministic threshold rules.
        """
        alerts: List[Alert] = []
        now_utc = datetime.now(timezone.utc).isoformat()

        # Collector Offline check
        if payload.collector_status.lower() == "offline":
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_COLLECTOR_OFFLINE,
                    severity=SEVERITY_CRITICAL,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="collector_status",
                    metric_value=0.0,
                    threshold=1.0,
                    evidence=f"Collector on node '{payload.source_id}' reported status 'offline'",
                    detection_method="threshold",
                    anomaly_score=1.0,
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        # CPU Threshold (> 95%)
        if payload.cpu > THRESHOLD_CPU_PERCENT:
            sev = SEVERITY_CRITICAL if payload.cpu >= 98.0 else SEVERITY_HIGH
            score = min(1.0, 0.7 + (payload.cpu - THRESHOLD_CPU_PERCENT) / 10.0)
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_CPU_SPIKE,
                    severity=sev,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="cpu",
                    metric_value=payload.cpu,
                    threshold=THRESHOLD_CPU_PERCENT,
                    evidence=f"CPU utilization at {payload.cpu:.1f}% exceeded critical threshold of {THRESHOLD_CPU_PERCENT}%",
                    detection_method="threshold",
                    anomaly_score=round(score, 3),
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        # RAM Threshold (> 90%)
        if payload.memory > THRESHOLD_MEMORY_PERCENT:
            sev = SEVERITY_CRITICAL if payload.memory >= 96.0 else SEVERITY_HIGH
            score = min(1.0, 0.7 + (payload.memory - THRESHOLD_MEMORY_PERCENT) / 10.0)
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_MEMORY_SPIKE,
                    severity=sev,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="memory",
                    metric_value=payload.memory,
                    threshold=THRESHOLD_MEMORY_PERCENT,
                    evidence=f"Memory utilization at {payload.memory:.1f}% exceeded threshold of {THRESHOLD_MEMORY_PERCENT}%",
                    detection_method="threshold",
                    anomaly_score=round(score, 3),
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        # Disk Threshold (> 90%)
        if payload.disk > THRESHOLD_DISK_PERCENT:
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_DISK_SPIKE,
                    severity=SEVERITY_HIGH,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="disk",
                    metric_value=payload.disk,
                    threshold=THRESHOLD_DISK_PERCENT,
                    evidence=f"Disk usage at {payload.disk:.1f}% exceeded warning threshold of {THRESHOLD_DISK_PERCENT}%",
                    detection_method="threshold",
                    anomaly_score=round(min(1.0, 0.6 + (payload.disk - THRESHOLD_DISK_PERCENT) / 20.0), 3),
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        # Latency Threshold (> 250ms)
        if payload.latency_ms > THRESHOLD_LATENCY_MS:
            sev = SEVERITY_CRITICAL if payload.latency_ms > 800.0 else SEVERITY_HIGH
            score = min(1.0, 0.65 + min(0.35, (payload.latency_ms - THRESHOLD_LATENCY_MS) / 1000.0))
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_LATENCY_SPIKE,
                    severity=sev,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="latency_ms",
                    metric_value=payload.latency_ms,
                    threshold=THRESHOLD_LATENCY_MS,
                    evidence=f"Network latency at {payload.latency_ms:.1f}ms exceeded threshold of {THRESHOLD_LATENCY_MS}ms",
                    detection_method="threshold",
                    anomaly_score=round(score, 3),
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        # Packet Loss Threshold (> 5%)
        if payload.packet_loss_pct > THRESHOLD_PACKET_LOSS_PCT:
            sev = SEVERITY_CRITICAL if payload.packet_loss_pct >= 10.0 else SEVERITY_HIGH
            score = min(1.0, 0.65 + (payload.packet_loss_pct - THRESHOLD_PACKET_LOSS_PCT) / 20.0)
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_PACKET_LOSS_SPIKE,
                    severity=sev,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="packet_loss_pct",
                    metric_value=payload.packet_loss_pct,
                    threshold=THRESHOLD_PACKET_LOSS_PCT,
                    evidence=f"Network packet loss at {payload.packet_loss_pct:.1f}% exceeded critical threshold of {THRESHOLD_PACKET_LOSS_PCT}%",
                    detection_method="threshold",
                    anomaly_score=round(score, 3),
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        # Failed Logins Threshold (>= 3)
        if payload.failed_logins >= THRESHOLD_FAILED_LOGINS:
            sev = SEVERITY_CRITICAL if payload.failed_logins >= 5 else SEVERITY_HIGH
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_FAILED_LOGINS_SPIKE,
                    severity=sev,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="failed_logins",
                    metric_value=float(payload.failed_logins),
                    threshold=float(THRESHOLD_FAILED_LOGINS),
                    evidence=f"Repeated authentication failures detected: {payload.failed_logins} failed logins (threshold: {THRESHOLD_FAILED_LOGINS})",
                    detection_method="threshold",
                    anomaly_score=round(min(1.0, 0.7 + (payload.failed_logins / 10.0)), 3),
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        # Error Count Threshold (>= 10)
        if payload.error_count >= THRESHOLD_ERROR_COUNT:
            sev = SEVERITY_CRITICAL if payload.error_count >= 50 else SEVERITY_HIGH
            alerts.append(
                Alert(
                    id=f"alt_{uuid.uuid4().hex[:8]}",
                    alert_type=ALERT_ERROR_BURST,
                    severity=sev,
                    source_id=payload.source_id,
                    tenant_id=payload.tenant_id,
                    payload_id=payload.payload_id,
                    metric_name="error_count",
                    metric_value=float(payload.error_count),
                    threshold=float(THRESHOLD_ERROR_COUNT),
                    evidence=f"Error burst detected: {payload.error_count} application errors (threshold: {THRESHOLD_ERROR_COUNT})",
                    detection_method="threshold",
                    anomaly_score=round(min(1.0, 0.6 + (payload.error_count / 100.0)), 3),
                    timestamp=payload.timestamp_utc or now_utc,
                )
            )

        return alerts

    def detect_statistical(self, payload: TelemetryPayload) -> List[Alert]:
        """
        Layer 2: Statistical anomaly detection using rolling mean, std-dev, and Z-score.
        Identifies subtle anomalies that haven't crossed static thresholds yet.
        """
        alerts: List[Alert] = []
        history = self._get_history(payload.tenant_id, payload.source_id)

        # Need at least 5 previous baseline samples for reliable statistical variance
        if len(history) < 5:
            return alerts

        history_array = np.array(history)  # shape (N, num_features)
        now_utc = datetime.now(timezone.utc).isoformat()

        # Check key numeric metrics for Z-score deviation
        check_metrics = [
            ("cpu", payload.cpu, 0, ALERT_CPU_SPIKE),
            ("memory", payload.memory, 1, ALERT_MEMORY_SPIKE),
            ("latency_ms", payload.latency_ms, 3, ALERT_LATENCY_SPIKE),
            ("packet_loss_pct", payload.packet_loss_pct, 4, ALERT_PACKET_LOSS_SPIKE),
        ]

        for metric_name, current_val, col_idx, alert_type in check_metrics:
            series = history_array[:, col_idx]
            mean_val = float(np.mean(series))
            std_val = float(np.std(series))

            # If variance is non-zero, compute Z-score
            if std_val > 0.001:
                z_score = (current_val - mean_val) / std_val
                # Only flag positive surges (metric worsening)
                if z_score >= self.z_score_threshold:
                    score = min(1.0, 0.5 + (z_score - self.z_score_threshold) * 0.1)
                    sev = SEVERITY_HIGH if z_score >= 4.5 else SEVERITY_MEDIUM
                    alerts.append(
                        Alert(
                            id=f"alt_stat_{uuid.uuid4().hex[:8]}",
                            alert_type=alert_type,
                            severity=sev,
                            source_id=payload.source_id,
                            tenant_id=payload.tenant_id,
                            payload_id=payload.payload_id,
                            metric_name=metric_name,
                            metric_value=current_val,
                            threshold=round(mean_val + (self.z_score_threshold * std_val), 2),
                            evidence=(
                                f"Statistical anomaly in {metric_name}: current value {current_val:.1f} "
                                f"deviates with Z-score {z_score:.2f} (baseline mean: {mean_val:.1f}, "
                                f"std: {std_val:.2f})"
                            ),
                            detection_method="statistical",
                            anomaly_score=round(score, 3),
                            timestamp=payload.timestamp_utc or now_utc,
                        )
                    )

        return alerts

    def detect_isolation_forest(self, payload: TelemetryPayload) -> List[Alert]:
        """
        Layer 3: Unsupervised Machine Learning using Isolation Forest.
        Detects anomalous multi-variate correlations across metrics.
        Gracefully falls back if scikit-learn is unavailable or history is insufficient.
        """
        if not SKLEARN_AVAILABLE:
            return []

        history = self._get_history(payload.tenant_id, payload.source_id)

        # Ensure sufficient history samples before fitting
        if len(history) < self.min_ml_samples:
            return []

        now_utc = datetime.now(timezone.utc).isoformat()
        current_vector = np.array([[getattr(payload, f) for f in self.FEATURE_NAMES]])

        try:
            # Fit Isolation Forest on the rolling window
            data = np.array(history)
            model = IsolationForest(
                n_estimators=50,
                contamination=self.iforest_contamination,
                random_state=42,
            )
            model.fit(data)

            # Predict: -1 indicates anomaly, 1 indicates normal
            pred = model.predict(current_vector)[0]
            score_raw = model.decision_function(current_vector)[0]

            if pred == -1:
                # Map negative score to 0.5 - 1.0 range
                anomaly_score = min(1.0, max(0.5, 0.5 - (score_raw * 2.0)))
                sev = SEVERITY_CRITICAL if anomaly_score >= 0.85 else SEVERITY_HIGH

                # Identify which features contributed most to the anomaly
                data_mean = np.mean(data, axis=0)
                deviations = np.abs(current_vector[0] - data_mean)
                top_idx = int(np.argmax(deviations))
                top_feature = self.FEATURE_NAMES[top_idx]

                alerts = [
                    Alert(
                        id=f"alt_ml_{uuid.uuid4().hex[:8]}",
                        alert_type=ALERT_MULTIVARIATE_ANOMALY,
                        severity=sev,
                        source_id=payload.source_id,
                        tenant_id=payload.tenant_id,
                        payload_id=payload.payload_id,
                        metric_name=top_feature,
                        metric_value=getattr(payload, top_feature),
                        threshold=None,
                        evidence=(
                            f"Isolation Forest detected multivariate anomaly with anomaly score "
                            f"{anomaly_score:.2f}. Dominant abnormal metric is '{top_feature}' "
                            f"(current: {getattr(payload, top_feature)}, baseline mean: {data_mean[top_idx]:.1f})"
                        ),
                        detection_method="isolation_forest",
                        anomaly_score=round(float(anomaly_score), 3),
                        timestamp=payload.timestamp_utc or now_utc,
                    )
                ]
                return alerts

        except Exception:
            # Graceful fallback: never crash telemetry pipeline if ML training encounters issue
            return []

        return []

    def reset(self, tenant_id: Optional[str] = None, source_id: Optional[str] = None) -> None:
        """Reset historical sliding windows (useful for testing or node decommission)."""
        if tenant_id and source_id:
            key = (tenant_id, source_id)
            if key in self._history:
                del self._history[key]
        else:
            self._history.clear()
            self._models.clear()
