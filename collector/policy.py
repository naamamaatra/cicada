"""
SentinelOps AI - Allow-List Policy Gate.
Member 1: Collector & Privacy Engine.

Responsibilities:
1. Enforce strict allow-list: ONLY approved telemetry fields can leave the local environment.
2. Block and strip unauthorized, unknown, or sensitive fields (e.g. raw logs, stack traces, headers).
3. Validate telemetry constraints (ranges, non-empty fields, valid timestamps).
4. Provide structured policy evaluation result with proof of what was permitted and what was blocked.
"""

from typing import Dict, Any, List, Set, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from shared.constants import ALLOWED_TELEMETRY_FIELDS


class PolicyViolationError(Exception):
    """Raised when telemetry payload strictly violates allow-list policy."""
    pass


class PolicyResult(BaseModel):
    """
    Detailed audit result of the allow-list policy evaluation.
    Used for local auditing and Egress Proof.
    """
    allowed: bool = Field(..., description="True if payload is valid for outbound transmission")
    allowed_fields: List[str] = Field(default_factory=list, description="Fields approved for egress")
    blocked_fields: List[str] = Field(default_factory=list, description="Fields intercepted and stripped")
    sanitized_payload: Optional[Dict[str, Any]] = Field(default=None, description="The safe payload ready to transmit")
    violations: List[str] = Field(default_factory=list, description="Validation issues or policy violations")
    summary: str = Field(default="", description="Human-readable policy status explanation")


class AllowListPolicy:
    """
    Strict allow-list policy enforcer.
    Ensures that only the agreed 13 telemetry fields can be transmitted.
    """

    ALLOWED_FIELDS: Set[str] = set(ALLOWED_TELEMETRY_FIELDS)

    # Mandatory fields for a valid telemetry payload
    REQUIRED_FIELDS: Set[str] = {
        "payload_id",
        "tenant_id",
        "source_id",
        "timestamp_utc",
        "cpu",
        "memory",
        "disk",
        "latency_ms",
        "packet_loss_pct",
        "collector_status",
    }

    def evaluate(self, payload: Dict[str, Any]) -> PolicyResult:
        """
        Evaluate incoming dictionary against allow-list policy.
        Drops unapproved fields and validates values of allowed fields.
        """
        allowed_found: List[str] = []
        blocked_found: List[str] = []
        violations: List[str] = []
        safe_payload: Dict[str, Any] = {}

        # 1. Field Partitioning (Allow-list vs Blocked)
        for key, value in payload.items():
            if key in self.ALLOWED_FIELDS:
                allowed_found.append(key)
                safe_payload[key] = value
            else:
                blocked_found.append(key)

        # 2. Check for missing required fields
        for req in self.REQUIRED_FIELDS:
            if req not in safe_payload:
                violations.append(f"Missing required telemetry field: '{req}'")

        # 3. Numeric bounds & type validation on safe fields
        if "cpu" in safe_payload:
            try:
                val = float(safe_payload["cpu"])
                if not (0.0 <= val <= 100.0):
                    violations.append(f"CPU utilization {val}% out of range [0.0, 100.0]")
                safe_payload["cpu"] = round(val, 2)
            except (ValueError, TypeError):
                violations.append(f"CPU value '{safe_payload['cpu']}' is not a valid float")

        if "memory" in safe_payload:
            try:
                val = float(safe_payload["memory"])
                if not (0.0 <= val <= 100.0):
                    violations.append(f"Memory utilization {val}% out of range [0.0, 100.0]")
                safe_payload["memory"] = round(val, 2)
            except (ValueError, TypeError):
                violations.append(f"Memory value '{safe_payload['memory']}' is not a valid float")

        if "disk" in safe_payload:
            try:
                val = float(safe_payload["disk"])
                if not (0.0 <= val <= 100.0):
                    violations.append(f"Disk utilization {val}% out of range [0.0, 100.0]")
                safe_payload["disk"] = round(val, 2)
            except (ValueError, TypeError):
                violations.append(f"Disk value '{safe_payload['disk']}' is not a valid float")

        if "latency_ms" in safe_payload:
            try:
                val = float(safe_payload["latency_ms"])
                if val < 0.0:
                    violations.append(f"Latency {val}ms cannot be negative")
                safe_payload["latency_ms"] = round(val, 2)
            except (ValueError, TypeError):
                violations.append(f"Latency value '{safe_payload['latency_ms']}' is not a valid float")

        if "packet_loss_pct" in safe_payload:
            try:
                val = float(safe_payload["packet_loss_pct"])
                if not (0.0 <= val <= 100.0):
                    violations.append(f"Packet loss {val}% out of range [0.0, 100.0]")
                safe_payload["packet_loss_pct"] = round(val, 2)
            except (ValueError, TypeError):
                violations.append(f"Packet loss value '{safe_payload['packet_loss_pct']}' is not a valid float")

        if "error_count" in safe_payload:
            try:
                val = int(safe_payload["error_count"])
                if val < 0:
                    violations.append(f"Error count {val} cannot be negative")
                safe_payload["error_count"] = val
            except (ValueError, TypeError):
                violations.append(f"Error count '{safe_payload['error_count']}' is not a valid integer")
        else:
            safe_payload["error_count"] = 0

        if "failed_logins" in safe_payload:
            try:
                val = int(safe_payload["failed_logins"])
                if val < 0:
                    violations.append(f"Failed logins {val} cannot be negative")
                safe_payload["failed_logins"] = val
            except (ValueError, TypeError):
                violations.append(f"Failed logins '{safe_payload['failed_logins']}' is not a valid integer")
        else:
            safe_payload["failed_logins"] = 0

        # String non-empty checks
        for str_field in ["payload_id", "tenant_id", "source_id", "collector_status"]:
            if str_field in safe_payload:
                val = str(safe_payload[str_field]).strip()
                if not val:
                    violations.append(f"String field '{str_field}' must not be empty")
                safe_payload[str_field] = val

        # Ensure default tenant if omitted
        if "tenant_id" not in safe_payload or not safe_payload["tenant_id"]:
            safe_payload["tenant_id"] = "tenant_demo"

        # Timestamp normalization
        if "timestamp_utc" in safe_payload:
            ts = safe_payload["timestamp_utc"]
            if isinstance(ts, datetime):
                safe_payload["timestamp_utc"] = ts.isoformat()
            elif isinstance(ts, str):
                safe_payload["timestamp_utc"] = ts.strip()

        is_allowed = len(violations) == 0

        if is_allowed:
            if blocked_found:
                summary = f"PASSED WITH POLICY FILTERING: {len(allowed_found)} allowed fields kept, {len(blocked_found)} unauthorized fields stripped ({', '.join(blocked_found)})"
            else:
                summary = f"PASSED: All {len(allowed_found)} fields conform to strict telemetry allow-list"
        else:
            summary = f"BLOCKED: Payload rejected due to {len(violations)} validation violations"

        return PolicyResult(
            allowed=is_allowed,
            allowed_fields=allowed_found,
            blocked_fields=blocked_found,
            sanitized_payload=safe_payload if is_allowed else None,
            violations=violations,
            summary=summary,
        )

