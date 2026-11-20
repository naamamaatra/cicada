# CICADA — SentinelOps AI

End-to-end, secure AIOps observability delivering autonomous insights across enterprise, data center, cloud, and distributed architectures.

---

## Collaborator Quickstart & Workflow Guidelines

### 1. Clone the repository
```bash
git clone https://github.com/naamamaatra/cicada.git
cd cicada
```

### 2. Workflow Guidelines
To avoid merge conflicts while contributing in parallel:
1. **Always sync with `main` before starting a feature:**
   ```bash
   git checkout main
   git pull origin main
   ```
2. **Create a feature branch:**
   ```bash
   git checkout -b <name>/<feature-name>
   ```
3. **Commit and push your feature branch:**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   git push -u origin <name>/<feature-name>
   ```
4. **Merge to `main` via PR on GitHub** after testing locally.

---

## Team Division & Deliverables (Phase 1)

- **Member 1 (Collector & Privacy Engine):** Local telemetry generator, deep privacy redaction, hostname pseudonymization, allow-list policy gate, offline buffering, and egress audit proof logging.
- **Member 4 (Backend & Integration):** Phase 1 Backend Foundation built with **FastAPI**, **Pydantic**, and in-memory storage.
- **Member 2 (AI & Incident Intelligence):** Anomaly detection, alert correlation, and root-cause engine.
- **Member 3 (Dashboard & UI):** Streamlit dashboard querying live metrics, alerts, health status, and egress proof.

---

## Member 3 — Dashboard & UI (Phase 1)

The **Phase 1 Streamlit Dashboard** is located in `dashboard/`:
- **App entrypoint:** `dashboard/app.py`
- **Component cards:** `dashboard/components/cards.py`
- **Interactive Plotly charts:** `dashboard/components/charts.py`
- **Telemetry simulation & API service:** `dashboard/data_service.py`

Run dashboard locally:
```powershell
streamlit run dashboard/app.py --server.port 8501
```

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
├── dashboard/
│   ├── app.py                  # Streamlit dashboard
│   ├── data_service.py         # Telemetry data engine & fallback service
│   └── components/
│       ├── cards.py            # 4-state health classification engine
│       └── charts.py           # Plotly trend visualizations
│
├── shared/
│   ├── constants.py            # Standard thresholds & server specifications
│   └── models.py               # Shared telemetry payload schemas
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

## Running the Dashboard

Start the Streamlit dashboard:

```powershell
streamlit run dashboard/app.py --server.port 8501
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
