"""
SentinelOps AI - Main FastAPI Application.
Phase 1 Backend Foundation for Member 4: Backend & Integration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.routes.telemetry import router as telemetry_router
from backend.routes.alerts import router as alerts_router
from backend.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI application."""
    print("=" * 60)
    print("🚀 SentinelOps AI Backend starting...")
    print("📦 Phase 1: In-Memory Storage & Threshold Alert Engine ready.")
    print("🔌 CORS configured for local Streamlit dashboard integration.")
    print("=" * 60)
    yield
    print("🛑 SentinelOps AI Backend shutting down.")


app = FastAPI(
    title="SentinelOps AI - Backend API",
    version="1.0.0",
    description=(
        "Privacy-First AI Infrastructure Monitoring & Incident Intelligence Platform. "
        "Phase 1 Ingestion, Validation, In-Memory Storage, and Alerting Engine."
    ),
    lifespan=lifespan,
)

# -----------------------------------------------------------------------------
# CORS Configuration (Strict Local Development Origins)
# -----------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:8501",  # Streamlit default
    "http://127.0.0.1:8501",
    "http://localhost:3000",  # Optional frontend
    "http://127.0.0.1:3000",
    "http://localhost:8000",  # API docs / Swagger
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Custom Validation Error Handler (Clear, Structured Responses)
# -----------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(part) for part in err.get("loc", []))
        errors.append({
            "field": loc,
            "message": err.get("msg"),
            "type": err.get("type"),
        })

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Telemetry validation failed. Payload rejected.",
            "errors": errors,
        },
    )


# -----------------------------------------------------------------------------
# Route Registration
# -----------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(telemetry_router)
app.include_router(alerts_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
