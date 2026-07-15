from app.routers.local_pc import parse_arp_table, parse_ssdp_response


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
