"""
SentinelOps AI - Organization & Workspace Management Routes.
Enforces multi-tenancy boundaries and role permissions.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import User, Organization, Membership, Collector, Incident, AuditLog
from backend.core.dependencies import get_current_user, get_tenant_membership
from backend.schemas_saas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    MemberItemResponse,
    AuditLogItemResponse,
)
from backend.routes.auth import generate_slug

router = APIRouter(prefix="/api/v1/orgs", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Organization / Workspace",
    description="Create a new tenant organization and assign the creator as Owner.",
)
def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationResponse:
    # 1. Generate slug
    slug = payload.slug.strip() if payload.slug else generate_slug(payload.name)

    # Check if slug exists
    existing = db.execute(select(Organization).where(Organization.slug == slug)).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    org = Organization(
        name=payload.name,
        slug=slug,
    )
    db.add(org)
    db.flush()

    # 2. Add creator as Owner
    membership = Membership(
        user_id=current_user.id,
        organization_id=org.id,
        role="owner",
    )
    db.add(membership)

    # 3. Audit log
    audit = AuditLog(
        organization_id=org.id,
        actor_user_id=current_user.id,
        action="organization.created",
        resource_type="organization",
        resource_id=org.id,
        safe_metadata={"name": org.name, "slug": org.slug},
    )
    db.add(audit)

    db.commit()
    db.refresh(org)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        role="owner",
        created_at=org.created_at,
        collector_count=0,
        incident_count=0,
    )


@router.get(
    "",
    response_model=List[OrganizationResponse],
    summary="List My Organizations",
    description="Retrieve all organizations where the authenticated user holds membership.",
)
def list_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OrganizationResponse]:
    memberships = db.execute(
        select(Membership, Organization)
        .join(Organization, Membership.organization_id == Organization.id)
        .where(Membership.user_id == current_user.id)
    ).all()

    results = []
    for mem, org in memberships:
        # Count collectors and incidents for this tenant
        collector_count = db.execute(
            select(func.count(Collector.id)).where(Collector.organization_id == org.id)
        ).scalar() or 0

        incident_count = db.execute(
            select(func.count(Incident.id)).where(Incident.organization_id == org.id)
        ).scalar() or 0

        results.append(
            OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                role=mem.role,
                created_at=org.created_at,
                collector_count=collector_count,
                incident_count=incident_count,
            )
        )

    return results


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get Organization Details",
    description="Retrieve organization metadata. Strictly scoped by tenant membership.",
)
def get_organization(
    org_id: str,
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> OrganizationResponse:
    org = db.execute(select(Organization).where(Organization.id == org_id)).scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    collector_count = db.execute(
        select(func.count(Collector.id)).where(Collector.organization_id == org.id)
    ).scalar() or 0

    incident_count = db.execute(
        select(func.count(Incident.id)).where(Incident.organization_id == org.id)
    ).scalar() or 0

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        role=membership.role,
        created_at=org.created_at,
        collector_count=collector_count,
        incident_count=incident_count,
    )


@router.get(
    "/{org_id}/members",
    response_model=List[MemberItemResponse],
    summary="List Organization Members",
    description="Retrieve all members of the organization. Strictly scoped by tenant membership.",
)
def get_organization_members(
    org_id: str,
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> List[MemberItemResponse]:
    rows = db.execute(
        select(Membership, User)
        .join(User, Membership.user_id == User.id)
        .where(Membership.organization_id == org_id)
        .order_by(Membership.created_at.asc())
    ).all()

    return [
        MemberItemResponse(
            id=mem.id,
            user_id=usr.id,
            email=usr.email,
            full_name=usr.full_name,
            role=mem.role,
            created_at=mem.created_at,
        )
        for mem, usr in rows
    ]


@router.get(
    "/{org_id}/audit-logs",
    response_model=List[AuditLogItemResponse],
    summary="List Organization Audit Logs",
    description="Retrieve recent audit log entries for the organization. Strictly scoped by tenant membership.",
)
def get_organization_audit_logs(
    org_id: str,
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
    limit: int = 50,
) -> List[AuditLogItemResponse]:
    logs = db.execute(
        select(AuditLog)
        .where(AuditLog.organization_id == org_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    ).scalars().all()

    return [
        AuditLogItemResponse(
            id=log.id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_user_id=log.actor_user_id,
            timestamp=log.timestamp,
            safe_metadata=log.safe_metadata or {},
        )
        for log in logs
    ]


