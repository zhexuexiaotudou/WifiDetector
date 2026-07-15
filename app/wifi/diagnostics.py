from __future__ import annotations

import asyncio
import importlib.util
import platform
import shutil
import socket
import sys
from pathlib import Path
from typing import Any

from app.config import Settings
from app.wifi.windows_netsh import WindowsWifiManager, safe_connection_summary


async def run_doctor(settings: Settings, database: Path) -> dict[str, Any]:
    wifi = WindowsWifiManager()
    profiles: list[str] = []
    current = None
    wifi_error = None
    try:
        profiles = await wifi.list_profiles()
        current = await wifi.current_connection()
    except (OSError, RuntimeError) as exc:
        wifi_error = str(exc)
    required = [room.wifi_profile for room in settings.rooms if room.enabled]
    missing = [profile for profile in required if profile not in profiles]
    database.parent.mkdir(parents=True, exist_ok=True)
    writable = database.parent.exists() and database.parent.is_dir()
    port_available = await asyncio.to_thread(_port_available, settings.app.dashboard_port)
    edge = shutil.which("msedge") or _find_edge()
    return {
        "windows": platform.platform(),
        "python": sys.version.split()[0],
        "edge_installed": bool(edge),
        "wifi_available": wifi_error is None,
        "wifi_error": wifi_error,
        "current_connection": safe_connection_summary(current),
        "required_profiles": required,
        "missing_profiles": missing,
        "config_valid": True,
        "database_writable": writable,
        "dashboard_host_local_only": settings.app.dashboard_host
        in {"127.0.0.1", "localhost", "::1"},
        "port_available": port_available,
        "playwright_installed": importlib.util.find_spec("playwright") is not None,
        "ready_for_gate_a": not missing and wifi_error is None,
    }


def _port_available(port: int) -> bool:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _find_edge() -> str | None:
    candidates = [
        Path.home() / "AppData/Local/Microsoft/Edge/Application/msedge.exe",
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    ]
    return str(next((path for path in candidates if path.exists()), "")) or None
