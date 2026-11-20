"""
SentinelOps AI - Local Offline Telemetry Buffer & Reliability Engine.
Member 1: Collector & Privacy Engine.

Responsibilities:
1. Buffers sanitized telemetry events locally when backend API is unreachable or returns errors.
2. Implements FIFO queuing with duplicate prevention by payload_id.
3. Supports exponential backoff and retry mechanisms to drain backlog once connectivity is restored.
4. Tracks delivery state: pending, sent, failed.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from threading import Lock
from pydantic import BaseModel, Field


class BufferedItem(BaseModel):
    """
    Representation of an enqueued telemetry event.
    """
    payload_id: str = Field(..., description="Payload unique identifier")
    payload: Dict[str, Any] = Field(..., description="Sanitized telemetry payload")
    enqueued_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when event was placed in offline buffer",
    )
    attempts: int = Field(default=0, description="Number of transmission attempts")
    last_attempt_utc: Optional[str] = Field(default=None, description="Last transmission attempt timestamp")
    status: str = Field(default="pending", description="'pending', 'sent', or 'failed'")
    last_error: Optional[str] = Field(default=None, description="Last network/API error encountered")


class OfflineBuffer:
    """
    Thread-safe local buffer for reliable telemetry delivery.
    """

    def __init__(self, max_capacity: int = 1000):
        self._lock = Lock()
        self.max_capacity = max_capacity
        self._queue: List[BufferedItem] = []
        self._items_by_id: Dict[str, BufferedItem] = {}

    def enqueue(self, payload: Dict[str, Any], initial_error: Optional[str] = None) -> bool:
        """
        Add a sanitized telemetry payload to the buffer.
        Returns True if enqueued, False if already present (duplicate prevention).
        """
        with self._lock:
            payload_id = str(payload.get("payload_id", "")).strip()
            if not payload_id:
                return False

            # Duplicate prevention check
            if payload_id in self._items_by_id:
                return False

            item = BufferedItem(
                payload_id=payload_id,
                payload=payload,
                enqueued_at_utc=datetime.now(timezone.utc).isoformat(),
                attempts=1,
                last_attempt_utc=datetime.now(timezone.utc).isoformat(),
                status="pending",
                last_error=initial_error,
            )

            # Prevent unbounded memory growth
            if len(self._queue) >= self.max_capacity:
                oldest = self._queue.pop(0)
                self._items_by_id.pop(oldest.payload_id, None)

            self._queue.append(item)
            self._items_by_id[payload_id] = item
            return True

    def get_pending(self) -> List[BufferedItem]:
        """Get all pending buffered items in FIFO order."""
        with self._lock:
            return [item for item in self._queue if item.status == "pending"]

    def mark_sent(self, payload_id: str) -> bool:
        """Mark a buffered payload as successfully sent and remove from pending."""
        with self._lock:
            item = self._items_by_id.get(payload_id)
            if item:
                item.status = "sent"
                item.last_attempt_utc = datetime.now(timezone.utc).isoformat()
                return True
            return False

    def mark_failed(self, payload_id: str, error: str) -> None:
        """Record an attempt failure on a buffered item."""
        with self._lock:
            item = self._items_by_id.get(payload_id)
            if item:
                item.attempts += 1
                item.last_attempt_utc = datetime.now(timezone.utc).isoformat()
                item.last_error = error

    def pending_count(self) -> int:
        """Return number of currently pending buffered items."""
        with self._lock:
            return sum(1 for item in self._queue if item.status == "pending")

    def total_count(self) -> int:
        """Return total items currently stored in buffer."""
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Return True if no pending items."""
        return self.pending_count() == 0

    def get_stats(self) -> Dict[str, Any]:
        """Buffer health and capacity stats."""
        with self._lock:
            pending = sum(1 for item in self._queue if item.status == "pending")
            sent = sum(1 for item in self._queue if item.status == "sent")
            failed = sum(1 for item in self._queue if item.status == "failed")
            return {
                "total_buffered": len(self._queue),
                "pending": pending,
                "sent": sent,
                "failed": failed,
                "max_capacity": self.max_capacity,
            }

    def clear(self) -> None:
        """Clear all buffer contents."""
        with self._lock:
            self._queue.clear()
            self._items_by_id.clear()
