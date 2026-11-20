"""
SentinelOps AI - Egress Audit Retrieval API Routes.
Phase 2 Endpoint for Member 3 (Dashboard) to query Egress Proof records.
"""

from typing import Optional, List
from fastapi import APIRouter, Query
from backend.schemas import ApiResponse
from collector.egress_audit import EgressAuditLogger, EgressAuditRecord

router = APIRouter(prefix="/api/v1/audit", tags=["Egress Audit"])

# Singleton audit logger instance shared or queryable
audit_logger = EgressAuditLogger()


@router.get(
    "/egress",
    response_model=ApiResponse,
    summary="Retrieve Egress Audit Records",
    description="Retrieve immutable audit records proving what was scrubbed, allowed, and transmitted.",
)
async def get_egress_audit(
    source_id: Optional[str] = Query(None, description="Filter by node source_id"),
    limit: Optional[int] = Query(50, ge=1, le=200, description="Max audit records to return"),
) -> ApiResponse:
    records = audit_logger.get_all(source_id=source_id, limit=limit)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(records)} egress audit records",
        data=[record.model_dump() for record in records],
    )


@router.get(
    "/egress/latest",
    response_model=ApiResponse,
    summary="Get Latest Egress Audit Record",
    description="Retrieve the most recent egress audit record showing proof of privacy.",
)
async def get_latest_egress_audit(
    source_id: Optional[str] = Query(None, description="Optional source filter"),
) -> ApiResponse:
    record = audit_logger.get_latest(source_id=source_id)
    return ApiResponse(
        success=True,
        message="Latest egress audit retrieved",
        data=record.model_dump() if record else None,
    )
