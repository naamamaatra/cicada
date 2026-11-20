"""
SentinelOps AI - Pydantic Schemas for Telemetry, Alerts, and API Responses.
Strictly defines the Phase 1 shared contracts.
"""

from datetime import datetime, timezone
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator


class TelemetryPayload(BaseModel):
    """
    Standard Telemetry Data Schema.
    Agreed contract between Member 1 (Collector), Member 2 (AI),
    Member 3 (Dashboard), and Member 4 (Backend).
    """
    payload_id: str = Field(
        ...,
        description="Unique identifier for the telemetry event (e.g. evt_0001)",
        min_length=1,
    )
    tenant_id: str = Field(
        ...,
        description="Tenant identifier for multi-tenancy separation",
        min_length=1,
    )
    source_id: str = Field(
        ...,
        description="Pseudonymous host/node identifier (e.g. node_a81f)",
        min_length=1,
    )
    timestamp_utc: datetime = Field(
        ...,
        description="Event generation timestamp in UTC (ISO-8601)",
    )
    cpu: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="CPU utilization percentage (0.0 - 100.0)",
    )
    memory: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Memory utilization percentage (0.0 - 100.0)",
    )
    disk: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Disk utilization percentage (0.0 - 100.0)",
    )
    latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Network round-trip latency in milliseconds (>= 0.0)",
    )
    packet_loss_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Network packet loss percentage (0.0 - 100.0)",
    )
    error_count: int = Field(
        ...,
        ge=0,
        description="Count of system or application errors observed (>= 0)",
    )
    failed_logins: int = Field(
        ...,
        ge=0,
        description="Number of failed authentication attempts (>= 0)",
    )
    collector_status: str = Field(
        ...,
        description="Status of the local collector agent (e.g. 'online', 'degraded')",
        min_length=1,
    )
    event_category: Optional[str] = Field(
        default=None,
        description="Optional category (e.g. 'resource_pressure', 'normal', 'network_spike')",
    )

    @field_validator("payload_id", "tenant_id", "source_id", "collector_status")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must not be empty or whitespace only.")
        return v.strip()


class Alert(BaseModel):
    """
    Alert record triggered by abnormal thresholds or rules.
    """
    alert_id: str = Field(..., description="Unique alert ID (e.g. alt_xxxx)")
    payload_id: str = Field(..., description="ID of telemetry payload that caused this alert")
    source_id: str = Field(..., description="Affected infrastructure source / node")
    alert_type: str = Field(..., description="Type of alert (e.g. HIGH_CPU, HIGH_MEMORY)")
    severity: str = Field(..., description="Alert severity: WARNING, CRITICAL")
    message: str = Field(..., description="Human-readable explanation of the alert")
    metric_value: float = Field(..., description="Observed metric value")
    threshold: float = Field(..., description="Threshold exceeded")
    timestamp_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the alert was triggered",
    )


class TelemetryIngestResponse(BaseModel):
    """
    Standard response returned when a collector posts telemetry.
    """
    success: bool = True
    message: str = "Telemetry received successfully"
    payload_id: str
    alerts_generated: int = 0
    alerts: List[Alert] = []


class HealthResponse(BaseModel):
    """
    System health check response.
    """
    success: bool = True
    status: str = "HEALTHY"
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    telemetry_count: int = 0
    alerts_count: int = 0
    active_sources_count: int = 0


class MetricsSummary(BaseModel):
    """
    Overview summary of fleet status for dashboard and monitoring.
    """
    total_sources: int = 0
    total_telemetry_events: int = 0
    healthy_sources: int = 0
    warning_sources: int = 0
    critical_sources: int = 0
    active_alert_count: int = 0


class ApiResponse(BaseModel):
    """
    Generic unified API response wrapper.
    """
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None
