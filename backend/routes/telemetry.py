"""
SentinelOps AI - Telemetry Ingestion & Retrieval API Routes.
Provides endpoints for Member 1 (Collector) to push and Member 3 (Dashboard) / Member 2 (AI) to read.
"""

from typing import Optional, List
import random
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from backend.schemas import (
    TelemetryPayload,
    TelemetryIngestResponse,
    ApiResponse,
)
from backend.storage import storage
from backend.services.alert_service import evaluate_telemetry_alerts
from collector.generator import TelemetryGenerator

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.post(
    "",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Telemetry Data",
    description="Receive, validate, store telemetry, evaluate threshold alerts, and return result.",
)
async def ingest_telemetry(payload: TelemetryPayload) -> TelemetryIngestResponse:
    # 1. Store in-memory
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

    # 2. Evaluate basic threshold alerts (Phase 1)
    triggered_alerts = evaluate_telemetry_alerts(payload)

    # 3. Store alerts if any
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


@router.post(
    "/simulate/{scenario}",
    response_model=ApiResponse,
    summary="Simulate Realistic Dynamic Scenario Telemetry",
    description="Generate dynamic, realistic, non-static telemetry across all 3 nodes with natural jitter.",
)
async def simulate_scenario(scenario: str) -> ApiResponse:
    gen = TelemetryGenerator()
    now = datetime.now(timezone.utc).isoformat()
    norm_scn = scenario.lower().replace("-", "_")

    payloads = []

    # Reset historical alerts for clean, non-conflicting scenario presentation
    storage.clear_alerts()

    if norm_scn in ("spike", "cpu_spike"):
        # node_a81f spiked with dynamic realistic variation
        p_a = gen.generate_cpu_spike(source_id="node_a81f")
        p_b = gen.generate_normal(source_id="node_b92c", timestamp_utc=now)
        p_c = gen.generate_normal(source_id="node_c73d", timestamp_utc=now)
        payloads = [p_a, p_b, p_c]
    elif norm_scn in ("network", "network_outage"):
        # node_c73d degraded with dynamic realistic latency & loss
        p_a = gen.generate_normal(source_id="node_a81f", timestamp_utc=now)
        p_b = gen.generate_normal(source_id="node_b92c", timestamp_utc=now)
        p_c = gen.generate_network_degradation(source_id="node_c73d")
        payloads = [p_a, p_b, p_c]
    elif norm_scn in ("degraded", "db_overload", "database_overload"):
        # node_b92c database overload with dynamic variation
        p_a = gen.generate_normal(source_id="node_a81f", timestamp_utc=now)
        p_b = {
            "payload_id": gen._next_payload_id("evt_db"),
            "tenant_id": gen.tenant_id,
            "source_id": "node_b92c",
            "timestamp_utc": now,
            "cpu": round(random.uniform(72.0, 84.5), 1),
            "memory": round(random.uniform(90.5, 95.8), 1),
            "disk": round(random.uniform(96.8, 99.4), 1),
            "latency_ms": round(random.uniform(165.0, 245.0), 1),
            "packet_loss_pct": round(random.uniform(0.1, 0.4), 2),
            "error_count": random.randint(18, 38),
            "failed_logins": random.randint(9, 22),
            "collector_status": "online",
            "event_category": "database_overload",
        }
        p_c = gen.generate_normal(source_id="node_c73d", timestamp_utc=now)
        payloads = [p_a, p_b, p_c]
    else:
        # normal baseline: all 3 healthy with fresh realistic jitter
        payloads = gen.generate_fleet_normal()

    all_alerts = []
    pydantic_payloads = []
    for raw in payloads:
        pyd = TelemetryPayload(**raw)
        storage.add_telemetry(pyd)
        pydantic_payloads.append(pyd)
        alerts = evaluate_telemetry_alerts(pyd)
        if alerts:
            storage.add_alerts(alerts)
            all_alerts.extend(alerts)

    fleet_lat_avg = round(sum(p.latency_ms for p in pydantic_payloads) / len(pydantic_payloads), 1)

    return ApiResponse(
        success=True,
        message=f"Simulated realistic {norm_scn} telemetry across fleet",
        data={
            "scenario": norm_scn,
            "fleet_latency_avg": fleet_lat_avg,
            "sources": [p.model_dump(mode="json") for p in pydantic_payloads],
            "alerts": [a.model_dump(mode="json") for a in all_alerts],
        },
    )

