from pathlib import Path

from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


def test_dashboard_and_api(tmp_path: Path) -> None:
    settings = load_settings()
    settings.app.inter_room_pause_seconds = 0
    with TestClient(create_app(settings, tmp_path / "web.db")) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "真实台账与可见信号" in response.text
        scan = client.post("/api/scan-cycle")
        assert scan.status_code == 200
        rooms = client.get("/api/rooms").json()
        assert len(rooms) == 8
        assert all("devices" in room for room in rooms)
        assert all("reported_devices" in room for room in rooms)
        assert any(
            device["probable_type"] == "电视"
            for room in rooms
            for device in room["devices"]
        )
        room_page = client.get("/rooms/2307")
        assert "设备台账" in room_page.text
        detail = client.get("/api/rooms/2307").json()
        assert detail["devices"]
        assert all("activity_label" in device for device in detail["devices"])
        assert client.get("/api/health").json()["mode"] == "mock"


def test_clear_requires_exact_confirmation(tmp_path: Path) -> None:
    with TestClient(create_app(load_settings(), tmp_path / "web.db")) as client:
        assert client.post("/api/clear", json={"confirmation": "wrong"}).status_code == 400


def test_field_test_dashboard_uses_configured_room_count(tmp_path: Path) -> None:
    settings = load_settings(Path("config/rooms.2312.field.yaml"))
    with TestClient(create_app(settings, tmp_path / "field.db")) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "1 个已配置房间" in response.text
        rooms = client.get("/api/rooms").json()
        assert [room["room_id"] for room in rooms] == ["2312"]


def test_reported_inventory_works_without_automatic_sample(tmp_path: Path) -> None:
    settings = load_settings(Path("config/rooms.2312.field.yaml"))
    with TestClient(create_app(settings, tmp_path / "field.db")) as client:
        payload = {
            "room_id": "2312",
            "label": "手机 1",
            "device_type": "手机",
            "usage_state": "已连接（使用未知）",
            "note": "",
        }
        created = client.post("/api/reported-devices", json=payload)
        assert created.status_code == 200
        device_id = created.json()["id"]
        detail = client.get("/api/rooms/2312")
        assert detail.status_code == 200
        assert detail.json()["reported_devices"][0]["label"] == "手机 1"
        payload["usage_state"] = "离线"
        assert client.put(f"/api/reported-devices/{device_id}", json=payload).status_code == 200
        assert client.get("/api/rooms").json()[0]["reported_devices"][0]["usage_state"] == "离线"
        assert client.delete(f"/api/reported-devices/{device_id}").status_code == 200


def test_reported_inventory_rejects_unknown_room_and_state(tmp_path: Path) -> None:
    with TestClient(create_app(load_settings(), tmp_path / "web.db")) as client:
        payload = {
            "room_id": "9999",
            "label": "设备",
            "device_type": "其他",
            "usage_state": "未知",
            "note": "",
        }
        assert client.post("/api/reported-devices", json=payload).status_code == 400
        payload["room_id"] = "2301"
        payload["usage_state"] = "随便"
        assert client.post("/api/reported-devices", json=payload).status_code == 422
