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

## Member 4 — Backend & Integration (Phase 1)

This repository contains the **Phase 1 Backend Foundation**, built with **FastAPI**, **Pydantic**, and a modular in-memory storage layer ready for integration with:
- **Member 1 (Collector & Privacy Engine):** Ingests sanitized telemetry payloads at `POST /api/v1/telemetry`.
- **Member 2 (AI & Incident Intelligence):** Consumes telemetry data and integrates advanced anomaly detection.
- **Member 3 (Dashboard & UI):** Queries live metrics, alerts, health status, and fleet summaries via REST API with pre-configured local CORS.

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
│   └── test_api.py              # Pytest suite covering all validation & endpoints
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

## Running the Automated Tests

The test suite runs with `pytest` using FastAPI's `TestClient`:

```powershell
python -m pytest tests/test_api.py -v
```
