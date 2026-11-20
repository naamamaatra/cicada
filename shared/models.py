"""
SentinelOps AI - Shared Pydantic Data Models.
Agreed schemas across all 4 team members for Phase 1 and beyond.
"""

from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator


class TelemetryPayload(BaseModel):
    """
    Standard agreed telemetry payload across all 4 team members.
    Matches Section 7 Shared Telemetry Schema.
    """
    payload_id: str = Field(
        ...,
        description="Unique identifier for the telemetry event for deduplication (e.g. evt_0001)",
        min_length=1,
    )
    tenant_id: str = Field(
        default="tenant_demo",
        description="Tenant identifier for multi-tenancy separation",
        min_length=1,
    )
    source_id: str = Field(
        ...,
        description="Pseudonymous host/node identifier (e.g. node_a81f)",
        min_length=1,
    )
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
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
        default=0,
        ge=0,
        description="Count of system or application errors observed (>= 0)",
    )
    failed_logins: int = Field(
        default=0,
        ge=0,
        description="Number of failed authentication attempts (>= 0)",
    )
    collector_status: str = Field(
        default="online",
        description="Status of the local collector agent (e.g. 'online', 'degraded', 'offline')",
        min_length=1,
    )
    event_category: Optional[str] = Field(
        default="normal",
        description="Optional telemetry classification category (e.g. 'normal', 'resource_pressure')",
    )

    @field_validator("payload_id", "tenant_id", "source_id", "collector_status")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"Field '{info.field_name}' must not be empty or whitespace only.")
        return v.strip()


class BasicAlert(BaseModel):
    """
    Alert record triggered by abnormal thresholds or rules.
    """
    alert_id: str = Field(..., description="Unique alert ID (e.g. alt_xxxx)")
    payload_id: Optional[str] = Field(default=None, description="Associated telemetry payload ID")
    source_id: str = Field(..., description="Affected infrastructure source / node")
    alert_type: str = Field(..., description="Type of alert (e.g. HIGH_CPU, HIGH_MEMORY)")
    severity: str = Field(..., description="Alert severity: WARNING, CRITICAL")
    message: str = Field(..., description="Human-readable explanation of the alert")
    metric_value: float = Field(..., description="Observed metric value")
    threshold: float = Field(..., description="Threshold exceeded")
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when the alert was triggered",
    )
