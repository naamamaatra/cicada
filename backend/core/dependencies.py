"""
SentinelOps AI - FastAPI Authentication & RBAC Dependencies.
Enforces user authentication, role-based access control, and strict tenant isolation.
"""

from typing import Optional, List, Callable
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
import jwt

from backend.db.session import get_db
from backend.db.models import User, Organization, Membership, Collector
from backend.core.security import decode_access_token, hash_collector_token

# Bearer security scheme for OpenAPI docs
oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts and verifies JWT token from Authorization header.
    Returns authenticated and active User model.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing subject identifier",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or corrupted authentication token",
        )

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token no longer exists",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def get_tenant_membership(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Membership:
    """
    Enforces Strict Tenant Isolation:
    Verifies that the authenticated user holds an active membership in org_id.
    Prevents cross-tenant access.
    """
    membership = db.execute(
        select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You do not have access to organization '{org_id}'",
        )

    return membership


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Factory dependency ensuring user's role in the organization meets requirements.
    Allowed roles: 'owner', 'admin', 'member', 'viewer'
    """
    def role_checker(membership: Membership = Depends(get_tenant_membership)) -> Membership:
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions: Requires one of {allowed_roles}, "
                    f"but your role is '{membership.role}'"
                ),
            )
        return membership

    return role_checker


async def get_authenticated_collector(
    authorization: Optional[str] = Header(None),
    x_collector_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[Collector]:
    """
    Authenticates a collector agent using its pre-shared token.
    Token can be provided via:
    - Authorization: Bearer <raw_token>
    - X-Collector-Token: <raw_token>
    Returns active Collector model or None if unauthenticated.
    """
    raw_token: Optional[str] = None
    if x_collector_token:
        raw_token = x_collector_token.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()

    if not raw_token:
        return None

    # Compute SHA-256 hash to compare against stored hash
    token_hash = hash_collector_token(raw_token)
    collector = db.execute(
        select(Collector).where(
            Collector.token_hash == token_hash,
            Collector.status != "revoked",
            Collector.revoked_at.is_(None),
        )
    ).scalar_one_or_none()

    if not collector:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, unknown, or revoked collector credentials",
        )

    # Touch last_seen timestamp
    collector.last_seen = datetime.now(timezone.utc)
    collector.status = "online"
    db.commit()

    return collector
