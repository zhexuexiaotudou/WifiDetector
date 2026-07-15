from app.detection.device_profiles import build_device_inventory, derive_type_hint
from app.models.domain import ClientSnapshot


def test_media_broadcast_is_a_tv_candidate_not_usage_proof() -> None:
    hint = derive_type_hint(
        ClientSnapshot(mac="opaque", connection_type="ssdp-media-device")
    )
    assert hint["type_hint"] == "电视/媒体设备"
    assert hint["type_hint_confidence"] == 0.82


def test_inventory_aggregates_history_and_keeps_pc_local_usage_unknown() -> None:
    samples = [
        {
            "captured_at": "2026-07-15T20:00:00+00:00",
            "clients": [
                {
                    "device_id": "dev_0123456789abcdef",
                    "connection_type": "ssdp-media-device",
                    "type_hint": "电视/媒体设备",
                    "type_hint_confidence": 0.82,
                    "type_hint_reason": "媒体服务广播",
                    "is_monitor_pc": False,
                }
            ],
        },
        {
            "captured_at": "2026-07-15T20:03:00+00:00",
            "clients": [
                {
                    "device_id": "dev_0123456789abcdef",
                    "connection_type": "ssdp-media-device",
                    "type_hint": "电视/媒体设备",
                    "type_hint_confidence": 0.82,
                    "type_hint_reason": "媒体服务广播",
                    "is_monitor_pc": False,
                }
            ],
        },
    ]
    device = build_device_inventory(samples, {})[0]
    assert device["probable_type"] == "电视/媒体设备"
    assert device["activity_label"] == "媒体服务可见，使用未知"
    assert device["observed_samples"] == 2
    assert device["visible_span_seconds"] == 180


def test_manual_type_label_overrides_rule_inference() -> None:
    samples = [
        {
            "captured_at": "2026-07-15T20:00:00+00:00",
            "clients": [
                {
                    "device_id": "dev_0123456789abcdef",
                    "connection_type": "icmp-neighbor",
                    "is_monitor_pc": False,
                }
            ],
        }
    ]
    device = build_device_inventory(samples, {"dev_0123456789abcdef": "平板"})[0]
    assert device["probable_type"] == "平板"
    assert device["type_confidence"] == 0.99
    assert device["type_source"] == "人工标记"
