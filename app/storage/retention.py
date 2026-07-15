from __future__ import annotations

from app.storage.repository import Repository


def enforce_retention(repository: Repository, hours: int) -> dict[str, int]:
    return repository.purge(hours)
