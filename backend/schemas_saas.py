"""
SentinelOps AI - Pydantic Schemas for SaaS Multi-Tenant Platform.
Covers Authentication, Organization Management, and Collector Registration.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
import re


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRegisterRequest(BaseModel):
    """Payload for new user registration."""
    email: str = Field(..., description="User's unique email address")
    password: str = Field(..., min_length=8, description="Password with minimum 8 characters")
    full_name: str = Field(..., min_length=1, description="Full name of user")
    organization_name: Optional[str] = Field(
        default="My Organization",
        description="Name of initial organization to create",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email address format")
        return cleaned

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Full name cannot be empty")
        return cleaned


class UserLoginRequest(BaseModel):
    """Payload for user login."""
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="Account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError("Invalid email address format")
        return cleaned


class UserResponse(BaseModel):
    """Public user profile information."""
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class OrgSummary(BaseModel):
    """Summary of an organization for user profile."""
    id: str
    name: str
    slug: str
    role: str
    created_at: datetime


class UserProfileResponse(BaseModel):
    """Detailed profile including all organization memberships."""
    user: UserResponse
    organizations: List[OrgSummary] = []


class TokenResponse(BaseModel):
    """JWT Token authentication response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    active_organization_id: str


class OrganizationCreateRequest(BaseModel):
    """Payload for creating a new tenant organization."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Organization name cannot be empty")
        return v


class OrganizationResponse(BaseModel):
    """Organization details with membership role and counts."""
    id: str
    name: str
    slug: str
    role: str
    created_at: datetime
    collector_count: int = 0
    incident_count: int = 0


class CollectorCreateRequest(BaseModel):
    """Payload to register a new collector agent."""
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the collector node")

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Collector name cannot be empty")
        return v


class CollectorCreateResponse(BaseModel):
    """
    Response when collector is created.
    raw_token is returned ONCE and must be saved by operator.
    """
    id: str
    name: str
    organization_id: str
    raw_token: str
    status: str
    created_at: datetime
    instructions: str = (
        "Keep raw_token secure! Provide it to the collector via environment variable "
        "SENTINEL_COLLECTOR_TOKEN or in the X-Collector-Token HTTP header."
    )


class CollectorResponse(BaseModel):
    """Public collector metadata (never exposes tokens or hashes)."""
    id: str
    name: str
    organization_id: str
    status: str
    last_seen: Optional[datetime] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None
