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
        assert "夜间态势总览" in response.text
        scan = client.post("/api/scan-cycle")
        assert scan.status_code == 200
        rooms = client.get("/api/rooms").json()
        assert len(rooms) == 8
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
