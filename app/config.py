from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

ROOM_IDS = ("2301", "2302", "2303", "2305", "2306", "2307", "2309", "2310")


class AppConfig(BaseModel):
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = Field(default=8765, ge=1024, le=65535)
    retention_hours: int = Field(default=72, ge=1, le=8760)
    scheduler_enabled: bool = True
    mock_mode: bool = True
    field_test_mode: bool = False
    field_data_source: Literal["router", "local_pc"] = "router"
    local_ping_sweep: bool = False
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
        if self.local_ping_sweep and self.field_data_source != "local_pc":
            raise ValueError("local_ping_sweep 只允许用于 local_pc 数据源")
        return self


class RoomConfig(BaseModel):
    room_id: str = Field(pattern=r"^\d{4}$")
    ssid: str
    wifi_profile: str
    router_url: str = "http://192.168.1.1"
    expected_bssid: str | None = None
    credential_key: str = "h10e31_shared_admin"
    enabled: bool = True

    @model_validator(mode="after")
    def validate_room(self) -> RoomConfig:
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
        if self.app.field_test_mode:
            if len(ids) != 1:
                raise ValueError("现场测试模式必须且只能配置一个已授权房间")
        else:
            if set(ids) != set(ROOM_IDS):
                raise ValueError(f"必须且只能配置 8 个指定房间：{', '.join(ROOM_IDS)}")
            if any(room.room_id != room.ssid for room in self.rooms):
                raise ValueError("正式八房间配置的 SSID 必须与房间号一致")
        return self


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_environment() -> None:
    """Load local environment defaults without overriding the parent process."""
    load_dotenv(project_root() / ".env", override=False)


def log_level() -> str:
    load_environment()
    return os.getenv("DORM_MONITOR_LOG_LEVEL", "INFO")


def load_settings(path: Path | None = None) -> Settings:
    load_environment()
    configured = path or Path(os.getenv("DORM_MONITOR_CONFIG", "config/rooms.example.yaml"))
    if not configured.is_absolute():
        configured = project_root() / configured
    with configured.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return Settings.model_validate(data)


def database_path() -> Path:
    load_environment()
    configured = Path(os.getenv("DORM_MONITOR_DATABASE", "private_artifacts/dorm_monitor.db"))
    if not configured.is_absolute():
        configured = project_root() / configured
    configured.parent.mkdir(parents=True, exist_ok=True)
    return configured
