from __future__ import annotations

import csv
import html
import json
from datetime import date
from pathlib import Path

from app.storage.repository import Repository


def export_daily(repository: Repository, target_date: date, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    events = [
        event
        for event in repository.recent_events(limit=100_000)
        if str(event["occurred_at"]).startswith(target_date.isoformat())
    ]
    rooms = repository.latest_rooms()
    base = output_dir / target_date.isoformat()
    json_path = base.with_suffix(".json")
    csv_path = base.with_suffix(".csv")
    html_path = base.with_suffix(".html")
    payload = {
        "date": target_date.isoformat(),
        "method_limitations": [
            "仅观测授权网关公开的最小元数据",
            "设备在线或联网活跃不等于特定人员正在使用",
            "无明确网关证据时不能判断 HDMI 电视是否亮屏",
        ],
        "rooms": rooms,
        "events": events,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "occurred_at",
                "room_id",
                "event_type",
                "severity",
                "confidence",
                "review_status",
            ],
        )
        writer.writeheader()
        for event in events:
            writer.writerow({key: event.get(key) for key in writer.fieldnames})
    rows = "".join(
        f"<tr><td>{html.escape(str(event['occurred_at']))}</td><td>{html.escape(str(event['room_id']))}</td>"
        f"<td>{html.escape(str(event['event_type']))}</td><td>{float(event['confidence']):.0%}</td></tr>"
        for event in events
    )
    html_path.write_text(
        "<!doctype html><meta charset='utf-8'><title>宿舍监测日报</title>"
        "<h1>宿舍联网活动人工复核日报</h1>"
        "<p>本报告不构成自动违规定性；所有异常均需人工复核。</p>"
        f"<table><tr><th>时间</th><th>房间</th><th>事件</th><th>置信度</th></tr>{rows}</table>"
        "<h2>方法限制</h2><ul><li>联网活动不等于人员使用。</li>"
        "<li>无明确证据时不能判断 HDMI 电视亮屏。</li></ul>",
        encoding="utf-8",
    )
    return {"json": json_path, "csv": csv_path, "html": html_path}
