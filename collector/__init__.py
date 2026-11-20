"""
SentinelOps AI - Collector Package Initialization.
Member 1: Collector & Privacy Engine.
"""

from collector.privacy import PrivacyEngine, Pseudonymizer
from collector.policy import AllowListPolicy, PolicyResult, PolicyViolationError
from collector.egress_audit import EgressAuditLogger, EgressAuditRecord
from collector.buffer import OfflineBuffer, BufferedItem
from collector.generator import TelemetryGenerator

def __getattr__(name: str):
    if name == "LocalCollector":
        from collector.collector import LocalCollector
        return LocalCollector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "PrivacyEngine",
    "Pseudonymizer",
    "AllowListPolicy",
    "PolicyResult",
    "PolicyViolationError",
    "EgressAuditLogger",
    "EgressAuditRecord",
    "OfflineBuffer",
    "BufferedItem",
    "TelemetryGenerator",
    "LocalCollector",
]
