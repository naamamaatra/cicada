"""
SentinelOps AI - Database & SaaS Foundation Test Suite (Milestone 2).
Verifies:
- Schema initialization
- CRUD on Users, Organizations, Memberships, Collectors, Telemetry, Incidents, Audit Logs
- Unique constraints and deduplication (payload_id, email, slug, user-org membership)
- Role validation
- Foreign key enforcement
- Relationship cascades and navigation
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.db.base import Base
from backend.db.models import (
    User,
    Organization,
    Membership,
    Collector,
    TelemetryRecord,
    Incident,
    AuditLog,
)


@pytest.fixture
def db_session():
    """
    Creates an isolated in-memory SQLite database for each test,
    with foreign keys explicitly enabled.
    """
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


# -----------------------------------------------------------------------------
# 1. Database Initialization
# -----------------------------------------------------------------------------
def test_database_initialization(db_session):
    """Verify all 7 tables are created and operational."""
    assert db_session is not None
    # Verify tables can be queried
    assert db_session.execute(select(User)).scalars().all() == []
    assert db_session.execute(select(Organization)).scalars().all() == []
    assert db_session.execute(select(Membership)).scalars().all() == []
    assert db_session.execute(select(Collector)).scalars().all() == []
    assert db_session.execute(select(TelemetryRecord)).scalars().all() == []
    assert db_session.execute(select(Incident)).scalars().all() == []
    assert db_session.execute(select(AuditLog)).scalars().all() == []


# -----------------------------------------------------------------------------
# 2. User Creation & Retrieval
# -----------------------------------------------------------------------------
def test_create_and_retrieve_user(db_session):
    user = User(
        email="operator@sentinelops.ai",
        password_hash="argon2_or_bcrypt_hashed_string",
        full_name="Alex Sentinel",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    retrieved = db_session.execute(
        select(User).where(User.email == "operator@sentinelops.ai")
    ).scalar_one()

    assert retrieved.id.startswith("usr_")
    assert retrieved.full_name == "Alex Sentinel"
    assert retrieved.is_active is True
    assert retrieved.created_at is not None


def test_unique_email_constraint(db_session):
    u1 = User(email="test@domain.com", password_hash="hash1", full_name="User One")
    u2 = User(email="test@domain.com", password_hash="hash2", full_name="User Two")
    db_session.add(u1)
    db_session.commit()

    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 3. Organization Creation & Slug Uniqueness
# -----------------------------------------------------------------------------
def test_create_organization(db_session):
    org = Organization(name="Acme Corp", slug="acme-corp")
    db_session.add(org)
    db_session.commit()

    retrieved = db_session.execute(
        select(Organization).where(Organization.slug == "acme-corp")
    ).scalar_one()

    assert retrieved.id.startswith("org_")
    assert retrieved.name == "Acme Corp"
    assert retrieved.created_at is not None


def test_unique_organization_slug(db_session):
    org1 = Organization(name="Acme 1", slug="acme")
    org2 = Organization(name="Acme 2", slug="acme")
    db_session.add(org1)
    db_session.commit()

    db_session.add(org2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 4. Membership Creation & RBAC Validation
# -----------------------------------------------------------------------------
def test_membership_and_roles(db_session):
    org = Organization(name="DevOrg", slug="dev-org")
    db_session.add(org)
    db_session.commit()

    for role in ["owner", "admin", "member", "viewer"]:
        u = User(email=f"user_{role}@org.com", password_hash="hash", full_name=f"{role.capitalize()} User")
        db_session.add(u)
        db_session.commit()
        mem = Membership(user_id=u.id, organization_id=org.id, role=role)
        db_session.add(mem)
        db_session.commit()
        assert mem.role == role


def test_unique_user_organization_membership(db_session):
    user = User(email="u@org.com", password_hash="hash", full_name="User")
    org = Organization(name="Org", slug="org")
    db_session.add_all([user, org])
    db_session.commit()

    m1 = Membership(user_id=user.id, organization_id=org.id, role="owner")
    m2 = Membership(user_id=user.id, organization_id=org.id, role="admin")
    db_session.add(m1)
    db_session.commit()

    db_session.add(m2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_invalid_membership_role_rejected(db_session):
    user = User(email="bad@role.com", password_hash="hash", full_name="Bad Role User")
    org = Organization(name="Org2", slug="org2")
    db_session.add_all([user, org])
    db_session.commit()

    bad_membership = Membership(user_id=user.id, organization_id=org.id, role="superadmin_invalid")
    db_session.add(bad_membership)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 5. Collector Registration Records
# -----------------------------------------------------------------------------
def test_collector_registration(db_session):
    org = Organization(name="CloudOps", slug="cloud-ops")
    db_session.add(org)
    db_session.commit()

    collector = Collector(
        organization_id=org.id,
        name="edge-node-01",
        status="registered",
        token_hash="sha256_hashed_token_string",
    )
    db_session.add(collector)
    db_session.commit()

    assert collector.id.startswith("col_")
    assert collector.organization_id == org.id
    assert collector.status == "registered"
    assert collector.last_seen is None
    assert collector.revoked_at is None


# -----------------------------------------------------------------------------
# 6. Telemetry Persistence & Idempotency / Deduplication
# -----------------------------------------------------------------------------
def test_telemetry_persistence(db_session):
    org = Organization(name="OpsOrg", slug="ops-org")
    db_session.add(org)
    db_session.commit()

    collector = Collector(
        organization_id=org.id,
        name="agent-prod",
        token_hash="hash",
    )
    db_session.add(collector)
    db_session.commit()

    now = datetime.now(timezone.utc)
    record = TelemetryRecord(
        payload_id="evt_unique_1001",
        organization_id=org.id,
        collector_id=collector.id,
        source_id="node_a81f",
        timestamp_utc=now,
        cpu=76.4,
        memory=83.2,
        disk=64.0,
        latency_ms=240.0,
        packet_loss_pct=2.5,
        error_count=12,
        failed_logins=1,
        collector_status="online",
        event_category="resource_pressure",
    )
    db_session.add(record)
    db_session.commit()

    retrieved = db_session.execute(
        select(TelemetryRecord).where(TelemetryRecord.payload_id == "evt_unique_1001")
    ).scalar_one()

    assert retrieved.id.startswith("tel_")
    assert retrieved.cpu == 76.4
    assert retrieved.memory == 83.2
    assert retrieved.source_id == "node_a81f"
    assert retrieved.collector_id == collector.id


def test_telemetry_payload_id_deduplication(db_session):
    org = Organization(name="DedupeOrg", slug="dedupe-org")
    db_session.add(org)
    db_session.commit()

    now = datetime.now(timezone.utc)
    r1 = TelemetryRecord(
        payload_id="evt_duplicate_check",
        organization_id=org.id,
        source_id="node_1",
        timestamp_utc=now,
        cpu=50.0,
        memory=50.0,
        disk=50.0,
        latency_ms=20.0,
        packet_loss_pct=0.0,
    )
    r2 = TelemetryRecord(
        payload_id="evt_duplicate_check",
        organization_id=org.id,
        source_id="node_1",
        timestamp_utc=now,
        cpu=60.0,
        memory=60.0,
        disk=60.0,
        latency_ms=30.0,
        packet_loss_pct=0.0,
    )
    db_session.add(r1)
    db_session.commit()

    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 7. Incident Creation & Status Workflow
# -----------------------------------------------------------------------------
def test_incident_creation_and_status(db_session):
    org = Organization(name="IncidentOrg", slug="incident-org")
    db_session.add(org)
    db_session.commit()

    incident = Incident(
        organization_id=org.id,
        title="High CPU & Latency Spike on Node A",
        description="Observed CPU at 98% and network degradation.",
        severity="CRITICAL",
        status="open",
        source_id="node_a81f",
    )
    db_session.add(incident)
    db_session.commit()

    assert incident.id.startswith("inc_")
    assert incident.status == "open"
    assert incident.severity == "CRITICAL"

    # Status transition
    incident.status = "investigating"
    db_session.commit()
    assert incident.status == "investigating"

    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)
    db_session.commit()
    assert incident.status == "resolved"


def test_invalid_incident_status_rejected(db_session):
    org = Organization(name="IncidentOrg2", slug="incident-org2")
    db_session.add(org)
    db_session.commit()

    bad_incident = Incident(
        organization_id=org.id,
        title="Invalid status incident",
        severity="HIGH",
        status="unknown_status",
    )
    db_session.add(bad_incident)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 8. Audit Log Creation
# -----------------------------------------------------------------------------
def test_audit_log_creation(db_session):
    org = Organization(name="AuditOrg", slug="audit-org")
    user = User(email="auditor@sec.com", password_hash="hash", full_name="Security Auditor")
    db_session.add_all([org, user])
    db_session.commit()

    log_entry = AuditLog(
        organization_id=org.id,
        actor_user_id=user.id,
        action="collector.enrollment_generated",
        resource_type="collector",
        resource_id="col_xyz123",
        safe_metadata={"collector_name": "db-server-01", "ip": "10.0.0.1"},
    )
    db_session.add(log_entry)
    db_session.commit()

    assert log_entry.id.startswith("aud_")
    assert log_entry.safe_metadata["collector_name"] == "db-server-01"
    assert log_entry.actor_user_id == user.id


# -----------------------------------------------------------------------------
# 9. Foreign Key Enforcement
# -----------------------------------------------------------------------------
def test_foreign_key_enforcement(db_session):
    """Attempt to insert child records referencing non-existent parent IDs."""
    fake_org_id = "org_nonexistent"

    # 1. Collector referencing fake org
    bad_col = Collector(organization_id=fake_org_id, name="bad-agent", token_hash="hash")
    db_session.add(bad_col)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 2. Telemetry referencing fake org
    bad_tel = TelemetryRecord(
        payload_id="evt_fake_fk",
        organization_id=fake_org_id,
        source_id="node_1",
        timestamp_utc=datetime.now(timezone.utc),
        cpu=10.0,
        memory=10.0,
        disk=10.0,
        latency_ms=10.0,
        packet_loss_pct=0.0,
    )
    db_session.add(bad_tel)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 10. Organization Relationship Cascades
# -----------------------------------------------------------------------------
def test_organization_cascade_delete(db_session):
    """Deleting an organization should cascade delete memberships, collectors, telemetry, incidents."""
    org = Organization(name="CascadeOrg", slug="cascade-org")
    user = User(email="casc@org.com", password_hash="hash", full_name="User")
    db_session.add_all([org, user])
    db_session.commit()

    mem = Membership(user_id=user.id, organization_id=org.id, role="owner")
    col = Collector(organization_id=org.id, name="col-1", token_hash="h1")
    inc = Incident(organization_id=org.id, title="Inc-1", severity="LOW", status="open")
    db_session.add_all([mem, col, inc])
    db_session.commit()

    # Delete organization
    db_session.delete(org)
    db_session.commit()

    # Assert children are cascade deleted
    assert db_session.execute(select(Membership).where(Membership.organization_id == org.id)).scalars().all() == []
    assert db_session.execute(select(Collector).where(Collector.organization_id == org.id)).scalars().all() == []
    assert db_session.execute(select(Incident).where(Incident.organization_id == org.id)).scalars().all() == []
    # User itself remains
    assert db_session.execute(select(User).where(User.id == user.id)).scalars().first() is not None
