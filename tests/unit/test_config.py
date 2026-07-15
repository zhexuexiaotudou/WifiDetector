from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import load_environment, load_settings, log_level, project_root


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


def test_local_env_is_loaded_without_overriding_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Path, bool]] = []

    def fake_load_dotenv(path: Path, *, override: bool) -> bool:
        calls.append((path, override))
        return True

    monkeypatch.setattr("app.config.load_dotenv", fake_load_dotenv)
    load_environment()
    assert calls == [(project_root() / ".env", False)]


def test_log_level_comes_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DORM_MONITOR_LOG_LEVEL", "DEBUG")
    assert log_level() == "DEBUG"


def test_single_authorized_field_room_can_use_a_different_ssid() -> None:
    settings = load_settings(Path("config/rooms.2312.field.yaml"))
    assert settings.app.field_test_mode is True
    assert settings.app.mock_mode is False
    assert settings.app.field_data_source == "local_pc"
    assert settings.app.local_ping_sweep is True
    assert [(room.room_id, room.ssid) for room in settings.rooms] == [("2312", "CMCC-2312")]


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
