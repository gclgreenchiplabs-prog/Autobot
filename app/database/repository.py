from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.database.connection import DatabaseConnection


class Repository:
    def __init__(self, database: DatabaseConnection) -> None:
        self.database = database

    def initialize_schema(self) -> None:
        conn = self.database.connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS application_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS broker_readiness (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS idempotency_records (
                idempotency_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reconciliation_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reason TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS health_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

    def save_state(self, key: str, value: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute(
            "INSERT INTO application_state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )

    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        row = self.database.connect().execute("SELECT value FROM application_state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def save_lifecycle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute(
            "INSERT INTO lifecycle_events(event_type, payload) VALUES(?, ?)",
            (event_type, json.dumps(payload)),
        )

    def save_idempotency(self, key: str, payload: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute(
            "INSERT INTO idempotency_records(idempotency_key, payload) VALUES(?, ?) ON CONFLICT(idempotency_key) DO UPDATE SET payload=excluded.payload",
            (key, json.dumps(payload)),
        )

    def save_reconciliation(self, reason: str, payload: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute("INSERT INTO reconciliation_records(reason, payload) VALUES(?, ?)", (reason, json.dumps(payload)))

    def save_order(self, payload: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute("INSERT INTO orders(payload) VALUES(?)", (json.dumps(payload),))

    def save_position(self, payload: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute("INSERT INTO positions(payload) VALUES(?)", (json.dumps(payload),))

    def save_system_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute("INSERT INTO system_events(event_type, payload) VALUES(?, ?)", (event_type, json.dumps(payload)))

    def save_health_snapshot(self, status: str, payload: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute("INSERT INTO health_snapshots(status, payload) VALUES(?, ?)", (status, json.dumps(payload)))

    def list_orders(self) -> List[Dict[str, Any]]:
        rows = self.database.connect().execute("SELECT payload FROM orders ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]
