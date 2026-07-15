from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class RoomStatus(StrEnum):
    NORMAL = "正常"
    PENDING = "待确认"
    SUSPECTED = "疑似异常"
    HIGH_CONFIDENCE = "高置信度异常"
    UNAVAILABLE = "能力不可用"
    INSUFFICIENT = "数据不足"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SYSTEM = "system"


@dataclass(slots=True)
class VisibleNetwork:
    ssid: str
    bssid: str | None = None
    signal_percent: int | None = None


@dataclass(slots=True)
class WifiConnection:
    ssid: str
    bssid: str | None
    profile: str | None
    state: str


@dataclass(slots=True)
class ConnectionResult:
    ok: bool
    reason: str
    connection: WifiConnection | None = None
    local_ipv4: str | None = None
    gateway: str | None = None


@dataclass(slots=True)
class ClientSnapshot:
    mac: str
    ip: str | None = None
    hostname: str | None = None
    connection_type: str | None = None
    rssi: int | None = None
    rx_bytes: int | None = None
    tx_bytes: int | None = None
    rx_rate_bps: int | None = None
    tx_rate_bps: int | None = None
    online_seconds: int | None = None
    last_seen: datetime | None = None


@dataclass(slots=True)
class IptvSnapshot:
    state: str | None = None
    rx_bytes: int | None = None
    tx_bytes: int | None = None
    evidence_field: str | None = None


@dataclass(slots=True)
class TvBusinessSnapshot:
    state: str | None = None
    hdmi_state: str | None = None
    cec_state: str | None = None
    evidence_field: str | None = None


@dataclass(slots=True)
class RouterCapabilities:
    client_list: bool = False
    client_ip: bool = False
    client_hostname: bool = False
    client_connection_type: bool = False
    client_rssi: bool = False
    client_total_bytes: bool = False
    client_realtime_rate: bool = False
    wan_total_bytes: bool = False
    iptv_state: bool = False
    iptv_interface_counters: bool = False
    stb_state: bool = False
    hdmi_state: bool = False
    cec_state: bool = False
    system_logs: bool = False
    json_api: bool = False
    html_scraping: bool = False
    login_automation: bool = False
    local_neighbor_discovery: bool = False
    ssdp_discovery: bool = False


@dataclass(slots=True)
class RouterSnapshot:
    room_id: str
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    router_reachable: bool = True
    clients: list[ClientSnapshot] = field(default_factory=list)
    wan_rx_bytes: int | None = None
    wan_tx_bytes: int | None = None
    iptv: IptvSnapshot | None = None
    tv_business: TvBusinessSnapshot | None = None
    capabilities: RouterCapabilities = field(default_factory=RouterCapabilities)
    raw_source: str = "unknown"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DetectionEvent:
    room_id: str
    event_type: str
    severity: Severity
    confidence: float
    reasons: list[str]
    limitations: list[str]
    evidence: dict[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
