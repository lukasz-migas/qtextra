"""Test CLI Queue."""

import pytest
from koyo.system import IS_MAC, IS_WIN

from qtextra.queue.cli_queue import CLIQueueHandler
from qtextra.queue.task import Task

IS_WIN_OR_MAC = IS_MAC or IS_WIN


@pytest.fixture
def setup_widget():
    """Setup panel"""

    def _widget() -> CLIQueueHandler:
        widget = CLIQueueHandler()
        return widget

    return _widget


class TestCLIQueueHandler:
    """Test CLIQueueHandler."""

    @pytest.mark.xfail(IS_WIN or IS_MAC, reason="Some signals don't fire on Windows/MacOS in time")
    def test_init(self, qtbot, setup_widget):
        queued, started, next_, finished, errored, cancelled, paused = [], [], [], [], [], [], []  # type: ignore
        queue = setup_widget()
        queue.n_parallel = 10
        queue.evt_queued.connect(queued.append)
        queue.evt_started.connect(started.append)
        queue.evt_next.connect(next_.append)
        queue.evt_finished.connect(finished.append)

        def _append_error(task, other=None) -> None:
            errored.append(task)

        queue.evt_errored.connect(_append_error)
        queue.evt_cancelled.connect(cancelled.append)

        def _append_pause(task, other=None) -> None:
            paused.append(task)

        queue.evt_paused.connect(_append_pause)
        assert queue, "Queue is not initialized"
        assert queue.n_tasks == (0, 0), "Queue should be empty"

        # test addition/running
        with (
            qtbot.assertNotEmitted(queue.evt_started),
            qtbot.assertNotEmitted(queue.evt_finished),
            qtbot.assertNotEmitted(queue.evt_errored),
        ):
            task = Task(task_id="123", task_name="Task 1", commands=[["echo", "Hello World"]])
            task_id = queue.add_task(task)
            assert len(queued) == 1, "Queue should have one task"
            assert queue.n_tasks == (0, 1), "Queue should have one task"
            assert task_id == task.task_id, "Task ID should be the same"
            assert not queue.queue_closed, "Queue should not be closed"
            assert not queue.is_running(), "Queue should not be running"
            assert len(queue.pending_queue) == 1, "Queue should have one pending task"
            assert len(queue.running_queue) == 0, "Queue should not have any running tasks"

        with qtbot.waitSignals([queue.evt_started, queue.evt_finished], timeout=3000 if IS_WIN_OR_MAC else 1000):
            queue.run_queued()

        assert len(started) == 1, "Queue should have one task running"
        assert len(errored) == 0, "Queue should not have any errors"
        assert len(finished) == 1, "Queue should have one task finished"
        assert queue.n_tasks == (0, 0), "Queue should have one task running"
        assert len(queue.pending_queue) == 0, "Queue should have one pending task"
        assert len(queue.running_queue) == 0, "Queue should not have any running tasks"

        # test failure
        with (
            qtbot.assertNotEmitted(queue.evt_started),
            qtbot.assertNotEmitted(queue.evt_finished),
            qtbot.assertNotEmitted(queue.evt_errored),
        ):
            task = Task(
                task_id="234",
                task_name="Task 2",
                commands=[
                    ["sleep", "0.5"],
                    ["fake-command", "Hello World"],  # should fail
                ],
            )  # error in command
            task_id = queue.add_task(task)
            assert task_id == task.task_id, "Task ID should be the same"
            assert len(queued) == 2, "Queue should have one task"

        with qtbot.waitSignals([queue.evt_started, queue.evt_errored], timeout=3000 if IS_WIN_OR_MAC else 1000):
            queue.run_queued()
        assert len(started) == 2, "Queue should have one task running"
        assert len(errored) == 1, "Queue should not have one error"
        assert len(finished) == 1, "Queue should have one task finished"

        # test cancellation
        with (
            qtbot.assertNotEmitted(queue.evt_started),
            qtbot.assertNotEmitted(queue.evt_finished),
            qtbot.assertNotEmitted(queue.evt_errored),
        ):
            task = Task(
                task_id="345", task_name="Task 3", commands=[["sleep", "0.5"], ["echo", "Hello World"]]
            )  # error in command
            task_id = queue.add_task(task)
            assert task_id == task.task_id, "Task ID should be the same"
            assert len(queued) == 3, "Queue should have one task"

        with qtbot.waitSignals([queue.evt_started], timeout=1000 if IS_WIN_OR_MAC else 500):
            queue.run_queued()

        with qtbot.waitSignals([queue.evt_cancelled], timeout=5000 if IS_WIN_OR_MAC else 1500):
            queue.cancel(task)

        assert len(started) == 3, "Queue should have one task running"
        assert len(cancelled) == 1, "Queue should have one task finished"

        # test pause
        with (
            qtbot.assertNotEmitted(queue.evt_started),
            qtbot.assertNotEmitted(queue.evt_finished),
            qtbot.assertNotEmitted(queue.evt_errored),
        ):
            task = Task(
                task_id="456", task_name="Task 4", commands=[["sleep", "0.5"], ["echo", "Hello World"]]
            )  # error in command
            task_id = queue.add_task(task)
            assert task_id == task.task_id, "Task ID should be the same"
            assert len(queued) == 4, "Queue should have one task"

        assert queue.n_parallel > 0, "Queue should have some parallel tasks"
        assert queue.is_available(), "Queue should be available"
        assert len(queue.pending_queue) > 0, "Queue should have some tasks"
        queue.auto_run = True
        with qtbot.waitSignals([queue.evt_started], timeout=1000 if IS_WIN_OR_MAC else 500):
            queue.run_queued()
        with qtbot.waitSignals([queue.evt_paused], timeout=3000 if IS_WIN_OR_MAC else 1500):
            queue.pause(task, True)
        assert len(started) == 4, "Queue should have one task running"
        assert len(paused) == 1, "Queue should have one task finished"

        with qtbot.waitSignals([queue.evt_started], timeout=3000 if IS_WIN_OR_MAC else 1500):
            queue.pause(task, False)
        assert len(paused) == 1, "Queue should have one task finished"
