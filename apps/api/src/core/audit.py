from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


def _hash_dict(d: dict[str, Any]) -> str:
    raw = json.dumps(d, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class AuditEvent:
    ts_ms: int
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    prev_hash: str | None = None
    hash: str | None = None


class AuditTrail:
    """Simple in-memory append-only audit chain (hash-linked).

    In production, persist to your metadata store via Core API, and/or to an immutable log store.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._last_hash: str | None = None

    def add(self, name: str, data: dict[str, Any] | None = None) -> None:
        evt = AuditEvent(
            ts_ms=int(time.time() * 1000),
            name=name,
            data=data or {},
            prev_hash=self._last_hash,
        )
        evt.hash = _hash_dict(
            {
                "ts_ms": evt.ts_ms,
                "name": evt.name,
                "data": evt.data,
                "prev_hash": evt.prev_hash,
            }
        )
        self._events.append(evt)
        self._last_hash = evt.hash

    def export(self) -> list[dict[str, Any]]:
        return [evt.__dict__ for evt in self._events]
