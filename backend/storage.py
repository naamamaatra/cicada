"""
SentinelOps AI - In-Memory Storage Layer for Phase 1.
Modular data access layer designed to be easily replaced by SQLite in Phase 4.
"""

from typing import List, Optional, Dict
from threading import Lock
from backend.schemas import TelemetryPayload, Alert


class InMemoryStorage:
    """
    Thread-safe in-memory store for telemetry events and alerts.
    """
    def __init__(self):
        self._lock = Lock()
        # List of all telemetry payloads in insertion order
        self._telemetry_list: List[TelemetryPayload] = []
        # Index by payload_id for fast lookup and deduplication
        self._telemetry_by_id: Dict[str, TelemetryPayload] = {}
        # Index by source_id for fast per-node queries
        self._telemetry_by_source: Dict[str, List[TelemetryPayload]] = {}

        # Alerts list in insertion order
        self._alerts_list: List[Alert] = []
        # Index alerts by source_id
        self._alerts_by_source: Dict[str, List[Alert]] = {}

    def add_telemetry(self, payload: TelemetryPayload) -> bool:
        """
        Add a telemetry record to memory.
        Returns True if inserted, False if duplicate payload_id.
        """
        with self._lock:
            if payload.payload_id in self._telemetry_by_id:
                # Duplicate detected: update or skip
                return False

            self._telemetry_list.append(payload)
            self._telemetry_by_id[payload.payload_id] = payload

            if payload.source_id not in self._telemetry_by_source:
                self._telemetry_by_source[payload.source_id] = []
            self._telemetry_by_source[payload.source_id].append(payload)
            return True

    def get_all_telemetry(
        self,
        source_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[TelemetryPayload]:
        """
        Retrieve telemetry records, newest first.
        Optional filtering by source_id and count limit.
        """
        with self._lock:
            if source_id:
                records = self._telemetry_by_source.get(source_id, [])
            else:
                records = self._telemetry_list

            # Return newest first
            results = list(reversed(records))
            if limit is not None and limit > 0:
                results = results[:limit]
            return results

    def get_latest_telemetry(self, source_id: Optional[str] = None) -> Optional[TelemetryPayload]:
        """
        Retrieve the single most recent telemetry record.
        """
        with self._lock:
            if source_id:
                records = self._telemetry_by_source.get(source_id, [])
                return records[-1] if records else None
            return self._telemetry_list[-1] if self._telemetry_list else None

    def get_telemetry_by_source(
        self, source_id: str, limit: Optional[int] = None
    ) -> List[TelemetryPayload]:
        """
        Retrieve telemetry records for a specific source node, newest first.
        """
        return self.get_all_telemetry(source_id=source_id, limit=limit)

    def add_alert(self, alert: Alert) -> None:
        """
        Store a generated alert in memory.
        """
        with self._lock:
            self._alerts_list.append(alert)
            if alert.source_id not in self._alerts_by_source:
                self._alerts_by_source[alert.source_id] = []
            self._alerts_by_source[alert.source_id].append(alert)

    def add_alerts(self, alerts: List[Alert]) -> None:
        """
        Store multiple alerts.
        """
        for alert in alerts:
            self.add_alert(alert)

    def get_all_alerts(
        self,
        source_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Alert]:
        """
        Retrieve alerts, newest first.
        """
        with self._lock:
            if source_id:
                records = self._alerts_by_source.get(source_id, [])
            else:
                records = self._alerts_list

            results = list(reversed(records))
            if limit is not None and limit > 0:
                results = results[:limit]
            return results

    def get_latest_alert(self, source_id: Optional[str] = None) -> Optional[Alert]:
        """
        Retrieve the single most recent alert.
        """
        with self._lock:
            if source_id:
                records = self._alerts_by_source.get(source_id, [])
                return records[-1] if records else None
            return self._alerts_list[-1] if self._alerts_list else None

    def get_alerts_by_source(self, source_id: str, limit: Optional[int] = None) -> List[Alert]:
        """
        Retrieve alerts for a specific source, newest first.
        """
        return self.get_all_alerts(source_id=source_id, limit=limit)

    def get_all_sources(self) -> List[str]:
        """
        Get all unique monitored source IDs.
        """
        with self._lock:
            return list(self._telemetry_by_source.keys())

    def get_latest_per_source(self) -> Dict[str, TelemetryPayload]:
        """
        Get the latest telemetry record for every unique source.
        """
        with self._lock:
            return {
                source_id: records[-1]
                for source_id, records in self._telemetry_by_source.items()
                if records
            }

    def total_telemetry_count(self) -> int:
        with self._lock:
            return len(self._telemetry_list)

    def total_alerts_count(self) -> int:
        with self._lock:
            return len(self._alerts_list)

    def clear_alerts(self, source_id: Optional[str] = None) -> None:
        """
        Clear active/historical alerts, optionally filtered by source_id.
        """
        with self._lock:
            if source_id:
                self._alerts_list = [a for a in self._alerts_list if a.source_id != source_id]
                if source_id in self._alerts_by_source:
                    self._alerts_by_source[source_id].clear()
            else:
                self._alerts_list.clear()
                self._alerts_by_source.clear()

    def clear(self) -> None:
        """
        Clear all stored records (useful for test isolation).
        """
        with self._lock:
            self._telemetry_list.clear()
            self._telemetry_by_id.clear()
            self._telemetry_by_source.clear()
            self._alerts_list.clear()
            self._alerts_by_source.clear()


# Global in-memory storage singleton for Phase 1
storage = InMemoryStorage()

