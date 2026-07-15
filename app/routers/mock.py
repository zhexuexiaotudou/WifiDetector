from __future__ import annotations

from datetime import UTC, datetime

from app.models.domain import (
    ClientSnapshot,
    IptvSnapshot,
    RouterCapabilities,
    RouterSnapshot,
)


class MockAdapter:
    """Deterministic adapter used for demonstrations, tests, and soak runs."""

    def __init__(self, room_id: str, cycle: int = 1) -> None:
        self.room_id = room_id
        self.cycle = cycle

    async def probe(self) -> RouterCapabilities:
        return RouterCapabilities(
            client_list=True,
            client_ip=True,
            client_hostname=True,
            client_connection_type=True,
            client_rssi=True,
            client_total_bytes=True,
            client_realtime_rate=True,
            wan_total_bytes=True,
            iptv_state=self.room_id == "2309",
            iptv_interface_counters=self.room_id in {"2309", "2310"},
            json_api=True,
        )

    async def login(self) -> None:
        return None

    async def fetch_snapshot(self) -> RouterSnapshot:
        capabilities = await self.probe()
        base = self.cycle * 1_000_000
        clients = [
            ClientSnapshot(
                mac="02:00:00:00:00:01",
                ip="192.168.1.100",
                hostname="monitor-pc",
                connection_type="wifi",
                rx_bytes=base + 10_000,
                tx_bytes=base // 5,
                rx_rate_bps=2_000,
                tx_rate_bps=500,
                online_seconds=self.cycle * 180,
            )
        ]
        room_devices = {
            "2301": ClientSnapshot(
                mac="02:00:00:00:01:11", hostname="iphone-mobile", connection_type="wifi",
                rx_rate_bps=180_000, tx_rate_bps=24_000, online_seconds=self.cycle * 180,
            ),
            "2302": ClientSnapshot(
                mac="02:00:00:00:02:12", hostname="ipad-tablet", connection_type="wifi",
                rx_rate_bps=42_000, tx_rate_bps=8_000, online_seconds=self.cycle * 180,
            ),
            "2303": ClientSnapshot(
                mac="02:00:00:00:03:13", hostname="windows-laptop", connection_type="wifi",
                rx_rate_bps=6_000, tx_rate_bps=2_000, online_seconds=self.cycle * 180,
            ),
            "2306": ClientSnapshot(
                mac="02:00:00:00:06:16", hostname="mobile-phone", connection_type="wifi",
                rx_rate_bps=0, tx_rate_bps=0, online_seconds=self.cycle * 180,
            ),
        }
        if self.room_id in room_devices:
            clients.append(room_devices[self.room_id])
        warnings: list[str] = []
        iptv = None
        if self.room_id == "2305":
            clients.append(
                ClientSnapshot(
                    mac="02:00:00:00:05:99",
                    ip="192.168.1.120",
                    hostname="",
                    connection_type="wifi",
                    rx_bytes=base * 9,
                    tx_bytes=base,
                    rx_rate_bps=800_000,
                    tx_rate_bps=50_000,
                    online_seconds=self.cycle * 180,
                )
            )
        elif self.room_id == "2307":
            clients.append(
                ClientSnapshot(
                    mac="02:00:00:00:07:53",
                    ip="192.168.1.53",
                    hostname="hisense-tv",
                    connection_type="wifi",
                    rx_bytes=base * 20,
                    tx_bytes=base,
                    rx_rate_bps=4_000_000,
                    tx_rate_bps=20_000,
                    online_seconds=self.cycle * 180,
                )
            )
        elif self.room_id == "2309":
            iptv = IptvSnapshot(state="active", rx_bytes=base * 30, evidence_field="iptv.state")
        elif self.room_id == "2310":
            iptv = IptvSnapshot(state=None, rx_bytes=base * 15, evidence_field="iptv.rx_bytes")
            warnings.append("仅有 IPTV 接口计数，无明确业务状态")
        return RouterSnapshot(
            room_id=self.room_id,
            captured_at=datetime.now(UTC),
            clients=clients,
            wan_rx_bytes=base * (40 if self.room_id in {"2309", "2310"} else 3),
            wan_tx_bytes=base,
            iptv=iptv,
            capabilities=capabilities,
            raw_source="mock",
            warnings=warnings,
        )

    async def logout(self) -> None:
        return None
