"""
SentinelOps AI - Authentication API Routes.
Provides User Registration, Login, and Profile endpoints with JWT.
"""

import uuid
import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import User, Organization, Membership, AuditLog
from backend.core.security import hash_password, verify_password, create_access_token
from backend.core.dependencies import get_current_user
from backend.schemas_saas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    UserProfileResponse,
    OrgSummary,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def generate_slug(name: str) -> str:
    """Generate a clean URL-friendly slug with unique random suffix."""
    base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not base_slug:
        base_slug = "org"
    return f"{base_slug}-{uuid.uuid4().hex[:6]}"


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User & Workspace",
    description="Create a new user account, an initial tenant organization, and return JWT token.",
)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    # 1. Check duplicate email
    existing_user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # 2. Hash password & create User
    hashed_pw = hash_password(payload.password)
    user = User(
        email=payload.email,
        password_hash=hashed_pw,
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    db.flush()  # Populates user.id

    # 3. Create default Organization
    org_name = payload.organization_name.strip() if payload.organization_name else "My Organization"
    org_slug = generate_slug(org_name)
    org = Organization(
        name=org_name,
        slug=org_slug,
    )
    db.add(org)
    db.flush()  # Populates org.id

    # 4. Create Owner Membership
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role="owner",
    )
    db.add(membership)

    # 5. Record Audit Log
    audit = AuditLog(
        organization_id=org.id,
        actor_user_id=user.id,
        action="user.signup",
        resource_type="user",
        resource_id=user.id,
        safe_metadata={"email": user.email, "org_name": org.name},
    )
    db.add(audit)

    db.commit()
    db.refresh(user)

    # 6. Issue JWT access token
    token = create_access_token({"sub": user.id, "org_id": org.id})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
        active_organization_id=org.id,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticate with email and password to receive a JWT access token.",
)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    # 1. Fetch user by email
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated",
        )

    # 2. Fetch user's organizations
    memberships = db.execute(
        select(Membership).where(Membership.user_id == user.id)
    ).scalars().all()

    active_org_id = memberships[0].organization_id if memberships else ""

    # 3. Create access token
    token = create_access_token({"sub": user.id, "org_id": active_org_id})

    # 4. Audit Log
    audit = AuditLog(
        organization_id=active_org_id if active_org_id else None,
        actor_user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=user.id,
        safe_metadata={"email": user.email},
    )
    db.add(audit)
    db.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
        active_organization_id=active_org_id,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Current User Profile",
    description="Retrieve profile and organization memberships for the authenticated user.",
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    # Retrieve user memberships with organizations
    memberships = db.execute(
        select(Membership, Organization)
        .join(Organization, Membership.organization_id == Organization.id)
        .where(Membership.user_id == current_user.id)
    ).all()

    org_summaries = [
        OrgSummary(
            id=org.id,
            name=org.name,
            slug=org.slug,
            role=mem.role,
            created_at=org.created_at,
        )
        for mem, org in memberships
    ]

    return UserProfileResponse(
        user=UserResponse(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
        ),
        organizations=org_summaries,
    )

