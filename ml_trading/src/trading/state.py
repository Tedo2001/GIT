from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class State:
    last_processed_bar: str | None = None
    daily_date: str | None = None
    daily_start_equity: float | None = None
    halted: bool = False
    halt_reason: str | None = None
    last_signal: dict[str, Any] | None = None
    last_order: dict[str, Any] | None = None


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> State:
        if not self.path.exists():
            return State()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return State(**data)
        except Exception:
            return State()

    def save(self, state: State) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(state), indent=2, default=str), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def utc_date() -> str:
        return datetime.now(timezone.utc).date().isoformat()
