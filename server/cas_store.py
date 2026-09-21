"""CAS transport contract; the in-memory implementation is for tests only.

Production adapters must provide uncached reads and atomic conditional writes.
Never translate an uncertain network/write outcome into CasConflict or absence.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from threading import Lock
from typing import Protocol


@dataclass(frozen=True)
class CasValue:
    payload: dict
    version: str


class CasConflict(Exception):
    """The expected version did not match; this write definitely did not occur."""


class CasStore(Protocol):
    def read(self, key: str) -> CasValue | None:
        """Read a fresh, matching payload/version; None means confirmed absence."""
        ...

    def compare_and_swap(self, key: str, payload: dict, expected_version: str | None) -> str:
        """Atomically write iff the version matches (None requires absence)."""
        ...


class InMemoryCasStore:
    """Thread-safe test double, not durable or shared between server processes."""

    def __init__(self):
        self._values: dict[str, CasValue] = {}
        self._sequence = 0
        self._lock = Lock()

    def read(self, key: str) -> CasValue | None:
        with self._lock:
            return copy.deepcopy(self._values.get(key))

    def compare_and_swap(self, key: str, payload: dict, expected_version: str | None) -> str:
        with self._lock:
            current = self._values.get(key)
            actual_version = current.version if current else None
            if actual_version != expected_version:
                raise CasConflict()
            self._sequence += 1
            version = str(self._sequence)
            self._values[key] = CasValue(copy.deepcopy(payload), version)
            return version
