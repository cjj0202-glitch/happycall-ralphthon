"""Conservative local reservations, NOT a provider billing balance.

Failed calls retain their reservation: timeout does not prove no charge occurred.
No transcript, input text, or credential is ever written to this ledger.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

from filelock import FileLock
from server.errors import DemoError
from server.repository import ROOT, atomic_json


class Budget:
    def __init__(self, path: Path | None = None, limit_cents: int = 3000, warn_cents: int = 2500):
        self.path = path or ROOT / ".local/demo-usage.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock", timeout=15)
        self.limit, self.warn = limit_cents, warn_cents

    def _read(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"entries": []}

    def status(self):
        with self.lock:
            total = sum(x["reservedCents"] for x in self._read()["entries"])
        return {"reservedUsd": total / 100, "limitUsd": self.limit / 100,
                "warning": total >= self.warn, "accounting": "conservative-local-reservations"}

    def reserve(self, cents: int, purpose: str) -> str:
        if cents <= 0:
            raise ValueError("Positive reservation required")
        with self.lock:
            data = self._read()
            total = sum(x["reservedCents"] for x in data["entries"])
            if total + cents > self.limit:
                raise DemoError("BUDGET_LIMIT", "데모 예산 30달러 상한에 도달하여 API 호출을 중단했습니다.", 429)
            request_id = str(uuid.uuid4())
            data["entries"].append({"requestId": request_id, "purpose": purpose,
                "reservedCents": cents, "state": "reserved", "at": datetime.now(timezone.utc).isoformat()})
            atomic_json(self.path, data)
        return request_id

    def finish(self, request_id: str, success: bool):
        with self.lock:
            data = self._read()
            for entry in data["entries"]:
                if entry["requestId"] == request_id:
                    entry["state"] = "completed" if success else "failed-cost-uncertain"
            atomic_json(self.path, data)
