"""
SentinelOps AI - Privacy Engine & Sensitive Data Redaction.
Member 1: Collector & Privacy Engine.

Responsibilities:
1. Detect sensitive information (passwords, tokens, API keys, credentials, PII).
2. Redact sensitive values from logs and metadata.
3. Pseudonymize hostnames and infrastructure identifiers deterministically.
4. Ensure unapproved raw logs and sensitive data never escape the local environment.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple, Optional


class Pseudonymizer:
    """
    Deterministically transforms real hostnames and internal identifiers
    into privacy-safe pseudonymous node IDs (e.g. node_a81f).
    The mapping is maintained locally and never transmitted.
    """

    def __init__(self, prefix: str = "node_"):
        self.prefix = prefix
        # Predefined stable mappings for demonstration consistency
        self._known_mappings: Dict[str, str] = {
            "prod-app-srv-01.internal.corp": "node_a81f",
            "prod-db-master-01.internal.corp": "node_b92c",
            "prod-ingress-gw-01.internal.corp": "node_c73d",
            "10.240.10.15": "node_a81f",
            "10.240.10.20": "node_b92c",
            "10.240.10.30": "node_c73d",
        }
        self._reverse_mappings: Dict[str, str] = {
            v: k for k, v in self._known_mappings.items()
        }

    def pseudonymize(self, identifier: str) -> str:
        """
        Convert a real hostname or IP to a deterministic pseudonymous ID.
        If already in 'node_xxxx' format, return as-is.
        """
        if not identifier:
            return f"{self.prefix}unknown"

        identifier_clean = identifier.strip()

        # If already pseudonymous
        if re.match(r"^node_[a-z0-9_]+$", identifier_clean, re.IGNORECASE):
            return identifier_clean.lower()

        # Check known mappings
        if identifier_clean in self._known_mappings:
            return self._known_mappings[identifier_clean]

        # Deterministic SHA-256 hash prefix (first 4-6 hex chars)
        hash_digest = hashlib.sha256(identifier_clean.encode("utf-8")).hexdigest()[:4]
        pseudo_id = f"{self.prefix}{hash_digest}".lower()

        # Store in local memory map
        self._known_mappings[identifier_clean] = pseudo_id
        self._reverse_mappings[pseudo_id] = identifier_clean
        return pseudo_id

    def register_mapping(self, real_identifier: str, pseudo_id: str) -> None:
        """Manually register a mapping for consistency."""
        self._known_mappings[real_identifier.strip()] = pseudo_id.strip()
        self._reverse_mappings[pseudo_id.strip()] = real_identifier.strip()

    def get_real_identifier_local_only(self, pseudo_id: str) -> Optional[str]:
        """
        Retrieve original identifier strictly within the local environment.
        Never to be included in outbound network payloads.
        """
        return self._reverse_mappings.get(pseudo_id)


class PrivacyEngine:
    """
    Comprehensive privacy filter that detects, redacts, and strips
    sensitive data from telemetry payloads and raw local events.
    """

    # Common sensitive key patterns in dictionaries
    SENSITIVE_KEY_PATTERNS = [
        re.compile(r"password|passwd|pwd|passphrase", re.IGNORECASE),
        re.compile(r"secret|private_key|priv_key", re.IGNORECASE),
        re.compile(r"token|bearer|auth|authorization", re.IGNORECASE),
        re.compile(r"api_key|apikey|client_secret", re.IGNORECASE),
        re.compile(r"credential|credentials|cert", re.IGNORECASE),
        re.compile(r"ssn|social_security|credit_card|cc_num", re.IGNORECASE),
        re.compile(r"cookie|session|jwt", re.IGNORECASE),
    ]

    # Regular expressions for sensitive text content
    REGEX_PATTERNS = [
        # Bearer Tokens (JWT or hex/alphanumeric)
        (
            re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.~\+\/=]{15,}", re.IGNORECASE),
            r"\1[REDACTED_TOKEN]",
            "bearer_token",
        ),
        # Generic API keys: key=..., api_key=..., token=...
        (
            re.compile(
                r"((?:api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key)\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.]{8,}(['\"]?)",
                re.IGNORECASE,
            ),
            r"\1[REDACTED_API_KEY]\2",
            "api_key",
        ),
        # OpenAI style API keys
        (
            re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
            "[REDACTED_API_KEY]",
            "openai_key",
        ),
        # GitHub Personal Access Tokens
        (
            re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}", re.IGNORECASE),
            "[REDACTED_GITHUB_TOKEN]",
            "github_token",
        ),
        # AWS Access Key IDs
        (
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            "[REDACTED_AWS_KEY]",
            "aws_access_key",
        ),
        # Passwords in URLs / Connection strings: postgresql://user:pass@host:5432/db
        (
            re.compile(
                r"([a-zA-Z0-9+.-]+://[^:/@\s]+:)([^@/\s]+)(@[^/\s]+)",
                re.IGNORECASE,
            ),
            r"\1[REDACTED_PASSWORD]\3",
            "db_connection_password",
        ),
        # Password in key-value format (password=..., "password": "...")
        (
            re.compile(
                r"((?:password|passwd|pwd|secret)\s*[:=]\s*['\"]?)([^'\",\s]{4,})(['\"]?)",
                re.IGNORECASE,
            ),
            r"\1[REDACTED_PASSWORD]\3",
            "password_literal",
        ),
        # Private Keys (PEM blocks)
        (
            re.compile(
                r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
            ),
            "[REDACTED_PRIVATE_KEY]",
            "private_key_pem",
        ),
        # Credit Card Numbers (13-19 digits formatted or unformatted)
        (
            re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
            "[REDACTED_CREDIT_CARD]",
            "credit_card",
        ),
        # Social Security Numbers (US format)
        (
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "[REDACTED_SSN]",
            "ssn",
        ),
    ]

    def __init__(self, pseudonymizer: Optional[Pseudonymizer] = None):
        self.pseudonymizer = pseudonymizer or Pseudonymizer()

    def redact_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Redact sensitive tokens, passwords, and keys from a string.
        Returns (redacted_text, list_of_detected_types).
        """
        if not isinstance(text, str):
            return text, []

        detected_types: List[str] = []
        redacted = text

        for pattern, replacement, pattern_name in self.REGEX_PATTERNS:
            if pattern.search(redacted):
                detected_types.append(pattern_name)
                redacted = pattern.sub(replacement, redacted)

        return redacted, detected_types

    def is_sensitive_key(self, key_name: str) -> bool:
        """Check if a dictionary key name suggests sensitive content."""
        if not isinstance(key_name, str):
            return False
        return any(pattern.search(key_name) for pattern in self.SENSITIVE_KEY_PATTERNS)

    def sanitize_dictionary(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Recursively redact sensitive values inside a dictionary.
        Returns (sanitized_dict, detected_secrets_list).
        """
        sanitized: Dict[str, Any] = {}
        all_detected: List[str] = []

        for key, value in data.items():
            # If the key itself is sensitive, redact completely
            if self.is_sensitive_key(key):
                all_detected.append(f"sensitive_field:{key}")
                sanitized[key] = "[REDACTED_SECRET]"
                continue

            # If value is string, check regex patterns
            if isinstance(value, str):
                redacted_val, detected = self.redact_text(value)
                sanitized[key] = redacted_val
                all_detected.extend([f"{d}_in_{key}" for d in detected])
            elif isinstance(value, dict):
                sub_sanitized, sub_detected = self.sanitize_dictionary(value)
                sanitized[key] = sub_sanitized
                all_detected.extend(sub_detected)
            elif isinstance(value, list):
                sanitized_list = []
                for item in value:
                    if isinstance(item, str):
                        r_item, detected = self.redact_text(item)
                        sanitized_list.append(r_item)
                        all_detected.extend([f"{d}_in_list" for d in detected])
                    elif isinstance(item, dict):
                        sub_s, sub_d = self.sanitize_dictionary(item)
                        sanitized_list.append(sub_s)
                        all_detected.extend(sub_d)
                    else:
                        sanitized_list.append(item)
                sanitized[key] = sanitized_list
            else:
                sanitized[key] = value

        return sanitized, all_detected

    def pseudonymize_host(self, host_identifier: str) -> str:
        """Pseudonymize a server hostname or IP."""
        return self.pseudonymizer.pseudonymize(host_identifier)

    def process_raw_telemetry(self, raw_event: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Run initial privacy pass:
        1. Pseudonymize hostname/source_id if real name provided.
        2. Redact any sensitive text or keys.
        Returns (privacy_cleaned_dict, detected_sensitive_items).
        """
        cleaned = dict(raw_event)
        detected_items: List[str] = []

        # 1. Pseudonymize host identifier
        if "hostname" in cleaned:
            real_host = cleaned["hostname"]
            cleaned["source_id"] = self.pseudonymize_host(real_host)
        elif "source_id" in cleaned:
            cleaned["source_id"] = self.pseudonymize_host(cleaned["source_id"])

        # 2. Sanitize all fields
        sanitized_dict, detected = self.sanitize_dictionary(cleaned)
        detected_items.extend(detected)

        return sanitized_dict, detected_items

