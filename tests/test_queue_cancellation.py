"""Cancellation releases both starting and running subprocesses."""

import sys
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from qtpy.QtCore import QProcess

from qtextra.queue.cli_queue import CLIQueueHandler
from qtextra.queue.task import Task


@pytest.mark.parametrize("wait_started", [False, True])
def test_cancel_releases_process_and_slot(qtbot: QtBot, tmp_path: Path, wait_started: bool) -> None:
    """A cancelled process exits before the queue starts its successor."""
    script = tmp_path / "wait.py"
    script.write_text("import time\ntime.sleep(30)\n")
    queue = CLIQueueHandler(n_parallel=1)
    cancelled: list[Task] = []
    finished: list[Task] = []
    queue.evt_cancelled.connect(cancelled.append)
    queue.evt_finished.connect(finished.append)
    task = Task("cancel", [[sys.executable, str(script)]])
    queue.add_task(task)
    process = queue.active_tasks[task.task_id].process
    queue.run_queued()
    if wait_started:
        qtbot.waitUntil(lambda: process.state() == QProcess.ProcessState.Running, timeout=5000)
    queue.cancel(task)
    qtbot.waitUntil(lambda: cancelled == [task], timeout=5000)
    assert process.state() == QProcess.ProcessState.NotRunning
    assert queue.n_tasks == (0, 0)
    assert not finished
    next_script = tmp_path / "done.py"
    next_script.write_text("print('done')\n")
    successor = Task("next", [[sys.executable, str(next_script)]])
    queue.add_task(successor)
    queue.run_queued()
    qtbot.waitUntil(lambda: finished == [successor], timeout=5000)
    assert queue.n_tasks == (0, 0)
    queue.close()
