"""
Shared Pydantic data models for SentinelOps AI telemetry and alert schemas.
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class TelemetryPayload(BaseModel):
    """
    Standard agreed telemetry payload across all 4 team members.
    """
    payload_id: str = Field(..., description="Unique event ID for deduplication")
    tenant_id: str = Field(default="tenant_demo", description="Tenant separation identifier")
    source_id: str = Field(..., description="Pseudonymous node/server identifier")
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cpu: float = Field(..., ge=0.0, le=100.0, description="CPU utilization percentage")
    memory: float = Field(..., ge=0.0, le=100.0, description="Memory utilization percentage")
    disk: float = Field(..., ge=0.0, le=100.0, description="Disk utilization percentage")
    latency_ms: float = Field(..., ge=0.0, description="Network round-trip latency in ms")
    packet_loss_pct: float = Field(..., ge=0.0, le=100.0, description="Packet loss percentage")
    error_count: int = Field(default=0, ge=0, description="Observed error events in window")
    failed_logins: int = Field(default=0, ge=0, description="Failed authentication attempts")
    collector_status: str = Field(default="online", description="Collector health state (online/degraded/offline)")
    event_category: str = Field(default="normal_telemetry", description="Telemetry classification category")


class BasicAlert(BaseModel):
    """
    Alert triggered when a threshold is breached.
    """
    alert_id: str
    source_id: str
    metric: str
    current_value: float
    threshold: float
    severity: str  # WARNING, CRITICAL
    message: str
    timestamp_utc: str
