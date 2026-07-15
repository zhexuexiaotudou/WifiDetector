from app.wifi.parser import parse_interfaces, parse_ipconfig, parse_networks, parse_profiles


def test_parse_english_profiles() -> None:
    output = """User profiles
-------------
    All User Profile     : 2301
    All User Profile     : 2302
"""
    assert parse_profiles(output) == ["2301", "2302"]


def test_parse_connected_interface_and_networks() -> None:
    interface = """State : connected\nSSID : 2301\nAP BSSID : aa:bb:cc:dd:ee:ff\nProfile : 2301\n"""
    current = parse_interfaces(interface)
    assert current is not None
    assert current.ssid == "2301"
    assert current.bssid == "aa:bb:cc:dd:ee:ff"
    networks = parse_networks("SSID 1 : 2301\n BSSID 1 : aa:bb:cc:dd:ee:ff\n Signal : 88%")
    assert networks[0].ssid == "2301"
    assert networks[0].signal_percent == 88


def test_parse_ipconfig() -> None:
    output = (
        "IPv4 Address. . . . . . . . . . . : 192.168.1.88\n"
        "Default Gateway . . . . . . . . . : 192.168.1.1"
    )
    assert parse_ipconfig(output) == ("192.168.1.88", "192.168.1.1")
