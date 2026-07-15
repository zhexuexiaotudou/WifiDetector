from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.models.domain import DetectionEvent, RouterSnapshot


class Repository:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    reachable INTEGER NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_samples_room_time
                    ON samples(room_id, captured_at DESC);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    review_status TEXT,
                    review_note TEXT,
                    dedup_key TEXT,
                    last_seen TEXT,
                    occurrence_count INTEGER NOT NULL DEFAULT 1,
                    open INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_events_time ON events(occurred_at DESC);
                CREATE TABLE IF NOT EXISTS allowlist (
                    room_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    note TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(room_id, device_id)
                );
                CREATE TABLE IF NOT EXISTS runtime_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scan_status (
                    room_id TEXT PRIMARY KEY,
                    attempted_at TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    error_code TEXT
                );
                """
            )
            self._migrate_events(db)

    @staticmethod
    def _migrate_events(db: sqlite3.Connection) -> None:
        columns = {str(row[1]) for row in db.execute("PRAGMA table_info(events)").fetchall()}
        migrations = {
            "dedup_key": "ALTER TABLE events ADD COLUMN dedup_key TEXT",
            "last_seen": "ALTER TABLE events ADD COLUMN last_seen TEXT",
            "occurrence_count": (
                "ALTER TABLE events ADD COLUMN occurrence_count INTEGER NOT NULL DEFAULT 1"
            ),
            "open": "ALTER TABLE events ADD COLUMN open INTEGER NOT NULL DEFAULT 1",
        }
        for column, statement in migrations.items():
            if column not in columns:
                db.execute(statement)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_open_key ON events(room_id,dedup_key,open)"
        )

    def add_sample(self, snapshot: RouterSnapshot, sanitized_payload: dict[str, Any]) -> int:
        with self.connection() as db:
            cursor = db.execute(
                "INSERT INTO samples(room_id,captured_at,reachable,payload) VALUES(?,?,?,?)",
                (
                    snapshot.room_id,
                    snapshot.captured_at.isoformat(),
                    int(snapshot.router_reachable),
                    json.dumps(sanitized_payload, ensure_ascii=False, default=str),
                ),
            )
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("SQLite did not return a sample row id")
            return row_id

    def add_event(self, event: DetectionEvent) -> int:
        payload = {
            "reasons": event.reasons,
            "limitations": event.limitations,
            "evidence": event.evidence,
        }
        evidence_identity = str(
            event.evidence.get("device_id") or event.evidence.get("field") or ""
        )
        dedup_key = f"{event.event_type}:{evidence_identity}"
        with self.connection() as db:
            existing = db.execute(
                """SELECT id FROM events
                WHERE room_id=? AND dedup_key=? AND open=1
                ORDER BY id DESC LIMIT 1""",
                (event.room_id, dedup_key),
            ).fetchone()
            if existing:
                event_id = int(existing["id"])
                db.execute(
                    """UPDATE events SET severity=?,confidence=?,payload=?,last_seen=?,
                    occurrence_count=occurrence_count+1 WHERE id=?""",
                    (
                        event.severity.value,
                        event.confidence,
                        json.dumps(payload, ensure_ascii=False, default=str),
                        event.occurred_at.isoformat(),
                        event_id,
                    ),
                )
                return event_id
            cursor = db.execute(
                """INSERT INTO events
                (room_id,event_type,severity,confidence,occurred_at,payload,dedup_key,last_seen)
                VALUES(?,?,?,?,?,?,?,?)""",
                (
                    event.room_id,
                    event.event_type,
                    event.severity.value,
                    event.confidence,
                    event.occurred_at.isoformat(),
                    json.dumps(payload, ensure_ascii=False, default=str),
                    dedup_key,
                    event.occurred_at.isoformat(),
                ),
            )
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("SQLite did not return an event row id")
            return row_id

    def close_absent_events(self, room_id: str, active_event_ids: list[int]) -> int:
        with self.connection() as db:
            if active_event_ids:
                placeholders = ",".join("?" for _ in active_event_ids)
                cursor = db.execute(
                    "UPDATE events SET open=0 WHERE room_id=? AND open=1 "
                    f"AND id NOT IN ({placeholders})",
                    [room_id, *active_event_ids],
                )
            else:
                cursor = db.execute(
                    "UPDATE events SET open=0 WHERE room_id=? AND open=1", (room_id,)
                )
            return cursor.rowcount

    def recent_device_occurrences(self, room_id: str, device_id: str, limit: int = 2) -> int:
        with self.connection() as db:
            rows = db.execute(
                "SELECT payload FROM samples WHERE room_id=? ORDER BY captured_at DESC LIMIT ?",
                (room_id, limit),
            ).fetchall()
        return sum(
            1
            for row in rows
            if any(
                client.get("device_id") == device_id
                for client in json.loads(row["payload"]).get("clients", [])
            )
        )

    def latest_rooms(self) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                """SELECT s.* FROM samples s JOIN (
                SELECT room_id, MAX(captured_at) AS captured_at FROM samples GROUP BY room_id
                ) latest ON latest.room_id=s.room_id AND latest.captured_at=s.captured_at
                ORDER BY s.room_id"""
            ).fetchall()
        return [self._sample_row(row) for row in rows]

    def latest_sample(self, room_id: str) -> dict[str, Any] | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM samples WHERE room_id=? ORDER BY captured_at DESC LIMIT 1",
                (room_id,),
            ).fetchone()
        return self._sample_row(row) if row else None

    def room_samples(self, room_id: str) -> list[dict[str, Any]]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM samples WHERE room_id=? ORDER BY captured_at ASC", (room_id,)
            ).fetchall()
        return [self._sample_row(row) for row in rows]

    def record_scan_status(self, room_id: str, ok: bool, error_code: str | None) -> None:
        with self.connection() as db:
            db.execute(
                """INSERT INTO scan_status(room_id,attempted_at,ok,error_code) VALUES(?,?,?,?)
                ON CONFLICT(room_id) DO UPDATE SET attempted_at=excluded.attempted_at,
                ok=excluded.ok,error_code=excluded.error_code""",
                (room_id, datetime.now(UTC).isoformat(), int(ok), error_code),
            )

    def latest_scan_statuses(self) -> dict[str, dict[str, object]]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT room_id,attempted_at,ok,error_code FROM scan_status ORDER BY room_id"
            ).fetchall()
        return {
            str(row["room_id"]): {
                "attempted_at": row["attempted_at"],
                "ok": bool(row["ok"]),
                "error_code": row["error_code"],
            }
            for row in rows
        }

    def recent_events(self, limit: int = 100, room_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM events"
        params: list[Any] = []
        if room_id:
            query += " WHERE room_id=?"
            params.append(room_id)
        query += " ORDER BY occurred_at DESC LIMIT ?"
        params.append(limit)
        with self.connection() as db:
            rows = db.execute(query, params).fetchall()
        return [self._event_row(row) for row in rows]

    def upsert_allowlist(self, room_id: str, device_id: str, label: str, note: str = "") -> None:
        with self.connection() as db:
            db.execute(
                """INSERT INTO allowlist(room_id,device_id,label,note,updated_at) VALUES(?,?,?,?,?)
                ON CONFLICT(room_id,device_id) DO UPDATE SET
                label=excluded.label,note=excluded.note,updated_at=excluded.updated_at""",
                (room_id, device_id, label, note, datetime.now(UTC).isoformat()),
            )

    def allowed_devices(self, room_id: str) -> dict[str, str]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT device_id,label FROM allowlist WHERE room_id=?", (room_id,)
            ).fetchall()
        return {str(row["device_id"]): str(row["label"]) for row in rows}

    def review_event(self, event_id: int, status: str, note: str) -> bool:
        allowed = {"已核实", "误报", "无法确认"}
        if status not in allowed:
            raise ValueError("无效人工复核状态")
        with self.connection() as db:
            cursor = db.execute(
                "UPDATE events SET review_status=?,review_note=? WHERE id=?",
                (status, note[:500], event_id),
            )
            return cursor.rowcount == 1

    def purge(self, older_than_hours: int) -> dict[str, int]:
        cutoff = (datetime.now(UTC) - timedelta(hours=older_than_hours)).isoformat()
        with self.connection() as db:
            samples = db.execute("DELETE FROM samples WHERE captured_at < ?", (cutoff,)).rowcount
            events = db.execute("DELETE FROM events WHERE occurred_at < ?", (cutoff,)).rowcount
        return {"samples": samples, "events": events}

    def clear_monitoring_data(self) -> dict[str, int]:
        with self.connection() as db:
            samples = db.execute("DELETE FROM samples").rowcount
            events = db.execute("DELETE FROM events").rowcount
        return {"samples": samples, "events": events}

    @staticmethod
    def _sample_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["payload"])
        return {
            "id": row["id"],
            "room_id": row["room_id"],
            "captured_at": row["captured_at"],
            "reachable": bool(row["reachable"]),
            **payload,
        }

    @staticmethod
    def _event_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = json.loads(row["payload"])
        return {
            "id": row["id"],
            "room_id": row["room_id"],
            "event_type": row["event_type"],
            "severity": row["severity"],
            "confidence": row["confidence"],
            "occurred_at": row["occurred_at"],
            "review_status": row["review_status"],
            "review_note": row["review_note"],
            "last_seen": row["last_seen"],
            "occurrence_count": row["occurrence_count"],
            "open": bool(row["open"]),
            **payload,
        }
