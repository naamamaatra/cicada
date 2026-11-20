"""
SentinelOps AI - Live Privacy Lab API Routes.
Directly connects to Member 1's real PrivacyEngine, Pseudonymizer, and AllowListPolicy.
Provides live interactive inspection of raw vs sanitized payloads for egress proof.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Body, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import AuditLog, User
from backend.core.dependencies import get_current_user, oauth2_scheme
from collector.privacy import PrivacyEngine, Pseudonymizer
from collector.policy import AllowListPolicy


router = APIRouter(prefix="/api/v1/privacy", tags=["Privacy Lab"])

# Singleton engine instances
_pseudonymizer = Pseudonymizer()
_privacy_engine = PrivacyEngine(_pseudonymizer)
_allow_list_policy = AllowListPolicy()


class PrivacyInspectRequest(BaseModel):
    sample_data: Dict[str, Any] = Field(
        ...,
        description="Raw sample telemetry or log event containing test credentials, internal hostnames, and metrics",
    )


class FieldMapping(BaseModel):
    field: str
    original_value: Any
    action: str  # REDACTED, PSEUDONYMIZED, ALLOWED, BLOCKED
    final_value: Optional[Any] = None
    reason: str


class PrivacyInspectResponse(BaseModel):
    success: bool = True
    policy_verdict: str  # PASS, BLOCKED
    raw_input: Dict[str, Any]
    sanitized_output: Dict[str, Any]
    detected_sensitive_fields: List[str]
    pseudonymized_mappings: List[Dict[str, str]]
    allowed_fields: List[str]
    blocked_fields: List[str]
    field_actions: List[FieldMapping]
    statistics: Dict[str, int]
    explanation: str


@router.post(
    "/inspect",
    response_model=PrivacyInspectResponse,
    status_code=status.HTTP_200_OK,
    summary="Live Privacy & Allow-List Inspection",
    description=(
        "Executes the real Python PrivacyEngine and AllowListPolicy on raw input. "
        "Provides exact egress proof: secret redaction, host pseudonymization, and unauthorized field blocking."
    ),
)
def inspect_privacy(
    payload: PrivacyInspectRequest = Body(...),
    db: Session = Depends(get_db),
) -> PrivacyInspectResponse:
    raw_data = payload.sample_data

    # 1. Real Privacy Engine & Pseudonymization
    redacted_payload, redaction_tags = _privacy_engine.process_raw_telemetry(raw_data)

    # Track pseudonymization mappings
    pseudo_mappings: List[Dict[str, str]] = []
    for host_key in ["hostname", "host", "node_name", "server"]:
        if host_key in raw_data:
            orig = str(raw_data[host_key])
            pseudo_id = _pseudonymizer.pseudonymize(orig)
            pseudo_mappings.append({"original": orig, "pseudonym": pseudo_id})

    # 2. Real Allow-List Policy Gate
    policy_result = _allow_list_policy.evaluate(redacted_payload)
    safe_outbound = policy_result.sanitized_payload or {}

    verdict = "PASS" if policy_result.allowed else "BLOCKED"

    # 3. Build step-by-step field actions
    field_actions: List[FieldMapping] = []
    for key, orig_val in raw_data.items():
        if key in policy_result.blocked_fields:
            if any(key in tag for tag in redaction_tags) or _privacy_engine.is_sensitive_key(key):
                action = "REDACTED & BLOCKED"
                reason = "Detected sensitive credential/secret; stripped by Allow-List policy."
            else:
                action = "BLOCKED"
                reason = "Unauthorized metadata field not in strict allow-list."
            field_actions.append(
                FieldMapping(
                    field=key,
                    original_value="[PROTECTED_PREVIEW]" if _privacy_engine.is_sensitive_key(key) else orig_val,
                    action=action,
                    final_value=None,
                    reason=reason,
                )
            )
        elif key in policy_result.allowed_fields:
            field_actions.append(
                FieldMapping(
                    field=key,
                    original_value=orig_val,
                    action="ALLOWED",
                    final_value=safe_outbound.get(key),
                    reason="Approved telemetry metric; permitted for egress.",
                )
            )

    stats = {
        "total_fields": len(raw_data),
        "secrets_redacted": len(redaction_tags),
        "fields_blocked": len(policy_result.blocked_fields),
        "fields_allowed": len(policy_result.allowed_fields),
        "hostnames_pseudonymized": len(pseudo_mappings),
    }

    explanation = (
        f"Privacy scan analyzed {len(raw_data)} fields: {len(redaction_tags)} sensitive secrets were redacted, "
        f"{len(pseudo_mappings)} internal hostnames pseudonymized, and {len(policy_result.blocked_fields)} unauthorized "
        f"fields blocked. Egress verdict: {verdict}."
    )

    # 4. Safe Audit Logging (Never store unredacted secrets!)
    try:
        audit = AuditLog(
            action="privacy.inspection_executed",
            resource_type="privacy_lab",
            safe_metadata={
                "fields_analyzed": stats["total_fields"],
                "secrets_redacted_count": stats["secrets_redacted"],
                "fields_blocked_count": stats["fields_blocked"],
                "policy_verdict": verdict,
            },
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()

    return PrivacyInspectResponse(
        success=True,
        policy_verdict=verdict,
        raw_input=raw_data,
        sanitized_output=safe_outbound,
        detected_sensitive_fields=redaction_tags,
        pseudonymized_mappings=pseudo_mappings,
        allowed_fields=policy_result.allowed_fields,
        blocked_fields=policy_result.blocked_fields,
        field_actions=field_actions,
        statistics=stats,
        explanation=explanation,
    )
