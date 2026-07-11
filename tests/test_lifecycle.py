import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lifecycle import AppLifecycle
from app.state_store import StateStore


def test_lifecycle_transitions_to_running_and_stopped():
    store = StateStore()
    lifecycle = AppLifecycle(state_store=store)

    lifecycle.start()
    lifecycle.stop()

    state = store.get("lifecycle")
    assert state is not None
    assert state["status"] == "stopped"
    assert state["mode"] == "paper"
