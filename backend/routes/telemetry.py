"""
SentinelOps AI - Telemetry Ingestion & Retrieval API Routes.
Provides endpoints for Member 1 (Collector) to push and Member 3 (Dashboard) / Member 2 (AI) to read.
Supports authenticated collector ingestion with persistent multi-tenant scoping.
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.schemas import (
    TelemetryPayload,
    TelemetryIngestResponse,
    ApiResponse,
)
from backend.storage import storage
from backend.services.alert_service import evaluate_telemetry_alerts
from backend.services.ai_service import ai_service
from backend.db.session import get_db
from backend.db.models import Collector, TelemetryRecord, Organization
from backend.core.dependencies import get_authenticated_collector

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.post(
    "",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Telemetry Data",
    description=(
        "Receive, validate, store telemetry, evaluate threshold alerts, and return result. "
        "Supports authenticated collectors with automatic organization association."
    ),
)
async def ingest_telemetry(
    payload: TelemetryPayload,
    collector: Optional[Collector] = Depends(get_authenticated_collector),
    db: Session = Depends(get_db),
) -> TelemetryIngestResponse:
    # 1. Store in-memory for backwards-compatible live dashboard & testing
    inserted = storage.add_telemetry(payload)
    if not inserted:
        # Duplicate payload ID detected
        return TelemetryIngestResponse(
            success=True,
            message="Duplicate payload received (already processed)",
            payload_id=payload.payload_id,
            alerts_generated=0,
            alerts=[],
        )

    # 2. Determine target organization for persistent multi-tenant record
    target_org_id: Optional[str] = None
    collector_id: Optional[str] = None

    if collector:
        target_org_id = collector.organization_id
        collector_id = collector.id
    elif payload.tenant_id:
        # Check if tenant_id matches an existing organization ID or slug in DB
        try:
            org = db.execute(
                select(Organization).where(
                    (Organization.id == payload.tenant_id) | (Organization.slug == payload.tenant_id)
                )
            ).scalar_one_or_none()
            if org:
                target_org_id = org.id
        except Exception:
            target_org_id = None

    # 3. Persist to SQLite/PostgreSQL database if organization was identified
    if target_org_id:
        try:
            # Ensure timestamp is datetime
            ts = payload.timestamp_utc
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

            db_record = TelemetryRecord(
                payload_id=payload.payload_id,
                organization_id=target_org_id,
                collector_id=collector_id,
                source_id=payload.source_id,
                timestamp_utc=ts,
                cpu=payload.cpu,
                memory=payload.memory,
                disk=payload.disk,
                latency_ms=payload.latency_ms,
                packet_loss_pct=payload.packet_loss_pct,
                error_count=payload.error_count,
                failed_logins=payload.failed_logins,
                collector_status=payload.collector_status,
                event_category=payload.event_category,
            )
            db.add(db_record)
            db.commit()
        except Exception:
            db.rollback()  # If deduplication conflict or validation, ignore persistent save

        # 3b. Run Member 2 AI Incident Intelligence analysis and persist incidents
        try:
            ai_service.process_telemetry_for_tenant(
                payload.model_dump(mode="json"), target_org_id, db
            )
        except Exception:
            pass

    # 4. Evaluate basic threshold alerts (Phase 1)
    triggered_alerts = evaluate_telemetry_alerts(payload)

    # 5. Store alerts if any
    if triggered_alerts:
        storage.add_alerts(triggered_alerts)

    return TelemetryIngestResponse(
        success=True,
        message="Telemetry received successfully",
        payload_id=payload.payload_id,
        alerts_generated=len(triggered_alerts),
        alerts=triggered_alerts,
    )


@router.get(
    "",
    response_model=ApiResponse,
    summary="Retrieve Stored Telemetry",
    description="Retrieve telemetry records with optional source_id filter and limit.",
)
async def get_telemetry(
    source_id: Optional[str] = Query(None, description="Filter by source ID (node identifier)"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Max records to return"),
) -> ApiResponse:
    records = storage.get_all_telemetry(source_id=source_id, limit=limit)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(records)} telemetry records",
        data=[record.model_dump(mode="json") for record in records],
    )


@router.get(
    "/latest",
    response_model=ApiResponse,
    summary="Get Latest Telemetry Event",
    description="Retrieve the single most recent telemetry event across the fleet or for a source.",
)
async def get_latest_telemetry(
    source_id: Optional[str] = Query(None, description="Optional source filter"),
) -> ApiResponse:
    record = storage.get_latest_telemetry(source_id=source_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No telemetry records found",
        )
    return ApiResponse(
        success=True,
        message="Latest telemetry retrieved successfully",
        data=record.model_dump(mode="json"),
    )


@router.get(
    "/{source_id}",
    response_model=ApiResponse,
    summary="Get Telemetry for Specific Source",
    description="Retrieve recent telemetry events belonging to a specific node.",
)
async def get_telemetry_by_source(
    source_id: str,
    limit: Optional[int] = Query(50, ge=1, le=500, description="Max records to return"),
) -> ApiResponse:
    records = storage.get_telemetry_by_source(source_id=source_id, limit=limit)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(records)} records for source '{source_id}'",
        data=[record.model_dump(mode="json") for record in records],
    )
