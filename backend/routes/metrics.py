"""
SentinelOps AI - Tenant-Scoped Infrastructure Monitoring Routes.
Queries persistent database telemetry records strictly bounded to the organization.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import TelemetryRecord, Incident, Membership
from backend.core.dependencies import get_tenant_membership
from backend.schemas import ApiResponse
from backend.services.alert_service import classify_health
from backend.schemas import TelemetryPayload

router = APIRouter(prefix="/api/v1/orgs/{org_id}/metrics", tags=["Infrastructure Monitoring"])


@router.get(
    "",
    response_model=ApiResponse,
    summary="Get Tenant Infrastructure Metrics",
    description="Retrieve real historical telemetry records for nodes enrolled in this organization.",
)
def get_tenant_metrics(
    org_id: str,
    source_id: Optional[str] = Query(None, description="Filter by node source_id"),
    limit: int = Query(100, ge=1, le=1000),
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> ApiResponse:
    query = select(TelemetryRecord).where(TelemetryRecord.organization_id == org_id)
    if source_id:
        query = query.where(TelemetryRecord.source_id == source_id)

    query = query.order_by(TelemetryRecord.timestamp_utc.desc()).limit(limit)
    records = db.execute(query).scalars().all()

    data = [
        {
            "id": r.id,
            "payload_id": r.payload_id,
            "organization_id": r.organization_id,
            "collector_id": r.collector_id,
            "source_id": r.source_id,
            "timestamp_utc": r.timestamp_utc.isoformat(),
            "cpu": r.cpu,
            "memory": r.memory,
            "disk": r.disk,
            "latency_ms": r.latency_ms,
            "packet_loss_pct": r.packet_loss_pct,
            "error_count": r.error_count,
            "failed_logins": r.failed_logins,
            "collector_status": r.collector_status,
            "event_category": r.event_category,
        }
        for r in records
    ]

    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data)} telemetry records for organization '{org_id}'",
        data=data,
    )


@router.get(
    "/summary",
    response_model=ApiResponse,
    summary="Get Tenant Fleet Health Summary",
    description="Calculates real fleet health state, source counts, and active incidents for this organization.",
)
def get_tenant_metrics_summary(
    org_id: str,
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> ApiResponse:
    # 1. Total telemetry count for this tenant
    total_events = db.execute(
        select(func.count(TelemetryRecord.id)).where(TelemetryRecord.organization_id == org_id)
    ).scalar() or 0

    # 2. Get distinct sources
    sources = db.execute(
        select(TelemetryRecord.source_id)
        .where(TelemetryRecord.organization_id == org_id)
        .distinct()
    ).scalars().all()

    healthy_count = 0
    warning_count = 0
    critical_count = 0

    # 3. For each source, fetch its single latest record
    for src in sources:
        latest = db.execute(
            select(TelemetryRecord)
            .where(TelemetryRecord.organization_id == org_id, TelemetryRecord.source_id == src)
            .order_by(TelemetryRecord.timestamp_utc.desc())
            .limit(1)
        ).scalar_one_or_none()

        if latest:
            # Map to TelemetryPayload for classification
            payload_obj = TelemetryPayload(
                payload_id=latest.payload_id,
                tenant_id=latest.organization_id,
                source_id=latest.source_id,
                timestamp_utc=latest.timestamp_utc,
                cpu=latest.cpu,
                memory=latest.memory,
                disk=latest.disk,
                latency_ms=latest.latency_ms,
                packet_loss_pct=latest.packet_loss_pct,
                error_count=latest.error_count,
                failed_logins=latest.failed_logins,
                collector_status=latest.collector_status,
                event_category=latest.event_category,
            )
            state = classify_health(payload_obj)
            if state == "CRITICAL":
                critical_count += 1
            elif state == "WARNING":
                warning_count += 1
            else:
                healthy_count += 1

    # 4. Count active incidents
    active_incidents = db.execute(
        select(func.count(Incident.id)).where(
            Incident.organization_id == org_id,
            Incident.status.in_(["open", "investigating"]),
        )
    ).scalar() or 0

    summary_data = {
        "organization_id": org_id,
        "total_sources": len(sources),
        "total_telemetry_events": total_events,
        "healthy_sources": healthy_count,
        "warning_sources": warning_count,
        "critical_sources": critical_count,
        "active_incidents": active_incidents,
    }

    return ApiResponse(
        success=True,
        message="Tenant metrics summary calculated successfully",
        data=summary_data,
    )

