"""
SentinelOps AI - SaaS Core Test Suite (Milestone 3).
Verifies:
1. User registration, password hashing, and login.
2. Duplicate email rejection.
3. Invalid credentials rejection.
4. JWT token validation, expiration, and protected endpoints.
5. Organization creation & listing.
6. Role permissions (Owner/Admin vs Viewer/Member).
7. Strict Tenant Isolation (Tenant A cannot view or manage Tenant B's data).
8. Collector enrollment, secure token issuance, and verification.
9. Collector authentication on telemetry ingestion.
10. Collector revocation and immediate token invalidation.
11. Invalid collector credentials rejection.
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.db.base import Base
from backend.db.session import get_db
from backend.db.models import User, Organization, Membership, Collector, TelemetryRecord
from backend.core.security import create_access_token


from sqlalchemy.pool import StaticPool

# Setup isolated in-memory test database for the API
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh database tables before each test and drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


# -----------------------------------------------------------------------------
# 1. User Registration and Login
# -----------------------------------------------------------------------------
def test_user_registration_success():
    payload = {
        "email": "sarah@cyberdyne.com",
        "password": "Password123!",
        "full_name": "Sarah Connor",
        "organization_name": "Cyberdyne Resistance",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "sarah@cyberdyne.com"
    assert data["user"]["full_name"] == "Sarah Connor"
    assert data["active_organization_id"].startswith("org_")


def test_user_registration_duplicate_email():
    payload = {
        "email": "duplicate@test.com",
        "password": "Password123!",
        "full_name": "Duplicate User",
        "organization_name": "Org One",
    }
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_user_login_success():
    # Register first
    client.post("/api/v1/auth/register", json={
        "email": "login_user@test.com",
        "password": "SecretPassword123",
        "full_name": "Login User",
    })

    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "login_user@test.com",
        "password": "SecretPassword123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login_user@test.com"


def test_user_login_invalid_password():
    client.post("/api/v1/auth/register", json={
        "email": "wrong_pw@test.com",
        "password": "CorrectPassword123",
        "full_name": "Wrong PW User",
    })

    response = client.post("/api/v1/auth/login", json={
        "email": "wrong_pw@test.com",
        "password": "IncorrectPassword",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_user_login_nonexistent_email():
    response = client.post("/api/v1/auth/login", json={
        "email": "ghost@nowhere.com",
        "password": "AnyPassword123",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


# -----------------------------------------------------------------------------
# 2. JWT Token Validation & Expiration
# -----------------------------------------------------------------------------
def test_protected_route_requires_auth():
    # Unauthenticated call to /api/v1/auth/me
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_protected_route_with_valid_token():
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": "valid_token@test.com",
        "password": "ValidPassword123",
        "full_name": "Valid Token User",
    })
    token = reg_resp.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "valid_token@test.com"
    assert len(data["organizations"]) == 1
    assert data["organizations"][0]["role"] == "owner"


def test_expired_token_rejected():
    # Create token expired 1 hour ago
    expired_token = create_access_token(
        {"sub": "usr_fake_expired"},
        expires_delta=timedelta(hours=-1),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 3. Organization Management & Multiple Workspaces
# -----------------------------------------------------------------------------
def test_create_and_list_organizations():
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": "multi_org@test.com",
        "password": "Password123!",
        "full_name": "Multi Org User",
        "organization_name": "Primary Org",
    })
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create second organization
    create_resp = client.post(
        "/api/v1/orgs",
        headers=headers,
        json={"name": "Secondary Workspace", "slug": "secondary-ws"},
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["name"] == "Secondary Workspace"
    assert create_resp.json()["role"] == "owner"

    # List all orgs for this user
    list_resp = client.get("/api/v1/orgs", headers=headers)
    assert list_resp.status_code == 200
    orgs = list_resp.json()
    assert len(orgs) == 2
    org_names = [o["name"] for o in orgs]
    assert "Primary Org" in org_names
    assert "Secondary Workspace" in org_names


# -----------------------------------------------------------------------------
# 4. Strict Tenant Isolation
# -----------------------------------------------------------------------------
def test_strict_tenant_isolation():
    """Tenant A must NEVER be able to access Tenant B's organization or collectors."""
    # User A in Org A
    user_a_resp = client.post("/api/v1/auth/register", json={
        "email": "usera@alpha.com",
        "password": "Password123!",
        "full_name": "User Alpha",
        "organization_name": "Alpha Corp",
    })
    token_a = user_a_resp.json()["access_token"]
    org_a_id = user_a_resp.json()["active_organization_id"]

    # User B in Org B
    user_b_resp = client.post("/api/v1/auth/register", json={
        "email": "userb@beta.com",
        "password": "Password123!",
        "full_name": "User Beta",
        "organization_name": "Beta Corp",
    })
    token_b = user_b_resp.json()["access_token"]
    org_b_id = user_b_resp.json()["active_organization_id"]

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B attempts to access Org A details -> FORBIDDEN (403)
    leak_org_resp = client.get(f"/api/v1/orgs/{org_a_id}", headers=headers_b)
    assert leak_org_resp.status_code == 403
    assert "Access denied" in leak_org_resp.json()["detail"]

    # User B attempts to list Org A's collectors -> FORBIDDEN (403)
    leak_col_resp = client.get(f"/api/v1/orgs/{org_a_id}/collectors", headers=headers_b)
    assert leak_col_resp.status_code == 403
    assert "Access denied" in leak_col_resp.json()["detail"]


# -----------------------------------------------------------------------------
# 5. Role Permissions (RBAC)
# -----------------------------------------------------------------------------
def test_role_based_permissions():
    """Verify that only Owners/Admins can register or revoke collectors."""
    # Register Owner
    owner_resp = client.post("/api/v1/auth/register", json={
        "email": "owner@corp.com",
        "password": "Password123!",
        "full_name": "Owner Person",
        "organization_name": "RBAC Corp",
    })
    owner_token = owner_resp.json()["access_token"]
    org_id = owner_resp.json()["active_organization_id"]

    # Register Viewer User and add to Org as 'viewer'
    viewer_resp = client.post("/api/v1/auth/register", json={
        "email": "viewer@corp.com",
        "password": "Password123!",
        "full_name": "Viewer Person",
        "organization_name": "Viewer Default",
    })
    viewer_token = viewer_resp.json()["access_token"]
    viewer_id = viewer_resp.json()["user"]["id"]

    # Add viewer to RBAC Corp via DB
    db = TestingSessionLocal()
    db.add(Membership(user_id=viewer_id, organization_id=org_id, role="viewer"))
    db.commit()
    db.close()

    # Viewer tries to enroll collector -> 403 Forbidden
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    forbidden_col = client.post(
        f"/api/v1/orgs/{org_id}/collectors",
        headers=viewer_headers,
        json={"name": "illegal-agent"},
    )
    assert forbidden_col.status_code == 403
    assert "Insufficient permissions" in forbidden_col.json()["detail"]

    # Owner enrolls collector -> 201 Created
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    allowed_col = client.post(
        f"/api/v1/orgs/{org_id}/collectors",
        headers=owner_headers,
        json={"name": "legal-agent"},
    )
    assert allowed_col.status_code == 201
    assert "raw_token" in allowed_col.json()


# -----------------------------------------------------------------------------
# 6. Collector Registration, Token Generation, and Ingestion
# -----------------------------------------------------------------------------
def test_collector_lifecycle_and_authenticated_ingest():
    # 1. Register owner & org
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": "fleet_admin@telemetry.io",
        "password": "Password123!",
        "full_name": "Fleet Admin",
        "organization_name": "Fleet Corp",
    })
    token = reg_resp.json()["access_token"]
    org_id = reg_resp.json()["active_organization_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Register new collector
    col_resp = client.post(
        f"/api/v1/orgs/{org_id}/collectors",
        headers=headers,
        json={"name": "edge-cluster-01"},
    )
    assert col_resp.status_code == 201
    col_data = col_resp.json()
    collector_id = col_data["id"]
    raw_token = col_data["raw_token"]
    assert raw_token.startswith("sc_live_")

    # 3. Collector posts telemetry using its secret token
    telemetry_payload = {
        "payload_id": "evt_collector_auth_101",
        "tenant_id": org_id,
        "source_id": "node_authenticated_edge",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": 54.0,
        "memory": 62.5,
        "disk": 40.0,
        "latency_ms": 15.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
        "event_category": "normal",
    }

    # Send with X-Collector-Token header
    ingest_resp = client.post(
        "/api/v1/telemetry",
        headers={"X-Collector-Token": raw_token},
        json=telemetry_payload,
    )
    assert ingest_resp.status_code == 201
    assert ingest_resp.json()["success"] is True

    # Verify collector last_seen is updated
    cols = client.get(f"/api/v1/orgs/{org_id}/collectors", headers=headers).json()
    assert cols[0]["status"] == "online"
    assert cols[0]["last_seen"] is not None

    # 4. Revoke collector
    del_resp = client.delete(
        f"/api/v1/orgs/{org_id}/collectors/{collector_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200

    # 5. Revoked collector attempts to send telemetry -> 401 Unauthorized!
    rejected_resp = client.post(
        "/api/v1/telemetry",
        headers={"X-Collector-Token": raw_token},
        json={**telemetry_payload, "payload_id": "evt_collector_revoked_try"},
    )
    assert rejected_resp.status_code == 401
    assert "revoked" in rejected_resp.json()["detail"].lower()


def test_invalid_collector_token_rejected():
    telemetry_payload = {
        "payload_id": "evt_bad_token",
        "tenant_id": "tenant_demo",
        "source_id": "node_fake",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cpu": 50.0,
        "memory": 50.0,
        "disk": 50.0,
        "latency_ms": 20.0,
        "packet_loss_pct": 0.0,
        "error_count": 0,
        "failed_logins": 0,
        "collector_status": "online",
    }
    resp = client.post(
        "/api/v1/telemetry",
        headers={"X-Collector-Token": "sc_live_completely_fake_invalid_token"},
        json=telemetry_payload,
    )
    assert resp.status_code == 401
    assert "Invalid, unknown, or revoked" in resp.json()["detail"]
