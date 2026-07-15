from __future__ import annotations

from app.models.domain import RouterCapabilities, RouterSnapshot


class H10e31Adapter:
    """Evidence-gated adapter; selectors/endpoints are intentionally not guessed."""

    def __init__(self, room_id: str) -> None:
        self.room_id = room_id

    async def probe(self) -> RouterCapabilities:
        return RouterCapabilities()

    async def login(self) -> None:
        raise RuntimeError("尚无脱敏后的真实 H10e-31 页面/API 证据，不能自动登录")

    async def fetch_snapshot(self) -> RouterSnapshot:
        return RouterSnapshot(
            room_id=self.room_id,
            router_reachable=False,
            capabilities=RouterCapabilities(),
            raw_source="h10e31-unverified",
            warnings=["真实适配器等待授权现场发现证据"],
        )

    async def logout(self) -> None:
        return None
