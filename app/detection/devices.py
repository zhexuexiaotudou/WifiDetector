from __future__ import annotations

from app.models.domain import ClientSnapshot


def identify_monitor(clients: list[ClientSnapshot], local_ipv4: str | None) -> str | None:
    if not local_ipv4:
        return None
    match = next((client for client in clients if client.ip == local_ipv4), None)
    return match.mac if match else None
