"""
SentinelOps AI - Incident Management & Workflow API Routes.
Provides tenant-scoped querying, filtering, and lifecycle transitions:
Open -> Investigating -> Resolved -> Dismissed.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import Incident as DBIncident, AuditLog, Membership, utc_now
from backend.core.dependencies import get_tenant_membership

router = APIRouter(prefix="/api/v1/orgs/{org_id}/incidents", tags=["Incidents"])


class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., description="Target status: 'open', 'investigating', 'resolved', 'dismissed'")


class IncidentResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    source_id: Optional[str] = None
    first_detected_at: datetime
    last_updated_at: datetime
    resolved_at: Optional[datetime] = None


@router.get(
    "",
    response_model=List[IncidentResponse],
    summary="List Organization Incidents",
    description="Retrieve all correlated AI incidents for this organization with optional filters.",
)
def list_incidents(
    org_id: str,
    status: Optional[str] = Query(None, description="Filter by status ('open', 'investigating', 'resolved', 'dismissed')"),
    severity: Optional[str] = Query(None, description="Filter by severity ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')"),
    source_id: Optional[str] = Query(None, description="Filter by affected source/node"),
    limit: int = Query(100, ge=1, le=500),
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> List[IncidentResponse]:
    query = select(DBIncident).where(DBIncident.organization_id == org_id)

    if status:
        query = query.where(DBIncident.status == status.lower())
    if severity:
        query = query.where(DBIncident.severity == severity.upper())
    if source_id:
        query = query.where(DBIncident.source_id == source_id)

    query = query.order_by(DBIncident.last_updated_at.desc()).limit(limit)
    incidents = db.execute(query).scalars().all()

    return [
        IncidentResponse(
            id=inc.id,
            organization_id=inc.organization_id,
            title=inc.title,
            description=inc.description,
            severity=inc.severity,
            status=inc.status,
            source_id=inc.source_id,
            first_detected_at=inc.first_detected_at,
            last_updated_at=inc.last_updated_at,
            resolved_at=inc.resolved_at,
        )
        for inc in incidents
    ]


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get Incident Details",
    description="Retrieve detailed AI explanation, evidence, and recommendations for a specific incident.",
)
def get_incident(
    org_id: str,
    incident_id: str,
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> IncidentResponse:
    inc = db.execute(
        select(DBIncident).where(
            and_(
                DBIncident.id == incident_id,
                DBIncident.organization_id == org_id,
            )
        )
    ).scalar_one_or_none()

    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found in organization '{org_id}'",
        )

    return IncidentResponse(
        id=inc.id,
        organization_id=inc.organization_id,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        status=inc.status,
        source_id=inc.source_id,
        first_detected_at=inc.first_detected_at,
        last_updated_at=inc.last_updated_at,
        resolved_at=inc.resolved_at,
    )


@router.patch(
    "/{incident_id}/status",
    response_model=IncidentResponse,
    summary="Update Incident Status",
    description="Transition incident lifecycle: open -> investigating -> resolved -> dismissed.",
)
def update_incident_status(
    org_id: str,
    incident_id: str,
    payload: IncidentStatusUpdate,
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> IncidentResponse:
    new_status = payload.status.lower().strip()
    valid_statuses = ["open", "investigating", "resolved", "dismissed"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Must be one of {valid_statuses}",
        )

    inc = db.execute(
        select(DBIncident).where(
            and_(
                DBIncident.id == incident_id,
                DBIncident.organization_id == org_id,
            )
        )
    ).scalar_one_or_none()

    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found in organization '{org_id}'",
        )

    old_status = inc.status
    inc.status = new_status
    now = utc_now()
    inc.last_updated_at = now

    if new_status == "resolved":
        inc.resolved_at = now
    elif old_status == "resolved" and new_status != "resolved":
        inc.resolved_at = None

    # Record Audit Log
    audit = AuditLog(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        action="incident.status_updated",
        resource_type="incident",
        resource_id=inc.id,
        safe_metadata={
            "from_status": old_status,
            "to_status": new_status,
            "title": inc.title,
        },
    )
    db.add(audit)
    db.commit()
    db.refresh(inc)

    return IncidentResponse(
        id=inc.id,
        organization_id=inc.organization_id,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        status=inc.status,
        source_id=inc.source_id,
        first_detected_at=inc.first_detected_at,
        last_updated_at=inc.last_updated_at,
        resolved_at=inc.resolved_at,
    )
