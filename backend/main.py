"""
SentinelOps AI - Main FastAPI Application.
SaaS Foundation with Multi-Tenancy, JWT Authentication, and Collector Management.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.db.session import init_db
from backend.routes.telemetry import router as telemetry_router
from backend.routes.alerts import router as alerts_router
from backend.routes.health import router as health_router
from backend.routes.auth import router as auth_router
from backend.routes.orgs import router as orgs_router
from backend.routes.collectors import router as collectors_router
from backend.routes.incidents import router as incidents_router
from backend.routes.privacy import router as privacy_router
from backend.routes.metrics import router as metrics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI application."""
    print("=" * 60)
    print("🚀 SentinelOps AI SaaS Backend starting...")
    print("🗄️ Initializing database tables...")
    init_db()
    print("📦 Multi-Tenant SaaS Foundation & Collector Auth ready.")
    print("🔌 CORS configured for local Streamlit dashboard integration.")
    print("=" * 60)
    yield
    print("🛑 SentinelOps AI Backend shutting down.")


app = FastAPI(
    title="SentinelOps AI - SaaS Platform API",
    version="2.0.0",
    description=(
        "Privacy-First AI Infrastructure Monitoring & Autonomous Incident Intelligence Platform. "
        "Multi-Tenant SaaS Foundation, Collector Authentication, and Telemetry Engine."
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
            "message": "Validation failed. Payload rejected.",
            "errors": errors,
        },
    )


# -----------------------------------------------------------------------------
# Route Registration
# -----------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(orgs_router)
app.include_router(collectors_router)
app.include_router(incidents_router)
app.include_router(metrics_router)
app.include_router(privacy_router)
app.include_router(telemetry_router)
app.include_router(alerts_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
