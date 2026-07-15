from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from dataclasses import dataclass

from app.models.domain import ClientSnapshot, RouterCapabilities, RouterSnapshot
from app.wifi.windows_netsh import WindowsWifiManager


class LocalDiscoveryError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code

ARP_ENTRY_RE = re.compile(
    r"^\s*(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+"
    r"(?P<mac>[0-9a-f]{2}(?:[-:][0-9a-f]{2}){5})\s+",
    re.IGNORECASE,
)
MEDIA_MARKERS = (
    "mediarenderer",
    "mediaserver",
    "dial-multiscreen",
    "avtransport",
    "roku",
)
SSDP_TARGETS = (
    "ssdp:all",
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:dial-multiscreen-org:service:dial:1",
)


@dataclass(frozen=True, slots=True)
class SsdpObservation:
    source_ip: str
    usn: str
    service_type: str
    server: str

    @property
    def is_media_device(self) -> bool:
        haystack = f"{self.usn} {self.service_type} {self.server}".lower()
        return any(marker in haystack for marker in MEDIA_MARKERS)


def parse_arp_table(output: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in output.splitlines():
        match = ARP_ENTRY_RE.match(line)
        if not match:
            continue
        mac = match.group("mac").replace("-", ":").lower()
        if mac != "ff:ff:ff:ff:ff:ff" and not mac.startswith("01:00:5e"):
            entries[match.group("ip")] = mac
    return entries


def parse_ssdp_response(payload: bytes, source_ip: str) -> SsdpObservation | None:
    text = payload.decode("iso-8859-1", errors="replace")
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or "200 OK" not in lines[0].upper():
        return None
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    usn = headers.get("usn", "")
    service_type = headers.get("st", "")
    server = headers.get("server", "")
    if not (usn or service_type or server):
        return None
    return SsdpObservation(source_ip, usn, service_type, server)


def discover_ssdp(local_ipv4: str, timeout_seconds: float = 2.0) -> list[SsdpObservation]:
    observations: dict[tuple[str, str, str], SsdpObservation] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ipv4))
        sock.bind((local_ipv4, 0))
        sock.settimeout(0.2)
        for target in SSDP_TARGETS:
            message = (
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                'MAN: "ssdp:discover"\r\n'
                "MX: 1\r\n"
                f"ST: {target}\r\n\r\n"
            ).encode("ascii")
            sock.sendto(message, ("239.255.255.250", 1900))
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                payload, address = sock.recvfrom(65_535)
            except TimeoutError:
                continue
            observation = parse_ssdp_response(payload, address[0])
            if observation:
                key = (observation.source_ip, observation.usn, observation.service_type)
                observations[key] = observation
    return list(observations.values())


class LocalPcAdapter:
    """Discover only what the authorized Windows client can observe without router login."""

    def __init__(
        self,
        room_id: str,
        expected_ssid: str,
        *,
        wifi_profile: str | None = None,
        expected_bssid: str | None = None,
        ping_sweep: bool = False,
        ssdp_timeout_seconds: float = 2.0,
    ) -> None:
        self.room_id = room_id
        self.expected_ssid = expected_ssid
        self.wifi_profile = wifi_profile or expected_ssid
        self.expected_bssid = expected_bssid
        self.ping_sweep = ping_sweep
        self.ssdp_timeout_seconds = ssdp_timeout_seconds
        self.wifi = WindowsWifiManager()
        self.local_ipv4: str | None = None
        self.gateway: str | None = None

    async def probe(self) -> RouterCapabilities:
        return RouterCapabilities(local_neighbor_discovery=True, ssdp_discovery=True)

    async def login(self) -> None:
        result = await self.wifi.connect(
            self.wifi_profile, self.expected_ssid, self.expected_bssid
        )
        if not result.ok:
            raise LocalDiscoveryError(result.reason)
        self.local_ipv4 = result.local_ipv4
        self.gateway = result.gateway

    async def fetch_snapshot(self) -> RouterSnapshot:
        if not self.local_ipv4 or not self.gateway:
            raise RuntimeError("必须先验证本机 Wi-Fi 连接")
        responsive = (
            await self._ping_sweep(self.local_ipv4, self.gateway)
            if self.ping_sweep
            else set()
        )
        observations = await asyncio.to_thread(
            discover_ssdp, self.local_ipv4, self.ssdp_timeout_seconds
        )
        arp_output = await self._run("arp", "-a")
        neighbors = parse_arp_table(arp_output)
        by_identity: dict[str, ClientSnapshot] = {}
        excluded = {self.local_ipv4, self.gateway}
        for ip in sorted(responsive - excluded):
            mac = neighbors.get(ip)
            if mac:
                by_identity[mac] = ClientSnapshot(mac=mac, connection_type="icmp-neighbor")
        for observation in observations:
            if observation.source_ip in excluded:
                continue
            identity = neighbors.get(observation.source_ip)
            if not identity:
                stable_hint = observation.usn or observation.source_ip
                identity = f"ssdp:{stable_hint}"
            connection_type = (
                "ssdp-media-device" if observation.is_media_device else "ssdp-device"
            )
            current = by_identity.get(identity)
            if current is None or connection_type == "ssdp-media-device":
                by_identity[identity] = ClientSnapshot(
                    mac=identity,
                    connection_type=connection_type,
                )
        warnings = [
            "仅包含本机 ICMP/ARP 与 SSDP 可见设备，不是完整路由器客户端列表",
            "设备可见不等于电视亮屏、正在播放或有人观看",
            "未采集数据包正文、域名、端口扫描结果或逐设备流量",
        ]
        if not observations:
            warnings.append("本轮没有收到 SSDP 响应；可能存在客户端隔离或设备未广播")
        return RouterSnapshot(
            room_id=self.room_id,
            clients=list(by_identity.values()),
            capabilities=await self.probe(),
            raw_source="pc-local",
            warnings=warnings,
        )

    async def logout(self) -> None:
        return None

    @staticmethod
    async def _run(*args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        if process.returncode:
            raise RuntimeError(f"命令失败：{args[0]}（退出码 {process.returncode}）")
        return stdout.decode("mbcs", errors="replace")

    @staticmethod
    async def _ping_sweep(local_ipv4: str, gateway: str) -> set[str]:
        network = ipaddress.ip_network(f"{local_ipv4}/24", strict=False)
        semaphore = asyncio.Semaphore(32)

        async def ping(address: str) -> str | None:
            if address in {local_ipv4, gateway}:
                return None
            async with semaphore:
                process = await asyncio.create_subprocess_exec(
                    "ping",
                    "-n",
                    "1",
                    "-w",
                    "250",
                    address,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                try:
                    await asyncio.wait_for(process.wait(), timeout=1.5)
                except TimeoutError:
                    process.kill()
                    await process.wait()
                    return None
                return address if process.returncode == 0 else None

        results = await asyncio.gather(*(ping(str(host)) for host in network.hosts()))
        return {result for result in results if result is not None}
