"""
SentinelOps AI - Local Collector & Privacy Engine Coordinator.
Member 1: Collector & Privacy Engine.

Coordinates the end-to-end Local Telemetry Pipeline:
Telemetry Sources / Generator
    ↓
Privacy Engine (Secret Redaction + Pseudonymization)
    ↓
Allow-List Policy Gate (Strict field allow-listing & type validation)
    ↓
Local Analysis & Safe Payload Preparation
    ↓
Egress Audit Logger & Offline Buffer (Reliability & Proof)
    ↓
FastAPI Backend Transmission (POST /api/v1/telemetry)
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import logging
from typing import Dict, Any, List, Optional
import requests

from collector.privacy import PrivacyEngine, Pseudonymizer
from collector.policy import AllowListPolicy, PolicyResult
from collector.egress_audit import EgressAuditLogger, EgressAuditRecord
from collector.buffer import OfflineBuffer
from collector.generator import TelemetryGenerator
from shared.constants import DEFAULT_SERVERS

logger = logging.getLogger("SentinelOps.Collector")


class LocalCollector:
    """
    Central local agent running on infrastructure nodes.
    Guarantees privacy-first data handling and reliable transmission.
    """

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:8000/api/v1/telemetry",
        tenant_id: str = "tenant_demo",
        request_timeout: float = 3.0,
    ):
        self.api_url = api_url
        self.tenant_id = tenant_id
        self.request_timeout = request_timeout

        # Initialize sub-modules
        self.pseudonymizer = Pseudonymizer()
        self.privacy_engine = PrivacyEngine(self.pseudonymizer)
        self.policy = AllowListPolicy()
        self.audit_logger = EgressAuditLogger()
        self.buffer = OfflineBuffer()
        self.generator = TelemetryGenerator(tenant_id=self.tenant_id)

    def process_and_send(
        self,
        raw_event: Dict[str, Any],
        destination_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full local pipeline on a raw telemetry/log event:
        1. Pseudonymization of hostnames.
        2. Deep redaction of sensitive credentials and tokens.
        3. Strict allow-list policy filtering and boundary validation.
        4. Egress audit recording (proof generation).
        5. Transmission to backend or buffering if offline.
        """
        target_url = destination_url or self.api_url
        raw_preview = dict(raw_event)  # Kept local for audit proof

        # -------------------------------------------------------------
        # STEP 1 & 2: Privacy Engine (Pseudonymize & Redact Secrets)
        # -------------------------------------------------------------
        sanitized_event, detected_secrets = self.privacy_engine.process_raw_telemetry(raw_event)

        # -------------------------------------------------------------
        # STEP 3: Allow-List Policy Gate
        # -------------------------------------------------------------
        policy_result: PolicyResult = self.policy.evaluate(sanitized_event)

        payload_id = str(sanitized_event.get("payload_id", f"evt_unregistered_{id(raw_event)}"))
        source_id = str(sanitized_event.get("source_id", "unknown_node"))

        # If policy blocks the payload
        if not policy_result.allowed:
            audit_record = self.audit_logger.record(
                payload_id=payload_id,
                source_id=source_id,
                policy_verdict="BLOCKED",
                transmission_status="BLOCKED",
                destination=target_url,
                safe_payload=None,
                raw_event_preview=raw_preview,
                allowed_fields=policy_result.allowed_fields,
                blocked_fields=policy_result.blocked_fields,
                detected_secrets=detected_secrets,
                error_message="; ".join(policy_result.violations),
            )
            return {
                "success": False,
                "status": "BLOCKED",
                "message": policy_result.summary,
                "audit_id": audit_record.audit_id,
                "violations": policy_result.violations,
                "blocked_fields": policy_result.blocked_fields,
            }

        safe_payload = policy_result.sanitized_payload
        payload_id = safe_payload["payload_id"]
        source_id = safe_payload["source_id"]

        # -------------------------------------------------------------
        # STEP 4: Transmit or Buffer (Reliability)
        # -------------------------------------------------------------
        try:
            response = requests.post(
                target_url,
                json=safe_payload,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code in [200, 201]:
                res_data = response.json()
                audit_record = self.audit_logger.record(
                    payload_id=payload_id,
                    source_id=source_id,
                    policy_verdict="PASS",
                    transmission_status="SENT",
                    destination=target_url,
                    safe_payload=safe_payload,
                    raw_event_preview=raw_preview,
                    allowed_fields=policy_result.allowed_fields,
                    blocked_fields=policy_result.blocked_fields,
                    detected_secrets=detected_secrets,
                )
                return {
                    "success": True,
                    "status": "SENT",
                    "http_status": response.status_code,
                    "payload_id": payload_id,
                    "source_id": source_id,
                    "alerts_generated": res_data.get("alerts_generated", 0),
                    "alerts": res_data.get("alerts", []),
                    "audit_id": audit_record.audit_id,
                    "safe_payload": safe_payload,
                }
            else:
                # Backend returned non-2xx status -> buffer locally
                err_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                self.buffer.enqueue(safe_payload, initial_error=err_msg)
                audit_record = self.audit_logger.record(
                    payload_id=payload_id,
                    source_id=source_id,
                    policy_verdict="PASS",
                    transmission_status="BUFFERED",
                    destination=target_url,
                    safe_payload=safe_payload,
                    raw_event_preview=raw_preview,
                    allowed_fields=policy_result.allowed_fields,
                    blocked_fields=policy_result.blocked_fields,
                    detected_secrets=detected_secrets,
                    error_message=err_msg,
                )
                return {
                    "success": True,
                    "status": "BUFFERED",
                    "message": "Backend returned non-2xx; payload buffered locally",
                    "payload_id": payload_id,
                    "audit_id": audit_record.audit_id,
                }

        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as exc:
            # Network failure / Backend offline -> buffer locally
            err_msg = f"Network failure: {type(exc).__name__} - {str(exc)}"
            self.buffer.enqueue(safe_payload, initial_error=err_msg)
            audit_record = self.audit_logger.record(
                payload_id=payload_id,
                source_id=source_id,
                policy_verdict="PASS",
                transmission_status="BUFFERED",
                destination=target_url,
                safe_payload=safe_payload,
                raw_event_preview=raw_preview,
                allowed_fields=policy_result.allowed_fields,
                blocked_fields=policy_result.blocked_fields,
                detected_secrets=detected_secrets,
                error_message=err_msg,
            )
            return {
                "success": True,
                "status": "BUFFERED",
                "message": "Backend unreachable; payload buffered locally",
                "payload_id": payload_id,
                "audit_id": audit_record.audit_id,
                "error": err_msg,
            }

    def flush_buffer(self) -> Dict[str, Any]:
        """
        Drain pending buffered events by attempting retransmission.
        Ensures in-order delivery and updates audit records.
        """
        pending_items = self.buffer.get_pending()
        if not pending_items:
            return {"status": "EMPTY", "flushed_count": 0, "remaining_count": 0}

        flushed = 0
        failed = 0

        for item in pending_items:
            try:
                response = requests.post(
                    self.api_url,
                    json=item.payload,
                    timeout=self.request_timeout,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code in [200, 201]:
                    self.buffer.mark_sent(item.payload_id)
                    self.audit_logger.update_transmission_status(
                        payload_id=item.payload_id,
                        new_status="SENT",
                    )
                    flushed += 1
                else:
                    self.buffer.mark_failed(item.payload_id, f"HTTP {response.status_code}")
                    failed += 1
            except requests.exceptions.RequestException as exc:
                self.buffer.mark_failed(item.payload_id, str(exc))
                failed += 1

        return {
            "status": "FLUSHED" if failed == 0 else "PARTIAL",
            "flushed_count": flushed,
            "failed_count": failed,
            "remaining_count": self.buffer.pending_count(),
        }

    def send_fleet_normal(self) -> List[Dict[str, Any]]:
        """
        Generate and transmit normal telemetry across all 3 simulated servers.
        Satisfies Phase 1 baseline requirement.
        """
        fleet_events = self.generator.generate_fleet_normal()
        results = []
        for event in fleet_events:
            results.append(self.process_and_send(event))
        return results

    def inject_failure(self, source_id: str, scenario: str = "cpu_spike") -> Dict[str, Any]:
        """
        Inject a simulated infrastructure failure for a specific node.
        """
        if scenario == "cpu_spike":
            raw_event = self.generator.generate_cpu_spike(source_id=source_id)
        elif scenario == "memory_leak":
            raw_event = self.generator.generate_memory_leak(source_id=source_id)
        elif scenario == "network_degradation":
            raw_event = self.generator.generate_network_degradation(source_id=source_id)
        elif scenario == "auth_attack":
            raw_event = self.generator.generate_auth_attack(source_id=source_id)
        elif scenario == "app_crash":
            raw_event = self.generator.generate_app_crash(source_id=source_id)
        elif scenario == "cascade_failure":
            raw_event = self.generator.generate_cascade_failure(source_id=source_id)
        else:
            raw_event = self.generator.generate_cpu_spike(source_id=source_id)

        return self.process_and_send(raw_event)

    def run_phase1_demo(self) -> Dict[str, Any]:
        """
        Execute the full Phase 1 Demo Flow:
        1. Send healthy baseline across 3 servers (node_a81f, node_b92c, node_c73d).
        2. Inject server failure on node_a81f (CPU spike / cascade).
        3. Verify backend receives data and triggers alerts.
        4. Verify audit trail.
        """
        print("\n" + "=" * 60)
        print("🚀 RUNNING SENTINELOPS AI — PHASE 1 DEMO WORKFLOW")
        print("=" * 60)

        # Step 1: Normal Fleet Telemetry
        print("\n[Step 1] Generating and transmitting normal baseline for 3 servers...")
        fleet_results = self.send_fleet_normal()
        for res in fleet_results:
            print(f"  -> Node {res.get('source_id')}: Status {res.get('status')} (Alerts: {res.get('alerts_generated', 0)})")

        # Step 2: Inject Simulated Failure on Node A
        target_node = DEFAULT_SERVERS[0]["source_id"]
        print(f"\n[Step 2] Injecting simulated server failure on {target_node} (CPU Spike > 95%)...")
        failure_res = self.inject_failure(source_id=target_node, scenario="cpu_spike")
        print(f"  -> Node {failure_res.get('source_id')}: Status {failure_res.get('status')}")
        print(f"  -> Alerts Generated by Backend: {failure_res.get('alerts_generated', 0)}")
        for alert in failure_res.get("alerts", []):
            print(f"     * [{alert.get('severity')}] {alert.get('alert_type')}: {alert.get('message')}")

        # Step 3: Egress Audit Proof
        latest_audit = self.audit_logger.get_latest()
        print(f"\n[Step 3] Egress Audit Verification:")
        if latest_audit:
            print(f"  -> Audit ID: {latest_audit.audit_id}")
            print(f"  -> Policy Verdict: {latest_audit.policy_verdict}")
            print(f"  -> Transmission Status: {latest_audit.transmission_status}")
            print(f"  -> Allowed Fields Transmitted: {len(latest_audit.allowed_fields)}")

        print("\n" + "=" * 60)
        print("✅ PHASE 1 DEMO WORKFLOW COMPLETE")
        print("=" * 60)

        return {
            "fleet_results": fleet_results,
            "failure_result": failure_res,
            "latest_audit": latest_audit.model_dump() if latest_audit else None,
        }

    def run_privacy_demo(self) -> Dict[str, Any]:
        """
        Execute the Privacy Engine & Allow-List Policy Demonstration:
        1. Generate a raw local event containing real hostname, fake password, bearer token, API key, and unapproved fields.
        2. Run through local privacy pipeline.
        3. Show that sensitive secrets are redacted, unapproved fields stripped, and hostname pseudonymized.
        """
        raw_event = self.generator.generate_raw_event_with_secrets(server_index=0, scenario="cpu_spike")
        result = self.process_and_send(raw_event)
        latest_audit = self.audit_logger.get_latest()

        return {
            "original_raw_event": raw_event,
            "pipeline_result": result,
            "egress_audit_proof": latest_audit.model_dump() if latest_audit else None,
        }


# -----------------------------------------------------------------------------
# Command-Line Interface Entrypoint
# -----------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="SentinelOps AI - Local Collector & Privacy Engine")
    parser.add_argument("--mode", choices=["normal", "failure", "demo-phase1", "demo-privacy", "flush"], default="demo-phase1")
    parser.add_argument("--source", default="node_a81f", help="Target source node ID")
    parser.add_argument("--scenario", default="cpu_spike", choices=["cpu_spike", "memory_leak", "network_degradation", "auth_attack", "app_crash", "cascade_failure"])
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/v1/telemetry", help="Backend API endpoint URL")

    args = parser.parse_args()

    collector = LocalCollector(api_url=args.api_url)

    if args.mode == "demo-phase1":
        collector.run_phase1_demo()
    elif args.mode == "demo-privacy":
        res = collector.run_privacy_demo()
        print("\n--- ORIGINAL RAW LOCAL EVENT ---")
        print(json.dumps(res["original_raw_event"], indent=2))
        print("\n--- EGRESS AUDIT PROOF (WHAT WAS TRANSMITTED) ---")
        print(json.dumps(res["egress_audit_proof"], indent=2))
    elif args.mode == "normal":
        print(f"Sending normal fleet telemetry to {args.api_url}...")
        results = collector.send_fleet_normal()
        print(f"Transmitted {len(results)} events.")
    elif args.mode == "failure":
        print(f"Injecting failure '{args.scenario}' on {args.source}...")
        res = collector.inject_failure(source_id=args.source, scenario=args.scenario)
        print(json.dumps(res, indent=2))
    elif args.mode == "flush":
        print("Flushing local offline buffer...")
        res = collector.flush_buffer()
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

