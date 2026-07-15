from datetime import UTC, datetime

from app.detection.baseline import summarize_baseline
from app.detection.events import detect_events
from app.detection.traffic import counter_delta
from app.models.domain import ClientSnapshot, IptvSnapshot, RouterCapabilities, RouterSnapshot


def test_counter_delta_handles_reset() -> None:
    assert counter_delta(100, 140) == 40
    assert counter_delta(140, 10) is None
    assert counter_delta(None, 10) is None


def test_unknown_device_and_monitor_exclusion() -> None:
    snapshot = RouterSnapshot(
        room_id="2305",
        captured_at=datetime.now(UTC),
        clients=[
            ClientSnapshot(mac="00:00:00:00:00:01", ip="192.168.1.100", rx_rate_bps=1),
            ClientSnapshot(mac="00:00:00:00:00:02", ip="192.168.1.120", rx_rate_bps=1000),
        ],
    )
    ids = {"00:00:00:00:00:01": "dev_monitor", "00:00:00:00:00:02": "dev_unknown"}
    events = detect_events(snapshot, ids, {}, "192.168.1.100")
    assert [event.event_type for event in events] == ["unknown_device_active"]
    assert events[0].evidence["device_id"] == "dev_unknown"


def test_explicit_iptv_state_is_high_confidence() -> None:
    snapshot = RouterSnapshot(
        room_id="2309",
        iptv=IptvSnapshot(state="active", evidence_field="iptv.state"),
        capabilities=RouterCapabilities(iptv_state=True),
    )
    event = detect_events(snapshot, {}, {}, None)[0]
    assert event.event_type == "iptv_active"
    assert event.confidence == 0.95


def test_pc_local_media_advertisement_is_only_visibility_evidence() -> None:
    snapshot = RouterSnapshot(
        room_id="2312",
        clients=[
            ClientSnapshot(mac="ssdp:device-1", connection_type="ssdp-media-device")
        ],
        raw_source="pc-local",
    )
    events = detect_events(snapshot, {"ssdp:device-1": "dev_media"}, {}, None)
    assert [event.event_type for event in events] == ["media_device_visible"]
    assert events[0].confidence < 0.7
    assert "不等于亮屏" in "".join(events[0].limitations)


def test_baseline_summary() -> None:
    result = summarize_baseline([1, 2, 3, 4, 5])
    assert result["median"] == 3
    assert result["p95"] is not None
