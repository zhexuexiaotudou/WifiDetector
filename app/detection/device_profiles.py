from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.domain import ClientSnapshot

MANUAL_DEVICE_TYPES = {
    "海信电视": ("电视", 0.99, "人工标记为海信电视"),
    "手机": ("手机", 0.99, "人工标记为手机"),
    "平板": ("平板", 0.99, "人工标记为平板"),
    "个人电脑": ("个人电脑", 0.99, "人工标记为个人电脑"),
    "酒店固定设备": ("固定网络设备", 0.95, "人工标记为酒店固定设备"),
    "允许设备": ("已允许设备", 0.95, "人工标记为允许设备"),
    "未知设备": ("未知设备", 0.99, "人工确认当前无法分类"),
}


def derive_type_hint(client: ClientSnapshot) -> dict[str, object]:
    """Derive a non-identifying type hint, then allow the raw hostname to be discarded."""
    hostname = (client.hostname or "").casefold()
    connection_type = (client.connection_type or "").casefold()
    if any(token in hostname for token in ("hisense", "smart-tv", "androidtv", "roku")):
        return {
            "type_hint": "电视",
            "type_hint_confidence": 0.92,
            "type_hint_reason": "设备公开名称包含电视类通用标识（原名称未保存）",
        }
    if any(token in hostname for token in ("ipad", "tablet", "-tab")):
        return {
            "type_hint": "平板",
            "type_hint_confidence": 0.86,
            "type_hint_reason": "设备公开名称包含平板类通用标识（原名称未保存）",
        }
    if any(token in hostname for token in ("iphone", "phone", "mobile")):
        return {
            "type_hint": "手机",
            "type_hint_confidence": 0.82,
            "type_hint_reason": "设备公开名称包含手机类通用标识（原名称未保存）",
        }
    if any(token in hostname for token in ("laptop", "desktop", "windows", "macbook")):
        return {
            "type_hint": "个人电脑",
            "type_hint_confidence": 0.82,
            "type_hint_reason": "设备公开名称包含电脑类通用标识（原名称未保存）",
        }
    if connection_type == "ssdp-media-device":
        return {
            "type_hint": "媒体服务端点",
            "type_hint_confidence": 0.60,
            "type_hint_reason": (
                "发现媒体服务；可能来自待机电视、机顶盒或电脑，不能据此确定设备类型"
            ),
        }
    if connection_type == "icmp-neighbor":
        return {
            "type_hint": "手机/平板/电脑候选",
            "type_hint_confidence": 0.30,
            "type_hint_reason": "只有本机邻居可见证据，无法区分个人终端类型",
        }
    return {
        "type_hint": "未知网络设备",
        "type_hint_confidence": 0.25,
        "type_hint_reason": "现有元数据不足以判断手机、平板、电脑或电视",
    }


def _automatic_type(client: dict[str, Any]) -> tuple[str, float, str]:
    label = client.get("type_hint")
    confidence = client.get("type_hint_confidence")
    reason = client.get("type_hint_reason")
    if isinstance(label, str) and isinstance(confidence, (float, int)) and isinstance(reason, str):
        return label, float(confidence), reason
    connection_type = client.get("connection_type")
    if connection_type == "ssdp-media-device":
        return (
            "媒体服务端点",
            0.60,
            "发现媒体服务；可能来自待机电视、机顶盒或电脑，不能据此确定设备类型",
        )
    if connection_type == "icmp-neighbor":
        return "手机/平板/电脑候选", 0.30, "只有本机邻居可见证据，无法区分个人终端类型"
    return "未知网络设备", 0.25, "现有元数据不足以判断手机、平板、电脑或电视"


def _activity(client: dict[str, Any], currently_visible: bool) -> dict[str, object]:
    if not currently_visible:
        return {
            "activity_label": "本轮未发现",
            "activity_confidence": 0.55,
            "activity_reason": "设备存在历史记录，但未出现在最新样本中",
            "activity_rate_bps": None,
        }
    rx = client.get("rx_rate_bps")
    tx = client.get("tx_rate_bps")
    if isinstance(rx, int) or isinstance(tx, int):
        rate = max(0, int(rx or 0)) + max(0, int(tx or 0))
        if rate >= 1_000_000:
            label = "联网高活跃"
            confidence = 0.86
        elif rate >= 10_000:
            label = "联网活跃"
            confidence = 0.78
        elif rate > 0:
            label = "少量联网活动"
            confidence = 0.68
        else:
            label = "在线，当前流量较低"
            confidence = 0.62
        return {
            "activity_label": label,
            "activity_confidence": confidence,
            "activity_reason": "网关提供该匿名客户端的实时速率元数据",
            "activity_rate_bps": rate,
        }
    if client.get("connection_type") == "ssdp-media-device":
        return {
            "activity_label": "媒体服务可见，使用未知",
            "activity_confidence": 0.35,
            "activity_reason": "媒体服务广播只证明联网可见，不证明亮屏、播放或有人使用",
            "activity_rate_bps": None,
        }
    return {
        "activity_label": "在线可见，使用未知",
        "activity_confidence": 0.25,
        "activity_reason": "本机能看到设备，但没有逐设备流量或应用状态",
        "activity_rate_bps": None,
    }


def build_device_inventory(
    samples: list[dict[str, Any]], allowlist: dict[str, str]
) -> list[dict[str, object]]:
    """Aggregate sanitized samples into explainable per-room device profiles."""
    if not samples:
        return []
    history: dict[str, dict[str, Any]] = {}
    for sample in samples:
        captured_at = str(sample.get("captured_at", ""))
        clients = sample.get("clients")
        if not isinstance(clients, list):
            continue
        for raw_client in clients:
            if not isinstance(raw_client, dict):
                continue
            client = dict(raw_client)
            device_id = client.get("device_id")
            if not isinstance(device_id, str):
                continue
            profile = history.setdefault(
                device_id,
                {
                    "device_id": device_id,
                    "first_seen": captured_at,
                    "last_seen": captured_at,
                    "observed_samples": 0,
                    "strongest_client": client,
                    "strongest_confidence": -1.0,
                },
            )
            profile["last_seen"] = captured_at
            profile["observed_samples"] = int(profile["observed_samples"]) + 1
            automatic = _automatic_type(client)
            if automatic[1] > float(profile["strongest_confidence"]):
                profile["strongest_client"] = client
                profile["strongest_confidence"] = automatic[1]

    latest_clients_raw = samples[-1].get("clients")
    latest_clients = {
        str(client["device_id"]): dict(client)
        for client in latest_clients_raw
        if isinstance(client, dict) and isinstance(client.get("device_id"), str)
    } if isinstance(latest_clients_raw, list) else {}

    inventory: list[dict[str, object]] = []
    for device_id, profile in history.items():
        current_client = latest_clients.get(device_id)
        strongest_client = profile["strongest_client"]
        manual_label = allowlist.get(device_id)
        if manual_label in MANUAL_DEVICE_TYPES:
            probable_type, type_confidence, type_reason = MANUAL_DEVICE_TYPES[manual_label]
            type_source = "人工标记"
        else:
            probable_type, type_confidence, type_reason = _automatic_type(strongest_client)
            type_source = "规则推断"
        activity_client = current_client or strongest_client
        activity = _activity(activity_client, current_client is not None)
        first_seen = str(profile["first_seen"])
        last_seen = str(profile["last_seen"])
        try:
            first_seen_at = datetime.fromisoformat(first_seen)
            last_seen_at = datetime.fromisoformat(last_seen)
            visible_span_seconds = max(
                0,
                int((last_seen_at - first_seen_at).total_seconds()),
            )
        except ValueError:
            visible_span_seconds = 0
        inventory.append(
            {
                "device_id": device_id,
                "currently_visible": current_client is not None,
                "probable_type": probable_type,
                "type_confidence": type_confidence,
                "type_reason": type_reason,
                "type_source": type_source,
                "manual_label": manual_label,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "observed_samples": int(profile["observed_samples"]),
                "total_room_samples": len(samples),
                "visible_span_seconds": visible_span_seconds,
                "connection_type": activity_client.get("connection_type"),
                "is_monitor_pc": bool(activity_client.get("is_monitor_pc")),
                **activity,
            }
        )
    return sorted(
        inventory,
        key=lambda item: (
            not bool(item["currently_visible"]),
            -float(item["type_confidence"])
            if isinstance(item["type_confidence"], (int, float))
            else 0.0,
            str(item["device_id"]),
        ),
    )
