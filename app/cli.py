from __future__ import annotations

import argparse
import asyncio
import gc
import json
import sys
import tracemalloc
from datetime import date
from typing import Any

from app.config import ROOM_IDS, database_path, load_settings, project_root
from app.logging_config import configure_logging
from app.routers.discovery import discover_router
from app.routers.h10e31 import H10e31Adapter
from app.scheduler.rotating_scanner import RotatingScanner
from app.storage.export import export_daily
from app.storage.repository import Repository
from app.wifi.diagnostics import run_doctor
from app.wifi.windows_netsh import WindowsWifiManager, safe_connection_summary


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="授权宿舍网关的本地只读监测工具")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("profiles")
    for name in ("connect-test", "discover", "probe", "calibrate", "scan-once"):
        item = commands.add_parser(name)
        item.add_argument("--room", required=True, choices=ROOM_IDS)
    commands.add_parser("scan-cycle")
    commands.add_parser("run")
    export = commands.add_parser("export")
    export.add_argument("--date", required=True)
    purge = commands.add_parser("purge")
    purge.add_argument("--older-than-hours", type=int, default=72)
    soak = commands.add_parser("soak")
    soak.add_argument("--cycles", type=int, default=300)
    return root


async def execute(args: argparse.Namespace) -> Any:
    settings = load_settings()
    repository = Repository(database_path())
    if args.command == "doctor":
        return await run_doctor(settings, repository.path)
    if args.command == "profiles":
        manager = WindowsWifiManager()
        return {"profiles": await manager.list_profiles()}
    if args.command == "connect-test":
        room = next(room for room in settings.rooms if room.room_id == args.room)
        manager = WindowsWifiManager(settings.app.per_room_connect_timeout_seconds)
        result = await manager.connect(room.wifi_profile, room.ssid, room.expected_bssid)
        return {
            "ok": result.ok,
            "reason": result.reason,
            "connection": safe_connection_summary(result.connection),
            "local_ipv4": result.local_ipv4,
            "gateway": result.gateway,
        }
    if args.command == "discover":
        room = next(room for room in settings.rooms if room.room_id == args.room)
        manager = WindowsWifiManager(settings.app.per_room_connect_timeout_seconds)
        result = await manager.connect(room.wifi_profile, room.ssid, room.expected_bssid)
        if not result.ok:
            raise RuntimeError(f"现场 Gate A 未通过：{result.reason}")
        output = await discover_router(
            room.room_id, room.router_url, project_root() / "artifacts/sanitized_discovery"
        )
        return {"sanitized_evidence": str(output)}
    if args.command == "probe":
        capabilities = await H10e31Adapter(args.room).probe()
        return {
            "room_id": args.room,
            "verified_capabilities": {
                key: getattr(capabilities, key) for key in capabilities.__dataclass_fields__
            },
            "status": "等待真实脱敏发现证据",
        }
    if args.command == "calibrate":
        return {
            "room_id": args.room,
            "status": "需要授权现场人工向导",
            "scenarios": ["全部空闲", "电视待机", "智能电视应用播放", "HDMI/IPTV 播放"],
            "minimum_minutes_per_scenario": 5,
            "warning": "首批设备不会自动加入白名单，阈值不得硬编码",
        }
    scanner = RotatingScanner(settings, repository)
    if args.command == "scan-once":
        return {"room_id": args.room, "event_ids": await scanner.scan_room(args.room, 1)}
    if args.command == "scan-cycle":
        return await scanner.scan_cycle()
    if args.command == "soak":
        original_pause = settings.app.inter_room_pause_seconds
        settings.app.inter_room_pause_seconds = 0
        tracemalloc.start()
        baseline_bytes = 0
        baseline_snapshot: tracemalloc.Snapshot | None = None
        warmup_cycle = min(max(9, args.cycles // 3), args.cycles - 1)
        try:
            for cycle_index in range(args.cycles):
                await scanner.scan_cycle()
                if cycle_index == warmup_cycle:
                    gc.collect()
                    baseline_bytes = tracemalloc.get_traced_memory()[0]
                    baseline_snapshot = tracemalloc.take_snapshot()
        finally:
            settings.app.inter_room_pause_seconds = original_pause
        gc.collect()
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        end_snapshot = tracemalloc.take_snapshot()
        growth_top = []
        if baseline_snapshot is not None:
            growth_top = [
                {
                    "location": str(stat.traceback[0]),
                    "size_diff": stat.size_diff,
                    "count_diff": stat.count_diff,
                }
                for stat in end_snapshot.compare_to(baseline_snapshot, "lineno")[:5]
            ]
        tracemalloc.stop()
        with repository.connection() as db:
            integrity = str(db.execute("PRAGMA integrity_check").fetchone()[0])
            sample_count = int(db.execute("SELECT COUNT(*) FROM samples").fetchone()[0])
            event_count = int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
            open_event_count = int(
                db.execute("SELECT COUNT(*) FROM events WHERE open=1").fetchone()[0]
            )
        return {
            "cycles": args.cycles,
            "rooms_per_cycle": len(settings.rooms),
            "status": "completed",
            "sqlite_integrity": integrity,
            "sample_count": sample_count,
            "event_count": event_count,
            "open_event_count": open_event_count,
            "tracemalloc_current_bytes": current_bytes,
            "tracemalloc_peak_bytes": peak_bytes,
            "post_warmup_growth_bytes": max(0, current_bytes - baseline_bytes),
            "allocation_growth_top": growth_top,
        }
    if args.command == "purge":
        if args.older_than_hours < 1:
            raise ValueError("保留时间必须至少为 1 小时")
        return repository.purge(args.older_than_hours)
    if args.command == "export":
        paths = export_daily(
            repository,
            date.fromisoformat(args.date),
            project_root() / "artifacts/reports",
        )
        return {key: str(value) for key, value in paths.items()}
    if args.command == "run":
        import uvicorn

        config = settings.app
        uvicorn.run("app.main:app", host=config.dashboard_host, port=config.dashboard_port)
        return {"status": "stopped"}
    raise RuntimeError("未知命令")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    configure_logging(log_dir=project_root() / "logs")
    try:
        result = asyncio.run(execute(args))
    except (RuntimeError, ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
