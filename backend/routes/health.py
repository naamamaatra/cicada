"""
SentinelOps AI - Health and Metrics Summary API Routes.
Provides system status and fleet health summary for Member 3 (Dashboard).
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from backend.schemas import HealthResponse, MetricsSummary, ApiResponse
from backend.storage import storage
from backend.services.alert_service import calculate_metrics_summary

router = APIRouter(tags=["Health & Summary"])


@router.get(
    "/",
    response_model=ApiResponse,
    summary="Root Endpoint",
    description="Check backend service details and operational status.",
)
async def root() -> ApiResponse:
    return ApiResponse(
        success=True,
        message="SentinelOps AI Backend is operational",
        data={
            "project_name": "SentinelOps AI",
            "version": "1.0.0",
            "phase": "Phase 1 - Foundation & Ingest Engine",
            "role": "Member 4 - Backend & Integration",
            "status": "online",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Health Status",
    description="Return overall health status and telemetry counts.",
)
async def health_check() -> HealthResponse:
    latest_summary = calculate_metrics_summary(storage)
    overall_status = "HEALTHY"
    if latest_summary.critical_sources > 0:
        overall_status = "CRITICAL"
    elif latest_summary.warning_sources > 0:
        overall_status = "WARNING"

    return HealthResponse(
        success=True,
        status=overall_status,
        timestamp_utc=datetime.now(timezone.utc),
        telemetry_count=storage.total_telemetry_count(),
        alerts_count=storage.total_alerts_count(),
        active_sources_count=len(storage.get_all_sources()),
    )


@router.get(
    "/api/v1/metrics/summary",
    response_model=ApiResponse,
    summary="Fleet Metrics & Health Summary",
    description="Return categorized health counts across all monitored sources for the dashboard.",
)
async def metrics_summary() -> ApiResponse:
    summary = calculate_metrics_summary(storage)
    return ApiResponse(
        success=True,
        message="Fleet metrics summary calculated successfully",
        data=summary.model_dump(mode="json"),
    )
