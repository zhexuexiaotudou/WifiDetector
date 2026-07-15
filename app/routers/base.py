from __future__ import annotations

from typing import Protocol

from app.models.domain import RouterCapabilities, RouterSnapshot


class RouterAdapter(Protocol):
    async def probe(self) -> RouterCapabilities: ...

    async def login(self) -> None: ...

    async def fetch_snapshot(self) -> RouterSnapshot: ...

    async def logout(self) -> None: ...
