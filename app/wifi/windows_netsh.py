from __future__ import annotations

import asyncio
import locale
import re

from app.models.domain import ConnectionResult, VisibleNetwork, WifiConnection
from app.wifi.parser import parse_interfaces, parse_ipconfig, parse_networks, parse_profiles


class WindowsWifiManager:
    def __init__(self, timeout_seconds: int = 18) -> None:
        self.timeout_seconds = timeout_seconds

    async def _run(self, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=self.timeout_seconds)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError(f"命令超时：{args[0]}") from None
        encoding = locale.getpreferredencoding(False) or "utf-8"
        output = stdout.decode(encoding, errors="replace")
        if process.returncode:
            raise RuntimeError(f"命令失败：{args[0]}（退出码 {process.returncode}）")
        return output

    async def list_profiles(self) -> list[str]:
        return parse_profiles(await self._run("netsh", "wlan", "show", "profiles"))

    async def scan_networks(self) -> list[VisibleNetwork]:
        return parse_networks(await self._run("netsh", "wlan", "show", "networks", "mode=bssid"))

    async def current_connection(self) -> WifiConnection | None:
        return parse_interfaces(await self._run("netsh", "wlan", "show", "interfaces"))

    async def current_ipv4(self) -> str | None:
        ipv4, _ = parse_ipconfig(await self._run("ipconfig"))
        return ipv4

    async def default_gateway(self) -> str | None:
        _, gateway = parse_ipconfig(await self._run("ipconfig"))
        return gateway

    async def connect(
        self, profile_name: str, expected_ssid: str, expected_bssid: str | None = None
    ) -> ConnectionResult:
        profiles = await self.list_profiles()
        if profile_name not in profiles:
            return ConnectionResult(False, "wifi_profile_missing")
        visible = await self.scan_networks()
        if expected_ssid not in {network.ssid for network in visible}:
            return ConnectionResult(False, "ssid_not_visible")
        await self._run("netsh", "wlan", "connect", f"name={profile_name}")
        deadline = asyncio.get_running_loop().time() + self.timeout_seconds
        connection: WifiConnection | None = None
        while asyncio.get_running_loop().time() < deadline:
            connection = await self.current_connection()
            if connection and connection.ssid == expected_ssid:
                break
            await asyncio.sleep(0.5)
        if not connection:
            return ConnectionResult(False, "wifi_connect_failed")
        if connection.ssid != expected_ssid:
            return ConnectionResult(False, "wrong_ssid", connection)
        if expected_bssid and (connection.bssid or "").lower() != expected_bssid.lower():
            return ConnectionResult(False, "wrong_bssid", connection)
        ipv4 = await self.current_ipv4()
        gateway = await self.default_gateway()
        if not ipv4:
            return ConnectionResult(False, "dhcp_timeout", connection)
        if gateway != "192.168.1.1":
            return ConnectionResult(False, "router_unreachable", connection, ipv4, gateway)
        return ConnectionResult(True, "connected", connection, ipv4, gateway)

    async def disconnect(self) -> None:
        await self._run("netsh", "wlan", "disconnect")


def safe_connection_summary(connection: WifiConnection | None) -> dict[str, str | None]:
    if not connection:
        return {"state": "disconnected", "ssid": None, "bssid": None}
    masked_bssid = None
    if connection.bssid and re.fullmatch(r"(?i)[0-9a-f]{2}(?::[0-9a-f]{2}){5}", connection.bssid):
        masked_bssid = "**:**:**:**:" + connection.bssid[-5:]
    return {"state": connection.state, "ssid": connection.ssid, "bssid": masked_bssid}
