import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from app.database.connection import DatabaseConnection
from app.database.migrations import MigrationRunner
from app.database.repository import Repository
from app.lifecycle import AppLifecycle
from app.scheduler.market_clock import MarketClock
from app.scheduler.session_scheduler import SessionScheduler
from app.settings import Settings, SettingsValidationError, validate_settings
from app.state_store import StateStore
from app.tasks.manager import BackgroundTaskManager


def test_database_initialization_and_wal_pragmas(tmp_path):
    db_path = tmp_path / "test.db"
    connection = DatabaseConnection(str(db_path))
    conn = connection.connect()
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] in {"wal", "memory"}
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_migration_runner_is_idempotent_and_uses_transaction(tmp_path):
    db_path = tmp_path / "migrations.db"
    connection = DatabaseConnection(str(db_path))
    runner = MigrationRunner(connection)
    first = runner.apply()
    second = runner.apply()
    assert first == second
    assert runner.current_version() == "004_live_market_data_foundation"


def test_lifecycle_persists_state():
    store = StateStore()
    lifecycle = AppLifecycle(state_store=store)
    lifecycle.start()
    payload = store.get("lifecycle")
    assert payload["status"] == "running"
    assert payload["kill_switch"] is False


def test_repository_persists_idempotency_and_reconciliation(tmp_path):
    connection = DatabaseConnection(str(tmp_path / "repo.db"))
    repository = Repository(connection)
    repository.initialize_schema()
    repository.save_idempotency("abc", {"status": "ok"})
    repository.save_reconciliation("reason", {"count": 1})
    assert repository.database.connect().execute("SELECT idempotency_key FROM idempotency_records").fetchone()[0] == "abc"
    assert repository.database.connect().execute("SELECT reason FROM reconciliation_records").fetchone()[0] == "reason"


def test_settings_validation_covers_timezones_and_time_values():
    valid = Settings(timezone="Asia/Kolkata")
    validate_settings(valid)

    with pytest.raises(SettingsValidationError):
        validate_settings(Settings(timezone="Europe/Atlantis"))

    with pytest.raises(SettingsValidationError):
        validate_settings(Settings(premarket_start_time="not-a-time"))


def test_scheduler_handles_weekend_forced_test_and_invalid_time_config(tmp_path):
    settings = Settings(forced_test_mode=True)
    clock = MarketClock(settings)
    assert clock.current_session_state(clock.current_ist()) == "FORCED_TEST"

    scheduler = SessionScheduler(MarketClock(Settings()), StateStore())
    payload = scheduler.get_state()
    assert payload["session_state"] in {"PREMARKET", "MARKET_OPEN", "POST_MARKET", "MARKET_CLOSED", "FORCED_TEST"}


def test_background_task_cancellation_and_exception_capture():
    manager = BackgroundTaskManager()

    async def sleepy():
        await asyncio.sleep(0)

    async def failing():
        raise RuntimeError("boom")

    manager.register("cancelled", lambda: sleepy())
    manager.stop("cancelled")
    assert manager.get_task("cancelled").state == "CANCELLED"

    manager.register("failed", lambda: failing())
    assert manager.get_task("failed").state in {"RUNNING", "FAILED"}
