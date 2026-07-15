from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

ROOM_IDS = ("2301", "2302", "2303", "2305", "2306", "2307", "2309", "2310")


class AppConfig(BaseModel):
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = Field(default=8765, ge=1024, le=65535)
    retention_hours: int = Field(default=72, ge=1, le=8760)
    scheduler_enabled: bool = True
    mock_mode: bool = True
    per_room_connect_timeout_seconds: int = Field(default=18, ge=3, le=120)
    per_room_scan_timeout_seconds: int = Field(default=20, ge=3, le=180)
    inter_room_pause_seconds: float = Field(default=2, ge=0, le=60)
    cycle_pause_seconds: float = Field(default=5, ge=0, le=3600)
    max_sample_age_minutes: int = Field(default=6, ge=1, le=1440)
    unknown_persistent_minutes: int = Field(default=10, ge=1, le=1440)

    @model_validator(mode="after")
    def local_only(self) -> AppConfig:
        if self.dashboard_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("dashboard_host 必须是本机回环地址")
        return self


class RoomConfig(BaseModel):
    room_id: str
    ssid: str
    wifi_profile: str
    router_url: str = "http://192.168.1.1"
    expected_bssid: str | None = None
    credential_key: str = "h10e31_shared_admin"
    enabled: bool = True

    @model_validator(mode="after")
    def validate_room(self) -> RoomConfig:
        if self.room_id != self.ssid:
            raise ValueError(f"房间 {self.room_id} 的 SSID 必须与房间号一致")
        if not self.router_url.startswith(("http://192.168.1.1", "https://192.168.1.1")):
            raise ValueError("MVP 仅允许访问已授权的 192.168.1.1 管理地址")
        return self


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    rooms: list[RoomConfig]

    @model_validator(mode="after")
    def validate_rooms(self) -> Settings:
        ids = [room.room_id for room in self.rooms]
        if len(ids) != len(set(ids)):
            raise ValueError("房间号不得重复")
        if set(ids) != set(ROOM_IDS):
            raise ValueError(f"必须且只能配置 8 个指定房间：{', '.join(ROOM_IDS)}")
        return self


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_settings(path: Path | None = None) -> Settings:
    configured = path or Path(os.getenv("DORM_MONITOR_CONFIG", "config/rooms.example.yaml"))
    if not configured.is_absolute():
        configured = project_root() / configured
    with configured.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return Settings.model_validate(data)


def database_path() -> Path:
    configured = Path(os.getenv("DORM_MONITOR_DATABASE", "private_artifacts/dorm_monitor.db"))
    if not configured.is_absolute():
        configured = project_root() / configured
    configured.parent.mkdir(parents=True, exist_ok=True)
    return configured
