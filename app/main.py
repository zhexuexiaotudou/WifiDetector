from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import Settings, database_path, load_settings
from app.scheduler.rotating_scanner import RotatingScanner
from app.storage.repository import Repository
from app.web.routes import router


def create_app(settings: Settings | None = None, db_path: Path | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    repository = Repository(db_path or database_path())
    scanner = RotatingScanner(resolved_settings, repository)
    web_dir = Path(__file__).parent / "web"

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        scanner.stop()

    application = FastAPI(
        title="宿舍夜间电子产品监测系统",
        description="仅供授权网络的本地只读监测和人工复核",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.repository = repository
    application.state.scanner = scanner
    application.state.templates = Jinja2Templates(directory=web_dir / "templates")
    application.mount("/static", StaticFiles(directory=web_dir / "static"), name="static")
    application.include_router(router)
    return application


app = create_app()
