"""
SentinelOps AI - SQLAlchemy Models for Multi-Tenant SaaS.
Defines persistent schema for Users, Organizations, Memberships,
Collectors, Telemetry, Incidents, and Audit Logs.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Boolean,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    JSON,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.db.base import Base


def utc_now() -> datetime:
    """Helper to return current datetime in timezone-aware UTC."""
    return datetime.now(timezone.utc)


def gen_id(prefix: str) -> str:
    """Generate a clean, deterministic-prefixed ID."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# -----------------------------------------------------------------------------
# 1. User Model
# -----------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: gen_id("usr"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="actor"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.id})>"


# -----------------------------------------------------------------------------
# 2. Organization Model (Tenant)
# -----------------------------------------------------------------------------
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: gen_id("org"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="organization", cascade="all, delete-orphan"
    )
    collectors: Mapped[List["Collector"]] = relationship(
        "Collector", back_populates="organization", cascade="all, delete-orphan"
    )
    telemetry_records: Mapped[List["TelemetryRecord"]] = relationship(
        "TelemetryRecord", back_populates="organization", cascade="all, delete-orphan"
    )
    incidents: Mapped[List["Incident"]] = relationship(
        "Incident", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name} ({self.slug})>"


# -----------------------------------------------------------------------------
# 3. Membership Model (User <-> Organization with RBAC)
# -----------------------------------------------------------------------------
class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
        CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="chk_membership_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: gen_id("mem"))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(30), default="member", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<Membership user={self.user_id} org={self.organization_id} role={self.role}>"


# -----------------------------------------------------------------------------
# 4. Collector Model (Agent Identity & Auth)
# -----------------------------------------------------------------------------
class Collector(Base):
    __tablename__ = "collectors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: gen_id("col"))
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="registered", nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Never raw tokens!
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="collectors")
    telemetry_records: Mapped[List["TelemetryRecord"]] = relationship(
        "TelemetryRecord", back_populates="collector"
    )

    def __repr__(self) -> str:
        return f"<Collector {self.name} ({self.id}) status={self.status}>"


# -----------------------------------------------------------------------------
# 5. TelemetryRecord Model (Persistent Ingestion)
# -----------------------------------------------------------------------------
class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: gen_id("tel"))
    payload_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collector_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("collectors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Metrics
    cpu: Mapped[float] = mapped_column(Float, nullable=False)
    memory: Mapped[float] = mapped_column(Float, nullable=False)
    disk: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    packet_loss_pct: Mapped[float] = mapped_column(Float, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collector_status: Mapped[str] = mapped_column(String(50), default="online", nullable=False)
    event_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="telemetry_records")
    collector: Mapped[Optional["Collector"]] = relationship("Collector", back_populates="telemetry_records")

    def __repr__(self) -> str:
        return f"<TelemetryRecord {self.payload_id} source={self.source_id}>"


# -----------------------------------------------------------------------------
# 6. Incident Model (Incident Management Workflow)
# -----------------------------------------------------------------------------
class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'investigating', 'resolved', 'dismissed')",
            name="chk_incident_status",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="chk_incident_severity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: gen_id("inc"))
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="incidents")

    def __repr__(self) -> str:
        return f"<Incident {self.id} status={self.status} severity={self.severity}>"


# -----------------------------------------------------------------------------
# 7. AuditLog Model (Immutable Audit Trail)
# -----------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: gen_id("aud"))
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    safe_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="audit_logs")
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.resource_type}:{self.resource_id}>"

