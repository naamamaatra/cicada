"""
SentinelOps AI - Collector Registration & Management Routes.
Enforces secure token generation, verification, and revocation.
"""

from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import Collector, AuditLog, Membership
from backend.core.security import generate_collector_token, hash_collector_token
from backend.core.dependencies import get_tenant_membership, require_role, get_current_user
from backend.schemas_saas import (
    CollectorCreateRequest,
    CollectorCreateResponse,
    CollectorResponse,
)

router = APIRouter(prefix="/api/v1/orgs/{org_id}/collectors", tags=["Collectors"])


@router.post(
    "",
    response_model=CollectorCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Collector Agent",
    description=(
        "Enroll a new infrastructure collector agent. Returns a high-entropy secret token "
        "displayed ONCE. Requires Owner or Admin role."
    ),
)
def register_collector(
    org_id: str,
    payload: CollectorCreateRequest,
    membership: Membership = Depends(require_role(["owner", "admin"])),
    db: Session = Depends(get_db),
) -> CollectorCreateResponse:
    # 1. Generate high-entropy raw token & hash
    raw_token = generate_collector_token()
    token_hash = hash_collector_token(raw_token)

    # 2. Store collector record with hashed token
    collector = Collector(
        organization_id=org_id,
        name=payload.name,
        status="registered",
        token_hash=token_hash,
    )
    db.add(collector)
    db.flush()

    # 3. Record Audit Log
    audit = AuditLog(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        action="collector.enrolled",
        resource_type="collector",
        resource_id=collector.id,
        safe_metadata={"collector_name": collector.name},
    )
    db.add(audit)

    db.commit()
    db.refresh(collector)

    return CollectorCreateResponse(
        id=collector.id,
        name=collector.name,
        organization_id=collector.organization_id,
        raw_token=raw_token,
        status=collector.status,
        created_at=collector.created_at,
    )


@router.get(
    "",
    response_model=List[CollectorResponse],
    summary="List Organization Collectors",
    description="Retrieve all collectors enrolled in this organization.",
)
def list_collectors(
    org_id: str,
    membership: Membership = Depends(get_tenant_membership),
    db: Session = Depends(get_db),
) -> List[CollectorResponse]:
    collectors = db.execute(
        select(Collector)
        .where(Collector.organization_id == org_id)
        .order_by(Collector.created_at.desc())
    ).scalars().all()

    return [
        CollectorResponse(
            id=c.id,
            name=c.name,
            organization_id=c.organization_id,
            status=c.status,
            last_seen=c.last_seen,
            created_at=c.created_at,
            revoked_at=c.revoked_at,
        )
        for c in collectors
    ]


@router.delete(
    "/{collector_id}",
    summary="Revoke Collector Access",
    description="Revoke credentials for a collector agent. Immediate invalidation.",
)
def revoke_collector(
    org_id: str,
    collector_id: str,
    membership: Membership = Depends(require_role(["owner", "admin"])),
    db: Session = Depends(get_db),
):
    collector = db.execute(
        select(Collector).where(
            Collector.id == collector_id,
            Collector.organization_id == org_id,
        )
    ).scalar_one_or_none()

    if not collector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collector '{collector_id}' not found in this organization",
        )

    collector.status = "revoked"
    collector.revoked_at = datetime.now(timezone.utc)

    # Record Audit Log
    audit = AuditLog(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        action="collector.revoked",
        resource_type="collector",
        resource_id=collector.id,
        safe_metadata={"collector_name": collector.name},
    )
    db.add(audit)

    db.commit()

    return {
        "success": True,
        "message": f"Collector '{collector.name}' ({collector.id}) access revoked successfully",
    }

