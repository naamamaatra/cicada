"""
SentinelOps AI - Alert Retrieval API Routes.
Provides endpoints for querying threshold alerts generated in Phase 1.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.schemas import ApiResponse
from backend.storage import storage

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=ApiResponse,
    summary="Retrieve Alerts",
    description="Retrieve list of alerts, newest first. Supports source_id filter and limit.",
)
async def get_alerts(
    source_id: Optional[str] = Query(None, description="Filter alerts by source ID"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Max alerts to return"),
) -> ApiResponse:
    alerts = storage.get_all_alerts(source_id=source_id, limit=limit)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(alerts)} alerts",
        data=[alert.model_dump(mode="json") for alert in alerts],
    )


@router.get(
    "/latest",
    response_model=ApiResponse,
    summary="Get Latest Alert",
    description="Retrieve the single most recent alert across all sources or for a specific source.",
)
async def get_latest_alert(
    source_id: Optional[str] = Query(None, description="Optional source ID filter"),
) -> ApiResponse:
    alert = storage.get_latest_alert(source_id=source_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No alerts found",
        )
    return ApiResponse(
        success=True,
        message="Latest alert retrieved successfully",
        data=alert.model_dump(mode="json"),
    )


@router.get(
    "/{source_id}",
    response_model=ApiResponse,
    summary="Get Alerts for Specific Source",
    description="Retrieve all alerts generated for a specific node.",
)
async def get_alerts_by_source(
    source_id: str,
    limit: Optional[int] = Query(50, ge=1, le=500, description="Max alerts to return"),
) -> ApiResponse:
    alerts = storage.get_alerts_by_source(source_id=source_id, limit=limit)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(alerts)} alerts for source '{source_id}'",
        data=[alert.model_dump(mode="json") for alert in alerts],
    )


@router.delete(
    "",
    response_model=ApiResponse,
    summary="Clear Stored Alerts",
    description="Clear active and historical alerts, optionally filtered by source_id.",
)
async def clear_alerts(
    source_id: Optional[str] = Query(None, description="Optional source ID filter"),
) -> ApiResponse:
    storage.clear_alerts(source_id=source_id)
    return ApiResponse(
        success=True,
        message=f"Alerts cleared{' for source ' + source_id if source_id else ' across all sources'}",
        data={"cleared": True},
    )


@router.post(
    "/clear",
    response_model=ApiResponse,
    summary="Reset/Clear Alerts (POST helper)",
    description="Convenience POST endpoint to clear alerts.",
)
async def reset_alerts(
    source_id: Optional[str] = Query(None, description="Optional source ID filter"),
) -> ApiResponse:
    storage.clear_alerts(source_id=source_id)
    return ApiResponse(
        success=True,
        message=f"Alerts cleared{' for source ' + source_id if source_id else ' across all sources'}",
        data={"cleared": True},
    )

