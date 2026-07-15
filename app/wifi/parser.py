from __future__ import annotations

import re

from app.models.domain import VisibleNetwork, WifiConnection

VALUE_RE = re.compile(r"^\s*([^:]+?)\s*:\s*(.*?)\s*$")
BSSID_RE = re.compile(r"(?i)^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")


def _pairs(output: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for line in output.splitlines():
        match = VALUE_RE.match(line)
        if match:
            result.append((match.group(1).strip().lower(), match.group(2).strip()))
    return result


def parse_profiles(output: str) -> list[str]:
    profiles: list[str] = []
    for key, value in _pairs(output):
        if "profile" in key and value and "<none>" not in value.lower():
            profiles.append(value)
    return list(dict.fromkeys(profiles))


def parse_interfaces(output: str) -> WifiConnection | None:
    values = dict(_pairs(output))
    state = values.get("state") or values.get("状态") or ""
    if state.lower() not in {"connected", "已连接"}:
        return None
    ssid = values.get("ssid")
    if not ssid:
        return None
    bssid = values.get("ap bssid") or values.get("bssid")
    profile = values.get("profile") or values.get("配置文件")
    return WifiConnection(ssid=ssid, bssid=bssid, profile=profile, state=state)


def parse_networks(output: str) -> list[VisibleNetwork]:
    networks: list[VisibleNetwork] = []
    current_ssid: str | None = None
    for key, value in _pairs(output):
        if key.startswith("ssid ") and value:
            current_ssid = value
            networks.append(VisibleNetwork(ssid=value))
        elif key.startswith("bssid ") and current_ssid and networks and BSSID_RE.match(value):
            networks[-1].bssid = value.lower()
        elif key in {"signal", "信号"} and networks:
            try:
                networks[-1].signal_percent = int(value.rstrip("%"))
            except ValueError:
                pass
    return networks


def parse_ipconfig(output: str) -> tuple[str | None, str | None]:
    ipv4: str | None = None
    gateway: str | None = None
    for key, value in _pairs(output):
        lowered = key.lower()
        if "ipv4" in lowered and re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", value):
            ipv4 = value
        elif ("default gateway" in lowered or "默认网关" in lowered) and re.fullmatch(
            r"\d{1,3}(?:\.\d{1,3}){3}", value
        ):
            gateway = value
    return ipv4, gateway
