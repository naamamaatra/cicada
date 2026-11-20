# SentinelOps AI — Privacy-First AI Infrastructure Monitoring & Incident Intelligence Platform

SentinelOps AI monitors servers, applications, and networks, detects unusual behavior, identifies related alerts, suggests possible root causes, and recommends corrective actions — while prioritizing privacy by processing sensitive information locally and transmitting only approved, sanitized telemetry data.

---

## Team Division & Deliverables (Phase 1)

- **Member 1 (Collector & Privacy Engine):** Local telemetry generator, deep privacy redaction, hostname pseudonymization, allow-list policy gate, offline buffering, and egress audit proof logging.
- **Member 4 (Backend & Integration):** Phase 1 Backend Foundation built with **FastAPI**, **Pydantic**, and in-memory storage.
- **Member 2 (AI & Incident Intelligence):** Anomaly detection, alert correlation, and root-cause engine.
- **Member 3 (Dashboard & UI):** Streamlit dashboard querying live metrics, alerts, health status, and egress proof.

---

## Project Structure

```text
cicada/
│
├── collector/
│   ├── __init__.py
│   ├── generator.py             # Multi-node synthetic telemetry & incident injector
│   ├── privacy.py               # Deep secret redaction & hostname pseudonymizer
│   ├── policy.py                # Strict allow-list policy gate & validation
│   ├── buffer.py                # Offline FIFO buffer with duplicate prevention
│   ├── egress_audit.py          # Egress audit logger & transmission proof
│   └── collector.py            # Local agent coordinator & CLI entrypoint
│
├── shared/
│   ├── __init__.py
│   ├── models.py                # Shared Pydantic data contracts (TelemetryPayload, BasicAlert)
│   └── constants.py             # Thresholds, health states, default servers, allow-list
│
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point & CORS configuration
│   ├── schemas.py               # Pydantic schemas for telemetry, alerts, and responses
│   ├── storage.py               # Thread-safe in-memory store (modular for SQLite in Phase 4)
│   ├── services/
│   │   ├── __init__.py
│   │   └── alert_service.py     # Threshold-based alerting and health scoring logic
│   └── routes/
│       ├── __init__.py
│       ├── telemetry.py         # Telemetry ingest and query endpoints
│       ├── health.py            # Health check and fleet summary endpoints
│       └── alerts.py           # Alert retrieval endpoints
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py              # FastAPI endpoints & validation tests (14 tests)
│   ├── test_privacy.py          # Secret redaction & pseudonymization tests (9 tests)
│   ├── test_policy.py           # Allow-list policy gate & boundary tests (5 tests)
│   ├── test_generator.py        # Telemetry generator & incident simulation tests (7 tests)
│   ├── test_buffer.py           # Offline buffer & egress audit tests (4 tests)
│   └── test_collector.py       # End-to-end integration & demo workflow tests (5 tests)
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Installation & Setup (Windows)

### 1. Prerequisites
- Python 3.11+ (Python 3.13 supported)
- pip

### 2. Install Dependencies
Open PowerShell or Command Prompt in the repository root (`D:\cicada hackathon`):

```powershell
pip install -r requirements.txt
```

---

## Running the Backend

Start the FastAPI development server with automatic reload:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Once running:
- **API Base URL:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## API Endpoints Reference

| Method | Endpoint | Description | Consumed By |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Root service info and operational status | Health check |
| `GET` | `/api/v1/health` | Backend status, total telemetry count, and alert counts | Dashboard / Monitoring |
| `POST` | `/api/v1/telemetry` | Validate, store telemetry & evaluate threshold alerts | Member 1 (Collector) |
| `GET` | `/api/v1/telemetry` | Retrieve recent telemetry (optional `source_id`, `limit`) | Dashboard / AI |
| `GET` | `/api/v1/telemetry/latest` | Retrieve latest telemetry across fleet or by `source_id` | Dashboard |
| `GET` | `/api/v1/telemetry/{source_id}` | Retrieve telemetry records for a specific host/node | Dashboard |
| `GET` | `/api/v1/alerts` | Retrieve generated alerts (optional `source_id`, `limit`) | Dashboard / AI |
| `GET` | `/api/v1/alerts/latest` | Retrieve the single most recent alert | Dashboard |
| `GET` | `/api/v1/alerts/{source_id}` | Retrieve all alerts for a specific node | Dashboard |
| `GET` | `/api/v1/metrics/summary` | Fleet summary: total sources, healthy/warning/critical | Member 3 (Dashboard) |

---

## Shared Telemetry Schema

Every member agrees on this JSON contract:

```json
{
  "payload_id": "evt_0001",
  "tenant_id": "tenant_demo",
  "source_id": "node_a81f",
  "timestamp_utc": "2026-11-20T16:00:00Z",
  "cpu": 76.4,
  "memory": 83.2,
  "disk": 64.0,
  "latency_ms": 240.0,
  "packet_loss_pct": 2.5,
  "error_count": 12,
  "failed_logins": 1,
  "collector_status": "online",
  "event_category": "resource_pressure"
}
```

### Validation Constraints:
- `cpu`, `memory`, `disk`: Float between `0.0` and `100.0`.
- `packet_loss_pct`: Float between `0.0` and `100.0`.
- `latency_ms`: Float non-negative (`>= 0.0`).
- `error_count`, `failed_logins`: Integer non-negative (`>= 0`).
- `payload_id`, `tenant_id`, `source_id`, `collector_status`: Non-empty strings.
- `timestamp_utc`: Valid ISO-8601 datetime.

---

## Example Requests

### 1. Send Normal Telemetry (No Alerts)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "payload_id": "evt_norm_01",
    "tenant_id": "tenant_demo",
    "source_id": "node_web_01",
    "timestamp_utc": "2026-11-20T16:00:00Z",
    "cpu": 35.5,
    "memory": 48.0,
    "disk": 52.0,
    "latency_ms": 28.0,
    "packet_loss_pct": 0.0,
    "error_count": 0,
    "failed_logins": 0,
    "collector_status": "online",
    "event_category": "normal"
  }'
```

**Response (HTTP 201):**
```json
{
  "success": true,
  "message": "Telemetry received successfully",
  "payload_id": "evt_norm_01",
  "alerts_generated": 0,
  "alerts": []
}
```

---

### 2. Send Critical Telemetry (Triggers Alerts)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "payload_id": "evt_spike_01",
    "tenant_id": "tenant_demo",
    "source_id": "node_db_01",
    "timestamp_utc": "2026-11-20T16:05:00Z",
    "cpu": 97.2,
    "memory": 94.5,
    "disk": 68.0,
    "latency_ms": 310.0,
    "packet_loss_pct": 7.5,
    "error_count": 25,
    "failed_logins": 6,
    "collector_status": "online",
    "event_category": "incident_spike"
  }'
```

**Response (HTTP 201):**
```json
{
  "success": true,
  "message": "Telemetry received successfully",
  "payload_id": "evt_spike_01",
  "alerts_generated": 6,
  "alerts": [
    {
      "alert_id": "alt_1a2b3c4d",
      "payload_id": "evt_spike_01",
      "source_id": "node_db_01",
      "alert_type": "HIGH_CPU",
      "severity": "CRITICAL",
      "message": "CPU utilization at 97.2% exceeds threshold of 90.0%",
      "metric_value": 97.2,
      "threshold": 90.0,
      "timestamp_utc": "2026-11-20T16:05:01Z"
    }
  ]
}
```

---

### 3. Fetch Fleet Summary

```bash
curl "http://127.0.0.1:8000/api/v1/metrics/summary"
```

**Response (HTTP 200):**
```json
{
  "success": true,
  "message": "Fleet metrics summary calculated successfully",
  "data": {
    "total_sources": 2,
    "total_telemetry_events": 2,
    "healthy_sources": 1,
    "warning_sources": 0,
    "critical_sources": 1,
    "active_alert_count": 6
  }
}
```

---

## Running Member 1: Local Collector & Privacy Engine

The collector agent generates multi-node telemetry, performs privacy sanitization and pseudonymization, applies the allow-list policy gate, and delivers safe payloads to the backend API.

### 1. Run Full Phase 1 Demo Flow
Generates normal baseline telemetry for all 3 simulated servers (`node_a81f`, `node_b92c`, `node_c73d`), injects a simulated failure on `node_a81f`, and displays backend alerts:

```powershell
python -m collector.collector --mode demo-phase1
```

### 2. Run Privacy Engine & Egress Proof Demo
Simulates a raw local event containing fake sensitive secrets (passwords, bearer tokens, API keys, real internal hostnames) and proves that secrets are redacted, unapproved fields stripped, and hostnames pseudonymized before leaving the node:

```powershell
python -m collector.collector --mode demo-privacy
```

### 3. Send Normal Fleet Telemetry
```powershell
python -m collector.collector --mode normal
```

### 4. Inject Failure Scenario
Inject specific simulated failures onto any node:
```powershell
# CPU spike on node_a81f
python -m collector.collector --mode failure --source node_a81f --scenario cpu_spike

# Memory leak on node_b92c
python -m collector.collector --mode failure --source node_b92c --scenario memory_leak

# Network degradation on node_c73d
python -m collector.collector --mode failure --source node_c73d --scenario network_degradation

# Full critical cascade failure
python -m collector.collector --mode failure --source node_a81f --scenario cascade_failure
```

### 5. Flush Local Offline Buffer
Drain any locally buffered telemetry events when connectivity to backend is restored:
```powershell
python -m collector.collector --mode flush
```

---

## Running the Automated Tests

The complete SentinelOps AI test suite runs with `pytest`:

```powershell
python -m pytest -v
```

All 44 automated tests verify:
- **Backend & API (`tests/test_api.py`, 14 tests):** Root, health, valid ingest, validation rejection (CPU, memory, packet loss, negative latency, empty IDs), ordering, alert engine, and fleet summary.
- **Privacy Engine (`tests/test_privacy.py`, 9 tests):** Host pseudonymization (deterministic mapping & hash), bearer token redaction, API key redaction, database URL password redaction, private key masking, dictionary scrubbing.
- **Allow-List Policy Gate (`tests/test_policy.py`, 5 tests):** Telemetry field allow-listing, stripping unapproved fields (raw logs, emails, passwords), required field enforcement, bounds checking.
- **Telemetry Generator (`tests/test_generator.py`, 7 tests):** 3-node fleet normal metrics, CPU spike, memory leak, network degradation, cascade failure, raw event generator with embedded secrets.
- **Offline Buffer & Audit (`tests/test_buffer.py`, 4 tests):** Enqueue, deduplication, retry handling, status transitions (pending -> sent/failed), egress audit proof generation.
- **End-to-End Integration (`tests/test_collector.py`, 5 tests):** Full privacy pipeline -> backend API ingest -> alert generation -> egress audit verification -> offline buffering upon outage -> recovery buffer flush.
