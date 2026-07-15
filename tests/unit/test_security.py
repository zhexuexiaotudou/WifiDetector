from pathlib import Path

from app.security.anonymize import DeviceAnonymizer
from app.security.redact import redact, redact_text


def test_anonymization_is_stable_and_salted(tmp_path: Path) -> None:
    first = DeviceAnonymizer(tmp_path / "one.key")
    second = DeviceAnonymizer(tmp_path / "two.key")
    mac = "AA:BB:CC:DD:EE:FF"
    assert first.device_id(mac) == first.device_id(mac.lower())
    assert first.device_id(mac) != second.device_id(mac)
    assert mac not in first.device_id(mac)


def test_redaction_removes_macs_and_secrets() -> None:
    text = "mac=AA:BB:CC:DD:EE:FF password=hunter2 token: abc123"
    result = redact_text(text)
    assert "AA:BB" not in result
    assert "hunter2" not in result
    assert "abc123" not in result
    assert redact({"cookie": "value", "nested": [text]})["cookie"] == "[REDACTED]"
