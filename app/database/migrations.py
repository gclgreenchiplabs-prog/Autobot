from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from app.database.connection import DatabaseConnection


class MigrationRunner:
    def __init__(self, database: DatabaseConnection) -> None:
        self.database = database
        self._migrations: List[tuple[str, str]] = [
            ("001_initial_schema", """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            """),
        ]

    def current_version(self) -> Optional[str]:
        conn = self.database.connect()
        row = conn.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1").fetchone()
        return row[0] if row else None

    def apply(self) -> str:
        conn = self.database.connect()
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        with self.database.transaction():
            for version, sql in self._migrations:
                existing = conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,)).fetchone()
                if existing:
                    continue
                conn.execute(sql)
                conn.execute("INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)", (version, datetime.now(timezone.utc).isoformat()))
        return self.current_version() or "000"
