"""
SentinelOps AI - Infrastructure Telemetry Generator.
Member 1: Collector & Privacy Engine.

Responsibilities:
1. Simulate realistic multi-server telemetry across 3 default production nodes.
2. Produce normal baseline metrics (CPU 20-50%, RAM 35-65%, Latency 20-50ms).
3. Inject simulated failure scenarios on-demand:
   - High CPU Spike (Resource exhaustion)
   - Memory Leak (RAM accumulation)
   - Network Degradation (High latency & packet loss)
   - Security Attack (Spike in failed logins)
   - Application Crash (Spike in error count)
   - Cascade Failure (Multi-metric critical degradation)
4. Embed realistic raw events with fake sensitive data (passwords, tokens) to prove Privacy Engine.
"""

import uuid
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from shared.constants import DEFAULT_SERVERS


class TelemetryGenerator:
    """
    Generates synthetic infrastructure telemetry matching the agreed schema.
    """

    def __init__(self, tenant_id: str = "tenant_demo"):
        self.tenant_id = tenant_id
        self.servers = list(DEFAULT_SERVERS)
        self._seq_counter = 1

    def _next_payload_id(self, prefix: str = "evt") -> str:
        """Generate unique sequential or UUID payload ID."""
        pid = f"{prefix}_{self._seq_counter:04d}_{uuid.uuid4().hex[:4]}"
        self._seq_counter += 1
        return pid

    def generate_normal(
        self,
        source_id: Optional[str] = None,
        timestamp_utc: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate healthy/normal telemetry for a server.
        Health State: EXCELLENT / GOOD
        """
        sid = source_id or self.servers[0]["source_id"]
        ts = timestamp_utc or datetime.now(timezone.utc).isoformat()

        return {
            "payload_id": self._next_payload_id("evt_norm"),
            "tenant_id": self.tenant_id,
            "source_id": sid,
            "timestamp_utc": ts,
            "cpu": round(random.uniform(22.0, 48.0), 1),
            "memory": round(random.uniform(36.0, 58.0), 1),
            "disk": round(random.uniform(42.0, 64.0), 1),
            "latency_ms": round(random.uniform(18.0, 42.0), 1),
            "packet_loss_pct": round(random.uniform(0.0, 0.2), 2),
            "error_count": random.choice([0, 0, 0, 1]),
            "failed_logins": 0,
            "collector_status": "online",
            "event_category": "normal",
        }

    def generate_cpu_spike(
        self,
        source_id: Optional[str] = None,
        cpu_val: float = 96.8,
    ) -> Dict[str, Any]:
        """Generate CPU exhaustion scenario (triggers HIGH_CPU alert)."""
        sid = source_id or self.servers[0]["source_id"]
        return {
            "payload_id": self._next_payload_id("evt_cpu"),
            "tenant_id": self.tenant_id,
            "source_id": sid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cpu": float(cpu_val),
            "memory": 62.4,
            "disk": 58.0,
            "latency_ms": 48.5,
            "packet_loss_pct": 0.0,
            "error_count": 3,
            "failed_logins": 0,
            "collector_status": "online",
            "event_category": "resource_pressure",
        }

    def generate_memory_leak(
        self,
        source_id: Optional[str] = None,
        memory_val: float = 95.2,
    ) -> Dict[str, Any]:
        """Generate Memory Leak scenario (triggers HIGH_MEMORY alert)."""
        sid = source_id or self.servers[1]["source_id"]
        return {
            "payload_id": self._next_payload_id("evt_mem"),
            "tenant_id": self.tenant_id,
            "source_id": sid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cpu": 64.0,
            "memory": float(memory_val),
            "disk": 68.0,
            "latency_ms": 65.0,
            "packet_loss_pct": 0.0,
            "error_count": 6,
            "failed_logins": 0,
            "collector_status": "online",
            "event_category": "memory_leak",
        }

    def generate_network_degradation(
        self,
        source_id: Optional[str] = None,
        latency_val: float = 380.0,
        packet_loss_val: float = 9.4,
    ) -> Dict[str, Any]:
        """Generate Network Congestion scenario (triggers HIGH_LATENCY and HIGH_PACKET_LOSS)."""
        sid = source_id or self.servers[2]["source_id"]
        return {
            "payload_id": self._next_payload_id("evt_net"),
            "tenant_id": self.tenant_id,
            "source_id": sid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cpu": 45.0,
            "memory": 52.0,
            "disk": 50.0,
            "latency_ms": float(latency_val),
            "packet_loss_pct": float(packet_loss_val),
            "error_count": 12,
            "failed_logins": 0,
            "collector_status": "online",
            "event_category": "network_degradation",
        }

    def generate_auth_attack(
        self,
        source_id: Optional[str] = None,
        failed_logins: int = 14,
    ) -> Dict[str, Any]:
        """Generate Credential Stuffing / Auth attack (triggers SECURITY_FAILED_LOGINS)."""
        sid = source_id or self.servers[0]["source_id"]
        return {
            "payload_id": self._next_payload_id("evt_sec"),
            "tenant_id": self.tenant_id,
            "source_id": sid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cpu": 52.0,
            "memory": 48.0,
            "disk": 45.0,
            "latency_ms": 32.0,
            "packet_loss_pct": 0.0,
            "error_count": 2,
            "failed_logins": int(failed_logins),
            "collector_status": "online",
            "event_category": "security_incident",
        }

    def generate_app_crash(
        self,
        source_id: Optional[str] = None,
        error_count: int = 42,
    ) -> Dict[str, Any]:
        """Generate Application Exception Wave (triggers HIGH_ERROR_COUNT)."""
        sid = source_id or self.servers[0]["source_id"]
        return {
            "payload_id": self._next_payload_id("evt_err"),
            "tenant_id": self.tenant_id,
            "source_id": sid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cpu": 78.0,
            "memory": 72.0,
            "disk": 55.0,
            "latency_ms": 110.0,
            "packet_loss_pct": 0.5,
            "error_count": int(error_count),
            "failed_logins": 0,
            "collector_status": "online",
            "event_category": "application_failure",
        }

    def generate_cascade_failure(
        self,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate full critical cascade incident (Section 17 Step 2).
        CPU 98%, RAM 94%, Latency 900ms, Packet Loss 15%, Errors 30, Failed Logins 8.
        """
        sid = source_id or self.servers[0]["source_id"]
        return {
            "payload_id": self._next_payload_id("evt_crit"),
            "tenant_id": self.tenant_id,
            "source_id": sid,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cpu": 98.2,
            "memory": 94.6,
            "disk": 74.0,
            "latency_ms": 900.0,
            "packet_loss_pct": 15.0,
            "error_count": 30,
            "failed_logins": 8,
            "collector_status": "online",
            "event_category": "cascade_failure",
        }

    def generate_fleet_normal(self) -> List[Dict[str, Any]]:
        """
        Generate healthy normal telemetry events for all 3 simulated servers.
        Satisfies Phase 1 requirement: Show 3 Healthy/Normal Servers.
        """
        now = datetime.now(timezone.utc).isoformat()
        events = []
        for server in self.servers:
            events.append(self.generate_normal(source_id=server["source_id"], timestamp_utc=now))
        return events

    def generate_raw_event_with_secrets(
        self,
        server_index: int = 0,
        scenario: str = "normal",
    ) -> Dict[str, Any]:
        """
        Generate a realistic RAW local event containing fake secrets,
        real internal hostnames, and unapproved metadata fields.
        Used to demonstrate the Privacy Engine & Allow-list Policy Gate.
        """
        server = self.servers[server_index % len(self.servers)]
        real_host = server["real_hostname"]

        # Base metrics depending on scenario
        if scenario == "cpu_spike":
            base = self.generate_cpu_spike(source_id=real_host)
        elif scenario == "cascade_failure":
            base = self.generate_cascade_failure(source_id=real_host)
        else:
            base = self.generate_normal(source_id=real_host)

        # Inject fake sensitive content and prohibited fields
        raw_event = dict(base)
        raw_event["hostname"] = real_host
        raw_event["internal_ip"] = server["base_ip"]
        raw_event["raw_system_logs"] = (
            f"[2026-11-20 16:30:00] ERROR Connection failed for "
            f"postgresql://app_admin:SuperSecretPass123!@{server['base_ip']}:5432/orders_prod. "
            f"Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake_token_jwt. "
            f"OpenAI service key: sk-proj-ab12cd34ef56gh78ij90kl123456"
        )
        raw_event["db_password"] = "SuperSecretPass123!"
        raw_event["api_key"] = "sk-proj-ab12cd34ef56gh78ij90kl123456"
        raw_event["auth_token"] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake_token_jwt"
        raw_event["debug_stack_trace"] = (
            "Traceback (most recent call last):\n"
            "  File '/var/app/server.py', line 124, in connect_db\n"
            "    raise OperationalError('Connection timed out')"
        )
        raw_event["user_email"] = "dev-oncall@internal.corp"

        return raw_event

