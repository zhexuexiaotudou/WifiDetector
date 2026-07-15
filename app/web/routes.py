from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.detection.device_profiles import build_device_inventory
from app.scheduler.health import HEALTH
from app.scheduler.rotating_scanner import RotatingScanner
from app.storage.repository import Repository
from app.web.schemas import (
    AllowlistRequest,
    ClearRequest,
    ReportedDeviceRequest,
    ReviewRequest,
)

router = APIRouter()


def _repository(request: Request) -> Repository:
    return cast(Repository, request.app.state.repository)


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _scanner(request: Request) -> RotatingScanner:
    return cast(RotatingScanner, request.app.state.scanner)


def _templates(request: Request) -> Jinja2Templates:
    return cast(Jinja2Templates, request.app.state.templates)


def _room_ids(request: Request) -> tuple[str, ...]:
    return tuple(room.room_id for room in _settings(request).rooms if room.enabled)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    return _templates(request).TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "room_ids": _room_ids(request),
            "mock_mode": _settings(request).app.mock_mode,
        },
    )


@router.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room_page(request: Request, room_id: str) -> Response:
    if room_id not in _room_ids(request):
        raise HTTPException(404, "未知房间")
    return _templates(request).TemplateResponse(
        request=request,
        name="room.html",
        context={"room_id": room_id},
    )


@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request) -> Response:
    return _templates(request).TemplateResponse(request=request, name="events.html", context={})


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> Response:
    return _templates(request).TemplateResponse(request=request, name="settings.html", context={})


@router.get("/api/health")
async def health(request: Request) -> dict[str, object]:
    repository = _repository(request)
    events = repository.recent_events(limit=500)
    return {
        **HEALTH.as_dict(),
        "server_time": datetime.now(UTC).isoformat(),
        "room_count": len(_room_ids(request)),
        "pending_events": sum(1 for event in events if not event.get("review_status")),
        "system_faults": sum(1 for event in events if event["severity"] == "system"),
        "mode": "mock" if _settings(request).app.mock_mode else "field",
    }


@router.get("/api/rooms")
async def rooms(request: Request) -> list[dict[str, object]]:
    repository = _repository(request)
    latest = {room["room_id"]: room for room in repository.latest_rooms()}
    scan_statuses = repository.latest_scan_statuses()
    response: list[dict[str, object]] = []
    for room_id in _room_ids(request):
        room = latest.get(room_id, {"room_id": room_id, "status": "数据不足"})
        samples = repository.room_samples(room_id)
        room["devices"] = build_device_inventory(samples, repository.allowed_devices(room_id))
        room["reported_devices"] = repository.reported_devices(room_id)
        room["scan_status"] = scan_statuses.get(room_id)
        response.append(room)
    return response


@router.get("/api/rooms/{room_id}")
async def room_detail(request: Request, room_id: str) -> dict[str, object]:
    if room_id not in _room_ids(request):
        raise HTTPException(404, "未知房间")
    repository = _repository(request)
    sample = repository.latest_sample(room_id)
    if sample is None:
        sample = {
            "room_id": room_id,
            "captured_at": None,
            "reachable": False,
            "raw_source": "尚无自动样本",
        }
    sample["events"] = repository.recent_events(limit=100, room_id=room_id)
    sample["allowlist"] = repository.allowed_devices(room_id)
    sample["devices"] = build_device_inventory(
        repository.room_samples(room_id), sample["allowlist"]
    )
    sample["reported_devices"] = repository.reported_devices(room_id)
    sample["scan_status"] = repository.latest_scan_statuses().get(room_id)
    return sample


@router.get("/api/events")
async def list_events(request: Request, room_id: str | None = None) -> list[dict[str, object]]:
    return _repository(request).recent_events(limit=500, room_id=room_id)


@router.post("/api/events/{event_id}/review")
async def review_event(request: Request, event_id: int, body: ReviewRequest) -> dict[str, bool]:
    try:
        updated = _repository(request).review_event(event_id, body.status, body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not updated:
        raise HTTPException(404, "事件不存在")
    return {"updated": True}


@router.post("/api/reported-devices")
async def add_reported_device(
    request: Request, body: ReportedDeviceRequest
) -> dict[str, int]:
    if body.room_id not in _room_ids(request):
        raise HTTPException(400, "未知房间")
    device_id = _repository(request).add_reported_device(
        body.room_id, body.label, body.device_type, body.usage_state, body.note
    )
    return {"id": device_id}


@router.put("/api/reported-devices/{device_id}")
async def update_reported_device(
    request: Request, device_id: int, body: ReportedDeviceRequest
) -> dict[str, bool]:
    if body.room_id not in _room_ids(request):
        raise HTTPException(400, "未知房间")
    updated = _repository(request).update_reported_device(
        device_id, body.room_id, body.label, body.device_type, body.usage_state, body.note
    )
    if not updated:
        raise HTTPException(404, "现场确认设备不存在")
    return {"updated": True}


@router.delete("/api/reported-devices/{device_id}")
async def delete_reported_device(request: Request, device_id: int) -> dict[str, bool]:
    if not _repository(request).delete_reported_device(device_id):
        raise HTTPException(404, "现场确认设备不存在")
    return {"deleted": True}


@router.post("/api/allowlist")
async def update_allowlist(request: Request, body: AllowlistRequest) -> dict[str, bool]:
    if body.room_id not in _room_ids(request):
        raise HTTPException(400, "未知房间")
    if body.label not in {
        "海信电视",
        "手机",
        "平板",
        "个人电脑",
        "酒店固定设备",
        "允许设备",
        "未知设备",
    }:
        raise HTTPException(400, "无效设备标签")
    _repository(request).upsert_allowlist(body.room_id, body.device_id, body.label, body.note)
    return {"updated": True}


@router.post("/api/scan-cycle")
async def trigger_scan(request: Request) -> dict[str, object]:
    if HEALTH.current_room:
        raise HTTPException(409, "当前已有扫描进行中")
    return await _scanner(request).scan_cycle()


@router.post("/api/purge")
async def purge(request: Request) -> dict[str, int]:
    hours = _settings(request).app.retention_hours
    return _repository(request).purge(hours)


@router.post("/api/clear")
async def clear(request: Request, body: ClearRequest) -> dict[str, int]:
    if body.confirmation != "清空本地监测数据":
        raise HTTPException(400, "确认短语不匹配")
    return _repository(request).clear_monitoring_data()
