import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from app.container import AppContainer
from app.tasks.manager import BackgroundTaskManager


def test_background_task_duplicate_rejection():
    manager = BackgroundTaskManager()

    manager.register('task-a', lambda: None)
    with pytest.raises(ValueError):
        manager.register('task-a', lambda: None)


def test_task_manager_tracks_status():
    manager = BackgroundTaskManager()
    manager.register('task-b', lambda: None)
    statuses = manager.get_status()
    assert statuses[0]['name'] == 'task-b'
