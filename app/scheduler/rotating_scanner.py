from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.detection.events import detect_events
from app.models.domain import RouterSnapshot
from app.routers.base import RouterAdapter
from app.routers.h10e31 import H10e31Adapter
from app.routers.local_pc import LocalPcAdapter
from app.routers.mock import MockAdapter
from app.scheduler.health import HEALTH
from app.security.anonymize import DeviceAnonymizer
from app.storage.repository import Repository

LOGGER = logging.getLogger(__name__)
AdapterFactory = Callable[[str, int], RouterAdapter]


class RotatingScanner:
    def __init__(
        self,
        settings: Settings,
        repository: Repository,
        adapter_factory: AdapterFactory | None = None,
        salt_file: Path | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        if adapter_factory is not None:
            self.adapter_factory = adapter_factory
        elif settings.app.mock_mode:
            self.adapter_factory = lambda room_id, cycle: MockAdapter(room_id, cycle)
        elif settings.app.field_data_source == "local_pc":
            rooms = {room.room_id: room for room in settings.rooms}
            self.adapter_factory = lambda room_id, _cycle: LocalPcAdapter(
                room_id,
                rooms[room_id].ssid,
                ping_sweep=settings.app.local_ping_sweep,
            )
        else:
            self.adapter_factory = lambda room_id, _cycle: H10e31Adapter(room_id)
        self.anonymizer = DeviceAnonymizer(salt_file or repository.path.parent / ".device_hmac_key")
        self._stop = asyncio.Event()

    async def scan_room(self, room_id: str, cycle: int) -> list[int]:
        room = next(room for room in self.settings.rooms if room.room_id == room_id)
        if not room.enabled:
            return []
        adapter = self.adapter_factory(room_id, cycle)
        await adapter.login()
        try:
            if isinstance(adapter, MockAdapter):
                snapshot = await adapter.fetch_snapshot()
            else:
                snapshot = await asyncio.wait_for(
                    adapter.fetch_snapshot(),
                    timeout=self.settings.app.per_room_scan_timeout_seconds,
                )
        finally:
            await adapter.logout()
        device_ids = {
            client.mac: self.anonymizer.device_id(client.mac) for client in snapshot.clients
        }
        monitor_ipv4 = "192.168.1.100" if snapshot.raw_source == "mock" else None
        sanitized = self._sanitize_snapshot(snapshot, device_ids, monitor_ipv4)
        self.repository.add_sample(snapshot, sanitized)
        seen_counts = {
            device_id: self.repository.recent_device_occurrences(room_id, device_id)
            for device_id in device_ids.values()
        }
        events = detect_events(
            snapshot,
            device_ids,
            self.repository.allowed_devices(room_id),
            monitor_ipv4,
            seen_counts,
        )
        event_ids = [self.repository.add_event(event) for event in events]
        self.repository.close_absent_events(room_id, event_ids)
        return event_ids

    async def scan_cycle(self) -> dict[str, object]:
        was_running = HEALTH.running
        HEALTH.current_cycle += 1
        HEALTH.rooms_completed = 0
        HEALTH.running = True
        if not HEALTH.started_at:
            HEALTH.started_at = datetime.now(UTC).isoformat()
        start = asyncio.get_running_loop().time()
        results: dict[str, object] = {}
        for room in self.settings.rooms:
            if self._stop.is_set():
                break
            HEALTH.current_room = room.room_id
            HEALTH.touch()
            try:
                event_ids = await self.scan_room(room.room_id, HEALTH.current_cycle)
                results[room.room_id] = {"ok": True, "event_ids": event_ids}
            except Exception as exc:  # isolated room failure is an explicit reliability boundary
                LOGGER.exception("room scan failed: %s", room.room_id)
                results[room.room_id] = {"ok": False, "error": type(exc).__name__}
            HEALTH.rooms_completed += 1
            HEALTH.touch()
            if self.settings.app.inter_room_pause_seconds:
                await asyncio.sleep(self.settings.app.inter_room_pause_seconds)
        HEALTH.current_room = None
        HEALTH.last_cycle_seconds = round(asyncio.get_running_loop().time() - start, 3)
        if not was_running:
            HEALTH.running = False
        HEALTH.touch()
        return {
            "cycle": HEALTH.current_cycle,
            "rooms": results,
            "seconds": HEALTH.last_cycle_seconds,
        }

    async def run(self) -> None:
        HEALTH.running = True
        try:
            while not self._stop.is_set():
                await self.scan_cycle()
                try:
                    await asyncio.wait_for(
                        self._stop.wait(), timeout=self.settings.app.cycle_pause_seconds
                    )
                except TimeoutError:
                    pass
        finally:
            HEALTH.running = False
            HEALTH.current_room = None
            HEALTH.touch()

    def stop(self) -> None:
        self._stop.set()

    @staticmethod
    def _sanitize_snapshot(
        snapshot: RouterSnapshot, device_ids: dict[str, str], monitor_ipv4: str | None
    ) -> dict[str, object]:
        clients: list[dict[str, object]] = []
        for client in snapshot.clients:
            is_monitor = bool(monitor_ipv4 and client.ip == monitor_ipv4)
            clients.append(
                {
                    "device_id": device_ids[client.mac],
                    "ip": None if not is_monitor else "monitor-pc",
                    "hostname": None,
                    "connection_type": client.connection_type,
                    "rssi": client.rssi,
                    "rx_bytes": client.rx_bytes,
                    "tx_bytes": client.tx_bytes,
                    "rx_rate_bps": client.rx_rate_bps,
                    "tx_rate_bps": client.tx_rate_bps,
                    "online_seconds": client.online_seconds,
                    "is_monitor_pc": is_monitor,
                }
            )
        capabilities = {
            name: getattr(snapshot.capabilities, name)
            for name in snapshot.capabilities.__dataclass_fields__
        }
        iptv = None
        if snapshot.iptv:
            iptv = {
                "state": snapshot.iptv.state,
                "rx_bytes": snapshot.iptv.rx_bytes,
                "tx_bytes": snapshot.iptv.tx_bytes,
                "evidence_field": snapshot.iptv.evidence_field,
            }
        return {
            "clients": clients,
            "wan_rx_bytes": snapshot.wan_rx_bytes,
            "wan_tx_bytes": snapshot.wan_tx_bytes,
            "iptv": iptv,
            "capabilities": capabilities,
            "raw_source": snapshot.raw_source,
            "warnings": snapshot.warnings,
        }
