import pytest

from app.models.domain import ConnectionResult, WifiConnection
from app.routers.local_pc import LocalPcAdapter, parse_arp_table, parse_ssdp_response


def test_parse_arp_table_normalizes_unicast_entries() -> None:
    output = """
Interface: 192.168.1.3 --- 0x11
  Internet Address      Physical Address      Type
  192.168.1.50          02-00-00-00-00-50     dynamic
  239.255.255.250       01-00-5e-7f-ff-fa     static
"""
    assert parse_arp_table(output) == {"192.168.1.50": "02:00:00:00:00:50"}


def test_parse_ssdp_marks_media_renderer_without_retaining_body() -> None:
    payload = (
        b"HTTP/1.1 200 OK\r\n"
        b"ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n"
        b"USN: uuid:device-1::urn:schemas-upnp-org:device:MediaRenderer:1\r\n"
        b"SERVER: test-device UPnP/1.0\r\n\r\n"
    )
    observation = parse_ssdp_response(payload, "192.168.1.50")
    assert observation is not None
    assert observation.source_ip == "192.168.1.50"
    assert observation.is_media_device is True


def test_invalid_ssdp_response_is_ignored() -> None:
    assert parse_ssdp_response(b"NOTIFY * HTTP/1.1\r\n", "192.168.1.50") is None


@pytest.mark.asyncio
async def test_local_adapter_connects_saved_profile_before_discovery() -> None:
    class FakeWifi:
        async def connect(
            self, profile_name: str, expected_ssid: str, expected_bssid: str | None = None
        ) -> ConnectionResult:
            assert profile_name == "room-profile"
            assert expected_ssid == "room-ssid"
            assert expected_bssid is None
            return ConnectionResult(
                True,
                "connected",
                WifiConnection("room-ssid", None, "room-profile", "connected"),
                "192.168.1.20",
                "192.168.1.1",
            )

    adapter = LocalPcAdapter("2301", "room-ssid", wifi_profile="room-profile")
    adapter.wifi = FakeWifi()  # type: ignore[assignment]
    await adapter.login()
    assert adapter.local_ipv4 == "192.168.1.20"
