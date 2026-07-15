from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class RuntimeHealth:
    running: bool = False
    current_room: str | None = None
    current_cycle: int = 0
    rooms_completed: int = 0
    last_cycle_seconds: float | None = None
    started_at: str | None = None
    updated_at: str | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


HEALTH = RuntimeHealth()
