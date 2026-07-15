from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.security.redact import redact, redact_text


def safe_url(value: str) -> str:
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


async def discover_router(room_id: str, router_url: str, output_dir: Path) -> Path:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("发现模式需要可选依赖：py -m pip install -e .[discovery]") from exc

    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    requests: list[dict[str, str | int]] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(channel="msedge", headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        def on_response(response: Any) -> None:
            request = response.request
            resource_type = request.resource_type
            if resource_type in {"xhr", "fetch"}:
                requests.append(
                    {
                        "method": request.method,
                        "url": safe_url(response.url),
                        "status": int(response.status),
                        "content_type": response.headers.get("content-type", ""),
                    }
                )

        page.on("response", on_response)
        await page.goto(router_url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.to_thread(
            input,
            "请在独立 Edge 窗口手动完成授权登录并浏览客户端/IPTV 页面；完成后按 Enter。"
            "凭据、Cookie、响应正文和截图不会保存：",
        )
        title = await page.title()
        body_text = await page.locator("body").inner_text(timeout=10_000)
        report = {
            "room_id": room_id,
            "captured_at": datetime.now(UTC).isoformat(),
            "router_url": safe_url(router_url),
            "page_title": redact_text(title)[:200],
            "visible_text_excerpt": redact_text(body_text)[:10_000],
            "xhr_fetch_metadata": redact(requests),
            "not_collected": [
                "Cookie 和浏览器存储",
                "请求或响应正文",
                "原始 HAR",
                "截图",
                "输入框值",
            ],
            "capability_conclusion": "需要根据此脱敏证据人工确认，不自动猜测接口或选择器",
        }
        await context.close()
        await browser.close()
    path = output_dir / f"room-{room_id}-{timestamp}.json"
    await asyncio.to_thread(
        path.write_text,
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
