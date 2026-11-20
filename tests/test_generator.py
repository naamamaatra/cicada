"""
SentinelOps AI - Tests for Member 1: Telemetry Generator.
"""

import pytest
from collector.generator import TelemetryGenerator
from shared.constants import DEFAULT_SERVERS


def test_generator_normal_metrics_bounds():
    gen = TelemetryGenerator()
    event = gen.generate_normal(source_id="node_a81f")

    assert event["source_id"] == "node_a81f"
    assert 0.0 <= event["cpu"] <= 100.0
    assert 0.0 <= event["memory"] <= 100.0
    assert 0.0 <= event["disk"] <= 100.0
    assert event["latency_ms"] >= 0.0
    assert 0.0 <= event["packet_loss_pct"] <= 100.0
    assert event["error_count"] >= 0
    assert event["failed_logins"] >= 0
    assert event["collector_status"] == "online"
    assert event["event_category"] == "normal"


def test_generator_fleet_normal():
    gen = TelemetryGenerator()
    fleet = gen.generate_fleet_normal()

    # Must produce 3 events corresponding to the 3 default servers
    assert len(fleet) == 3
    source_ids = {e["source_id"] for e in fleet}
    expected_ids = {s["source_id"] for s in DEFAULT_SERVERS}
    assert source_ids == expected_ids


def test_generator_cpu_spike_scenario():
    gen = TelemetryGenerator()
    event = gen.generate_cpu_spike(source_id="node_a81f", cpu_val=97.5)
    assert event["cpu"] == 97.5
    assert event["cpu"] > 90.0  # Critical threshold
    assert event["event_category"] == "resource_pressure"


def test_generator_memory_leak_scenario():
    gen = TelemetryGenerator()
    event = gen.generate_memory_leak(source_id="node_b92c", memory_val=94.5)
    assert event["memory"] == 94.5
    assert event["memory"] > 90.0
    assert event["event_category"] == "memory_leak"


def test_generator_network_degradation_scenario():
    gen = TelemetryGenerator()
    event = gen.generate_network_degradation(source_id="node_c73d", latency_val=350.0, packet_loss_val=8.0)
    assert event["latency_ms"] == 350.0
    assert event["packet_loss_pct"] == 8.0
    assert event["event_category"] == "network_degradation"


def test_generator_cascade_failure_scenario():
    gen = TelemetryGenerator()
    event = gen.generate_cascade_failure(source_id="node_a81f")
    assert event["cpu"] > 95.0
    assert event["memory"] > 90.0
    assert event["latency_ms"] >= 900.0
    assert event["packet_loss_pct"] >= 10.0


def test_generator_raw_event_with_secrets():
    gen = TelemetryGenerator()
    raw = gen.generate_raw_event_with_secrets(server_index=0, scenario="normal")
    assert "raw_system_logs" in raw
    assert "db_password" in raw
    assert "api_key" in raw
    assert "hostname" in raw
    assert "internal_ip" in raw
    assert "SuperSecretPass123!" in raw["db_password"]

