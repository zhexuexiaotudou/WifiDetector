from __future__ import annotations

import hashlib
import hmac
import secrets
from pathlib import Path


class DeviceAnonymizer:
    def __init__(self, salt_file: Path) -> None:
        salt_file.parent.mkdir(parents=True, exist_ok=True)
        if salt_file.exists():
            self._key = salt_file.read_bytes()
        else:
            self._key = secrets.token_bytes(32)
            salt_file.write_bytes(self._key)

    def device_id(self, mac: str) -> str:
        normalized = mac.strip().lower().replace("-", ":")
        digest = hmac.new(self._key, normalized.encode(), hashlib.sha256).hexdigest()
        return f"dev_{digest[:16]}"
