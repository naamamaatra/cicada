"""
SentinelOps AI - Tests for Member 1: Privacy Engine & Pseudonymization.
"""

import pytest
from collector.privacy import PrivacyEngine, Pseudonymizer


def test_pseudonymizer_known_mappings():
    pseudo = Pseudonymizer()
    assert pseudo.pseudonymize("prod-app-srv-01.internal.corp") == "node_a81f"
    assert pseudo.pseudonymize("prod-db-master-01.internal.corp") == "node_b92c"
    assert pseudo.pseudonymize("prod-ingress-gw-01.internal.corp") == "node_c73d"
    assert pseudo.pseudonymize("10.240.10.15") == "node_a81f"


def test_pseudonymizer_already_pseudonymous():
    pseudo = Pseudonymizer()
    assert pseudo.pseudonymize("node_custom123") == "node_custom123"
    assert pseudo.pseudonymize("node_a81f") == "node_a81f"


def test_pseudonymizer_dynamic_hash():
    pseudo = Pseudonymizer()
    res1 = pseudo.pseudonymize("random-hostname.internal.net")
    res2 = pseudo.pseudonymize("random-hostname.internal.net")
    assert res1.startswith("node_")
    # Must be deterministic
    assert res1 == res2


def test_redact_bearer_token():
    engine = PrivacyEngine()
    text = "Authorization header Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token12345 in log"
    redacted, detected = engine.redact_text(text)
    assert "[REDACTED_TOKEN]" in redacted
    assert "eyJhbGci" not in redacted
    assert "bearer_token" in detected


def test_redact_api_keys():
    engine = PrivacyEngine()
    text = "Failed with api_key='sk-proj-1234567890abcdef1234567890' or secret_key: 'abcdef123456'"
    redacted, detected = engine.redact_text(text)
    assert "[REDACTED_API_KEY]" in redacted
    assert "sk-proj-1234567890" not in redacted
    assert "abcdef123456" not in redacted


def test_redact_database_connection_string():
    engine = PrivacyEngine()
    text = "Connecting to postgresql://dbuser:SuperSecretPassword123!@10.0.0.5:5432/my_db failed"
    redacted, detected = engine.redact_text(text)
    assert "[REDACTED_PASSWORD]" in redacted
    assert "SuperSecretPassword123!" not in redacted
    assert "db_connection_password" in detected


def test_redact_private_key():
    engine = PrivacyEngine()
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0fakekey...==\n-----END RSA PRIVATE KEY-----"
    redacted, detected = engine.redact_text(text)
    assert "[REDACTED_PRIVATE_KEY]" in redacted
    assert "MIIEow" not in redacted


def test_sanitize_dictionary_sensitive_keys():
    engine = PrivacyEngine()
    raw = {
        "source_id": "node_a81f",
        "cpu": 45.0,
        "db_password": "MySecretPassword99!",
        "api_key": "sk-1234567890abcdef12345",
        "nested": {
            "auth_token": "Bearer token998877665544",
            "normal_field": "hello world",
        },
    }
    sanitized, detected = engine.sanitize_dictionary(raw)
    assert sanitized["db_password"] == "[REDACTED_SECRET]"
    assert sanitized["api_key"] == "[REDACTED_SECRET]"
    assert sanitized["nested"]["auth_token"] == "[REDACTED_SECRET]"
    assert sanitized["nested"]["normal_field"] == "hello world"
    assert len(detected) >= 3


def test_process_raw_telemetry():
    engine = PrivacyEngine()
    raw = {
        "hostname": "prod-app-srv-01.internal.corp",
        "cpu": 75.0,
        "raw_logs": "User password=Confidential123 failed login",
    }
    cleaned, detected = engine.process_raw_telemetry(raw)
    assert cleaned["source_id"] == "node_a81f"
    assert "[REDACTED_PASSWORD]" in cleaned["raw_logs"]
    assert "Confidential123" not in cleaned["raw_logs"]
