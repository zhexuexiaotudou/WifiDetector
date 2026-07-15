from pathlib import Path

import pytest

from app.config import load_settings
from app.routers.local_pc import LocalPcAdapter
from app.scheduler.health import HEALTH
from app.scheduler.rotating_scanner import RotatingScanner
from app.storage.repository import Repository


@pytest.mark.asyncio
async def test_all_eight_rooms_complete_and_scenarios_are_visible(tmp_path: Path) -> None:
    settings = load_settings()
    settings.app.inter_room_pause_seconds = 0
    repository = Repository(tmp_path / "data.db")
    scanner = RotatingScanner(settings, repository, salt_file=tmp_path / "salt")
    result = await scanner.scan_cycle()
    assert len(result["rooms"]) == 8
    assert len(repository.latest_rooms()) == 8
    events = repository.recent_events(limit=100)
    assert any(
        event["room_id"] == "2305" and event["event_type"] == "unknown_device_active"
        for event in events
    )
    assert any(
        event["room_id"] == "2309" and event["event_type"] == "iptv_active" for event in events
    )
    assert any(
        event["room_id"] == "2310" and event["event_type"] == "iptv_traffic_observed"
        for event in events
    )
    assert "mac" not in str(repository.latest_rooms()).lower()
    assert HEALTH.running is False


@pytest.mark.asyncio
async def test_accelerated_soak(tmp_path: Path) -> None:
    settings = load_settings()
    settings.app.inter_room_pause_seconds = 0
    repository = Repository(tmp_path / "soak.db")
    scanner = RotatingScanner(settings, repository, salt_file=tmp_path / "salt")
    for _ in range(25):
        result = await scanner.scan_cycle()
        assert len(result["rooms"]) == 8
    with repository.connection() as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    assert integrity == "ok"


def test_field_mode_never_falls_back_to_mock_data(tmp_path: Path) -> None:
    settings = load_settings(Path("config/rooms.2312.field.yaml"))
    repository = Repository(tmp_path / "field.db")
    scanner = RotatingScanner(settings, repository, salt_file=tmp_path / "salt")
    assert isinstance(scanner.adapter_factory("2312", 1), LocalPcAdapter)
