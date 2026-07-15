from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import load_settings


def test_example_configuration_has_exact_room_set() -> None:
    settings = load_settings()
    assert [room.room_id for room in settings.rooms] == [
        "2301",
        "2302",
        "2303",
        "2305",
        "2306",
        "2307",
        "2309",
        "2310",
    ]
    assert settings.app.dashboard_host == "127.0.0.1"


def test_non_local_dashboard_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "rooms.yaml"
    original = Path("config/rooms.example.yaml").read_text(encoding="utf-8")
    path.write_text(
        original.replace('dashboard_host: "127.0.0.1"', 'dashboard_host: "0.0.0.0"'),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="回环"):
        load_settings(path)


def test_room_ssid_mismatch_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "rooms.yaml"
    original = Path("config/rooms.example.yaml").read_text(encoding="utf-8")
    path.write_text(original.replace('ssid: "2301"', 'ssid: "wrong"', 1), encoding="utf-8")
    with pytest.raises(ValidationError, match="SSID"):
        load_settings(path)
