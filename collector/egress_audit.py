"""
SentinelOps AI - Egress Audit & Transmission Proof Logger.
Member 1: Collector & Privacy Engine.

Responsibilities:
1. Maintain auditable evidence of every outbound data transmission attempt.
2. Record original local event summary (for local proof only), safe payload, allowed/blocked fields.
3. Track transmission status (SENT, BUFFERED, FAILED, BLOCKED).
4. Provide structured data to power Dashboard Page 5 (Privacy & Egress Proof).
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from threading import Lock
from pydantic import BaseModel, Field


class EgressAuditRecord(BaseModel):
    """
    Immutable proof record of an outbound telemetry transmission.
    """
    audit_id: str = Field(..., description="Unique audit event ID (aud_xxxx)")
    payload_id: str = Field(..., description="Telemetry payload ID")
    source_id: str = Field(..., description="Pseudonymous node/source identifier")
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Audit generation timestamp in UTC",
    )
    raw_event_preview: Dict[str, Any] = Field(
        default_factory=dict,
        description="Local preview of original un-sanitized event (LOCAL ONLY)",
    )
    safe_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The exact sanitized payload authorized for transmission",
    )
    allowed_fields: List[str] = Field(default_factory=list, description="Fields allowed by policy")
    blocked_fields: List[str] = Field(default_factory=list, description="Fields blocked by policy")
    detected_secrets: List[str] = Field(default_factory=list, description="Sensitive items redacted")
    policy_verdict: str = Field(..., description="'PASS' or 'BLOCKED'")
    transmission_status: str = Field(..., description="'SENT', 'BUFFERED', 'FAILED', or 'BLOCKED'")
    destination: str = Field(..., description="Target transmission endpoint")
    error_message: Optional[str] = Field(default=None, description="Transmission error if failed")


class EgressAuditLogger:
    """
    Thread-safe in-memory and queryable Egress Audit trail.
    Ensures verifiable proof of privacy and transmission.
    """

    def __init__(self, max_records: int = 500):
        self._lock = Lock()
        self.max_records = max_records
        self._records: List[EgressAuditRecord] = []
        self._records_by_payload_id: Dict[str, EgressAuditRecord] = {}

    def record(
        self,
        payload_id: str,
        source_id: str,
        policy_verdict: str,
        transmission_status: str,
        destination: str,
        safe_payload: Optional[Dict[str, Any]] = None,
        raw_event_preview: Optional[Dict[str, Any]] = None,
        allowed_fields: Optional[List[str]] = None,
        blocked_fields: Optional[List[str]] = None,
        detected_secrets: Optional[List[str]] = None,
        error_message: Optional[str] = None,
    ) -> EgressAuditRecord:
        """Create and store a new Egress Audit Record."""
        with self._lock:
            audit_id = f"aud_{uuid.uuid4().hex[:8]}"
            record = EgressAuditRecord(
                audit_id=audit_id,
                payload_id=payload_id,
                source_id=source_id,
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                raw_event_preview=raw_event_preview or {},
                safe_payload=safe_payload,
                allowed_fields=allowed_fields or [],
                blocked_fields=blocked_fields or [],
                detected_secrets=detected_secrets or [],
                policy_verdict=policy_verdict,
                transmission_status=transmission_status,
                destination=destination,
                error_message=error_message,
            )

            self._records.append(record)
            self._records_by_payload_id[payload_id] = record

            # Trim old records if max limit reached
            if len(self._records) > self.max_records:
                oldest = self._records.pop(0)
                self._records_by_payload_id.pop(oldest.payload_id, None)

            return record

    def update_transmission_status(
        self,
        payload_id: str,
        new_status: str,
        error_message: Optional[str] = None,
    ) -> Optional[EgressAuditRecord]:
        """Update status of existing record (e.g. from BUFFERED to SENT)."""
        with self._lock:
            record = self._records_by_payload_id.get(payload_id)
            if record:
                record.transmission_status = new_status
                record.error_message = error_message
                return record
            return None

    def get_all(
        self,
        source_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[EgressAuditRecord]:
        """Retrieve audit records newest first."""
        with self._lock:
            records = self._records
            if source_id:
                records = [r for r in records if r.source_id == source_id]
            reversed_records = list(reversed(records))
            if limit and limit > 0:
                return reversed_records[:limit]
            return reversed_records

    def get_latest(self, source_id: Optional[str] = None) -> Optional[EgressAuditRecord]:
        """Retrieve the single most recent egress audit record."""
        with self._lock:
            if not self._records:
                return None
            if source_id:
                for r in reversed(self._records):
                    if r.source_id == source_id:
                        return r
                return None
            return self._records[-1]

    def get_summary_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics on egress audit."""
        with self._lock:
            total = len(self._records)
            sent = sum(1 for r in self._records if r.transmission_status == "SENT")
            buffered = sum(1 for r in self._records if r.transmission_status == "BUFFERED")
            blocked = sum(1 for r in self._records if r.policy_verdict == "BLOCKED")
            failed = sum(1 for r in self._records if r.transmission_status == "FAILED")
            total_secrets_redacted = sum(len(r.detected_secrets) for r in self._records)
            total_unauthorized_fields_blocked = sum(len(r.blocked_fields) for r in self._records)

            return {
                "total_egress_audits": total,
                "sent_count": sent,
                "buffered_count": buffered,
                "blocked_count": blocked,
                "failed_count": failed,
                "total_secrets_redacted": total_secrets_redacted,
                "total_unauthorized_fields_blocked": total_unauthorized_fields_blocked,
            }

    def clear(self) -> None:
        """Clear all audit logs."""
        with self._lock:
            self._records.clear()
            self._records_by_payload_id.clear()
