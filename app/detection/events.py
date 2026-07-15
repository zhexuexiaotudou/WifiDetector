from __future__ import annotations

from app.models.domain import DetectionEvent, RouterSnapshot, Severity


def detect_events(
    snapshot: RouterSnapshot,
    device_ids: dict[str, str],
    allowlist: dict[str, str],
    monitor_ipv4: str | None,
    seen_counts: dict[str, int] | None = None,
) -> list[DetectionEvent]:
    events: list[DetectionEvent] = []
    seen_counts = seen_counts or {}
    if not snapshot.router_reachable:
        events.append(
            DetectionEvent(
                room_id=snapshot.room_id,
                event_type="router_unreachable",
                severity=Severity.SYSTEM,
                confidence=1.0,
                reasons=["授权网关本轮不可达"],
                limitations=["未读取任何客户端或电视业务数据"],
                evidence={"raw_source": snapshot.raw_source},
            )
        )
        return events
    monitor_identified = (
        any(client.ip == monitor_ipv4 for client in snapshot.clients) if monitor_ipv4 else False
    )
    for client in snapshot.clients:
        device_id = device_ids[client.mac]
        if monitor_ipv4 and client.ip == monitor_ipv4:
            continue
        label = allowlist.get(device_id)
        active = bool((client.rx_rate_bps or 0) + (client.tx_rate_bps or 0))
        if not label:
            confidence = 0.72 if active else 0.55
            if not active and seen_counts.get(device_id, 1) < 2:
                continue
            reasons = ["设备不在该房间匿名化白名单中"]
            if active:
                reasons.append("网关报告该客户端存在实时流量")
            events.append(
                DetectionEvent(
                    room_id=snapshot.room_id,
                    event_type="unknown_device_active" if active else "unknown_device_seen",
                    severity=Severity.MEDIUM if active else Severity.LOW,
                    confidence=confidence,
                    reasons=reasons,
                    limitations=["无法确认设备持有人", "需跨样本持续性与人工复核"],
                    evidence={"device_id": device_id, "active": active},
                )
            )
        elif label == "海信电视" and active and seen_counts.get(device_id, 1) >= 2:
            events.append(
                DetectionEvent(
                    room_id=snapshot.room_id,
                    event_type="smart_tv_active",
                    severity=Severity.MEDIUM,
                    confidence=0.75,
                    reasons=["人工标记的海信电视客户端存在联网流量"],
                    limitations=["联网活跃不等于电视亮屏或有人观看"],
                    evidence={"device_id": device_id},
                )
            )
    if monitor_ipv4 and not monitor_identified:
        events.append(
            DetectionEvent(
                room_id=snapshot.room_id,
                event_type="monitor_pc_unconfirmed",
                severity=Severity.SYSTEM,
                confidence=1.0,
                reasons=["客户端列表中未匹配本机 IPv4"],
                limitations=["本轮未知设备结果可能包含监测电脑"],
                evidence={},
            )
        )
    if snapshot.iptv and snapshot.capabilities.iptv_state and snapshot.iptv.state == "active":
        events.append(
            DetectionEvent(
                room_id=snapshot.room_id,
                event_type="iptv_active",
                severity=Severity.HIGH,
                confidence=0.95,
                reasons=["网关明确报告 IPTV 业务状态为 active"],
                limitations=["业务活跃不证明具体观看人员"],
                evidence={"field": snapshot.iptv.evidence_field or "iptv.state"},
            )
        )
    elif snapshot.iptv and snapshot.capabilities.iptv_interface_counters and snapshot.iptv.rx_bytes:
        events.append(
            DetectionEvent(
                room_id=snapshot.room_id,
                event_type="iptv_traffic_observed",
                severity=Severity.MEDIUM,
                confidence=0.7,
                reasons=["网关提供 IPTV 专用接口累计流量计数"],
                limitations=["单个累计计数不能证明当前播放，需校准和连续差分"],
                evidence={"field": snapshot.iptv.evidence_field or "iptv.rx_bytes"},
            )
        )
    return events
