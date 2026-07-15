from __future__ import annotations

import re
from typing import Any

MAC_RE = re.compile(r"(?i)\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b")
SECRET_RE = re.compile(
    r"(?i)(password|passwd|pwd|token|cookie|authorization|secret)\s*[:=]\s*([^\s,;]+)"
)


def redact_text(value: str) -> str:
    value = MAC_RE.sub("[REDACTED_MAC]", value)
    return SECRET_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if _sensitive(key) else redact(item)) for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def _sensitive(key: object) -> bool:
    lowered = str(key).lower()
    return any(token in lowered for token in ("password", "passwd", "token", "cookie", "secret"))
