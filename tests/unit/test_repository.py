from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.models.domain import DetectionEvent, RouterSnapshot, Severity
from app.storage.repository import Repository


def test_repository_wal_review_and_retention(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "data.db")
    snapshot = RouterSnapshot(room_id="2301")
    repository.add_sample(snapshot, {"clients": []})
    event = DetectionEvent(
        "2301", "unknown_device_seen", Severity.LOW, 0.5, ["reason"], ["limit"], {}
    )
    event_id = repository.add_event(event)
    assert repository.review_event(event_id, "误报", "测试")
    assert repository.recent_events()[0]["review_status"] == "误报"
    old = (datetime.now(UTC) - timedelta(hours=100)).isoformat()
    with repository.connection() as db:
        db.execute("UPDATE samples SET captured_at=?", (old,))
    assert repository.purge(72)["samples"] == 1


def test_allowlist_upsert(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "data.db")
    repository.upsert_allowlist("2307", "dev_0123456789abcdef", "海信电视")
    assert repository.allowed_devices("2307")["dev_0123456789abcdef"] == "海信电视"


def test_open_event_is_refreshed_not_duplicated(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "data.db")
    event = DetectionEvent(
        "2305",
        "unknown_device_active",
        Severity.MEDIUM,
        0.72,
        ["reason"],
        ["limit"],
        {"device_id": "dev_0123456789abcdef"},
    )
    first = repository.add_event(event)
    second = repository.add_event(event)
    assert first == second
    rows = repository.recent_events()
    assert len(rows) == 1
    assert rows[0]["occurrence_count"] == 2
    assert repository.close_absent_events("2305", []) == 1
    third = repository.add_event(event)
    assert third != first


def test_latest_scan_status_exposes_room_failure_without_sensitive_detail(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "data.db")
    repository.record_scan_status("2301", False, "wifi_profile_missing")
    status = repository.latest_scan_statuses()["2301"]
    assert status["ok"] is False
    assert status["error_code"] == "wifi_profile_missing"


def test_reported_device_crud_is_separate_from_automatic_samples(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "data.db")
    device_id = repository.add_reported_device(
        "2312", "电脑 1", "个人电脑", "已连接（使用未知）"
    )
    devices = repository.reported_devices("2312")
    assert devices[0]["id"] == device_id
    assert devices[0]["source"] == "现场确认"
    assert repository.update_reported_device(
        device_id, "2312", "电脑 1", "个人电脑", "使用中", "现场复核"
    )
    assert repository.reported_devices("2312")[0]["usage_state"] == "使用中"
    assert repository.delete_reported_device(device_id)
    assert repository.reported_devices("2312") == []
