from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from app.cli import execute


@pytest.mark.asyncio
async def test_run_awaits_uvicorn_server(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    served: list[bool] = []

    class FakeServer:
        def __init__(self, _config: Any) -> None:
            pass

        async def serve(self) -> None:
            served.append(True)

    monkeypatch.setenv("DORM_MONITOR_CONFIG", "config/rooms.example.yaml")
    monkeypatch.setenv("DORM_MONITOR_DATABASE", str(tmp_path / "cli.db"))
    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    result = await execute(Namespace(command="run"))
    assert result == {"status": "stopped"}
    assert served == [True]
