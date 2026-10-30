"""Tiny JSON-file storage with a lock and atomic writes."""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


class SubmissionStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def all(self) -> list:
        """Return every saved submission, oldest first."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def add(self, record: dict) -> dict:
        entry = {
            "id": uuid.uuid4().hex[:8],
            **record,
            "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        with self._lock:
            items = self.all()
            items.append(entry)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(items, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        return entry
