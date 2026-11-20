"""
SentinelOps AI - Tests for Member 1: Local Buffer & Egress Audit.
"""

import pytest
from collector.buffer import OfflineBuffer
from collector.egress_audit import EgressAuditLogger


def test_buffer_enqueue_and_pending():
    buf = OfflineBuffer()
    p1 = {"payload_id": "evt_buf_01", "cpu": 50.0}
    p2 = {"payload_id": "evt_buf_02", "cpu": 60.0}

    assert buf.enqueue(p1) is True
    assert buf.enqueue(p2) is True
    assert buf.pending_count() == 2
    assert buf.total_count() == 2


def test_buffer_deduplication():
    buf = OfflineBuffer()
    p1 = {"payload_id": "evt_dup_01", "cpu": 50.0}

    assert buf.enqueue(p1) is True
    # Attempting to enqueue same payload_id must return False (deduplication)
    assert buf.enqueue(p1) is False
    assert buf.pending_count() == 1


def test_buffer_mark_sent_and_failed():
    buf = OfflineBuffer()
    p1 = {"payload_id": "evt_01", "cpu": 50.0}
    p2 = {"payload_id": "evt_02", "cpu": 60.0}
    buf.enqueue(p1)
    buf.enqueue(p2)

    buf.mark_sent("evt_01")
    assert buf.pending_count() == 1

    buf.mark_failed("evt_02", "Connection refused")
    pending = buf.get_pending()
    assert len(pending) == 1
    assert pending[0].attempts == 2
    assert pending[0].last_error == "Connection refused"


def test_egress_audit_logger():
    audit = EgressAuditLogger()
    rec = audit.record(
        payload_id="evt_aud_01",
        source_id="node_a81f",
        policy_verdict="PASS",
        transmission_status="SENT",
        destination="http://127.0.0.1:8000/api/v1/telemetry",
        safe_payload={"payload_id": "evt_aud_01", "cpu": 45.0},
        allowed_fields=["payload_id", "cpu"],
        blocked_fields=["raw_logs", "password"],
        detected_secrets=["password_in_raw_logs"],
    )

    assert rec.audit_id.startswith("aud_")
    assert rec.policy_verdict == "PASS"
    assert rec.transmission_status == "SENT"
    assert len(rec.blocked_fields) == 2

    # Query latest
    latest = audit.get_latest()
    assert latest is not None
    assert latest.audit_id == rec.audit_id

    # Update status
    audit.update_transmission_status(payload_id="evt_aud_01", new_status="BUFFERED")
    updated = audit.get_latest()
    assert updated.transmission_status == "BUFFERED"

    stats = audit.get_summary_stats()
    assert stats["total_egress_audits"] == 1
    assert stats["buffered_count"] == 1
