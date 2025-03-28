"""Event queue handler."""

from __future__ import annotations

import atexit
import typing as ty
from contextlib import suppress

from loguru import logger
from qtpy.QtCore import QObject, QProcess, Signal  # type: ignore[attr-defined]

from qtextra.queue.cli_qprocess import QProcessWrapper
from qtextra.queue.task import Task
from qtextra.typing import Callback, TaskState
from qtextra.utils.utilities import running_under_pytest

logger = logger.bind(src="Queue")


class CLIQueueHandler(QObject):
    """Simple Queue handler that executes code as its being added to the queue."""

    CAN_FORCE_START = True

    # internally used signal to cancel thread
    _evt_cancel = Signal(Task)
    _evt_pause = Signal(Task, bool)
    # signal to indicate when task had started
    evt_queued = Signal(Task)
    # signal to indicate when task had started
    evt_started = Signal(Task)
    # signal to indicate when task had started
    evt_next = Signal(Task)
    # signal to indicate when task had finished
    evt_finished = Signal(Task)
    # signal to indicate when queue is empty
    evt_empty = Signal()
    # signal to indicate when task had been cancelled
    evt_cancelled = Signal(Task)
    # signal to indicate when task had crashed
    evt_errored = Signal(Task, object)
    evt_part_errored = Signal(Task, object)
    # signal to indicate when task had been paused
    evt_paused = Signal(Task, bool)
    # signal each time there has been a progress update
    evt_progress = Signal(Task)
    # signal to indicate that the queue is closed
    evt_queue_closed = Signal()
    # signal to indicate that all process had been finished
    evt_finished_all = Signal()
    # signal to indicate that a task had been removed
    evt_remove_task = Signal(str)

    def __init__(self, parent: ty.Optional[QObject] = None, n_parallel: int = 1, auto_run: bool = True):
        super().__init__(parent=parent)
        self.auto_run = auto_run
        self.n_parallel = n_parallel

        # flag to close queueing
        self.queue_closed: bool = False

        # dictionary holding currently running thread tasks
        self.active_tasks: ty.Dict[str, QProcessWrapper] = {}
        # pending tasks are added to this queue
        self.pending_queue: ty.List[str] = []
        # running tasks are added to this queue
        self.running_queue: ty.List[str] = []
        # finished tasks are added to this queue
        self.finished_queue: ty.List[str] = []
        self._evt_cancel.connect(self._kill)  # type: ignore[unused-ignore]

        atexit.register(self.close)

    def set_max_parallel(self, n_parallel: int) -> None:
        """Set maximum number of parallel tasks."""
        self.n_parallel = n_parallel
        self.run_queued()

    @property
    def n_tasks(self) -> ty.Tuple[int, int]:
        """Return the number of tasks."""
        return len(self.running_queue), len(self.pending_queue)

    def task_started(self, task: Task) -> None:
        """Triggered whenever function started processing."""
        task_id = task.task_id
        if task_id in self.pending_queue:
            self.pending_queue.remove(task_id)

        if task_id not in self.running_queue:
            self.running_queue.append(task_id)
        worker_obj = self.active_tasks.get(task_id)
        if worker_obj:
            logger.trace(f"Task '{worker_obj.summary()}' started.")
        self.evt_started.emit(task)  # type: ignore[unused-ignore]
        self.run_queued()

    def task_finished(self, task: Task) -> None:
        """Triggered whenever function finished processing."""
        task_id = task.task_id
        worker_obj = self.active_tasks.pop(task_id, None)  # remove from threads
        if worker_obj:
            logger.trace(f"Removed '{task_id}' from active tasks (finished).")
            with suppress(ValueError):
                self.running_queue.remove(task_id)  # remove from restricted queue
            logger.trace(f"Task '{worker_obj.summary()}' ended.")
        else:
            logger.trace(f"Failed to remove '{task_id}' from active tasks (finished).")
        self.finished_queue.append(task_id)
        self.evt_finished.emit(task)  # type: ignore[unused-ignore]
        self.run_queued()

    def task_cancelled(self, task: Task) -> None:
        """Triggered whenever function finished processing."""
        task_id = task.task_id
        worker_obj = self.active_tasks.pop(task_id, None)  # remove from threads
        if worker_obj:
            logger.trace(f"Removed '{task_id}' from active tasks (cancelled).")
            # this condition is always going to be false because we don't allow cancellation of running tasks
            if worker_obj.is_running():
                self.running_queue.remove(task_id)
            else:
                with suppress(ValueError):
                    self.pending_queue.remove(task_id)
            logger.trace(f"Task '{worker_obj.summary()}' was cancelled.")
        else:
            logger.trace(f"Failed to remove '{task_id}' from active tasks (cancelled).")
        self.finished_queue.append(task_id)
        self.evt_cancelled.emit(task)  # type: ignore[unused-ignore]
        self.run_queued()

    def task_errored(self, task: Task) -> None:
        """Triggered whenever function finished processing."""
        task_id = task.task_id
        worker_obj = self.active_tasks.pop(task_id, None)  # remove from threads
        with suppress(ValueError):
            self.running_queue.remove(task_id)
            logger.trace(f"Removed '{task_id}' from running tasks (errored).")
        with suppress(ValueError):
            self.pending_queue.remove(task_id)
            logger.trace(f"Removed '{task_id}' from pending tasks (errored).")
        if worker_obj:
            logger.trace(f"Removed '{task_id}' from active tasks (errored).")
            logger.trace(f"Task '{worker_obj.summary()}' encountered an error")
            error_info = worker_obj.process.readAllStandardOutput().data().decode()
            self.evt_errored.emit(task, error_info)  # type: ignore[unused-ignore]
        else:
            logger.warning(f"Failed to remove task '{task_id}' from active tasks (errored).")
        self.finished_queue.append(task_id)
        self.run_queued()

    def task_part_errored(self, task: Task) -> None:
        """Triggered whenever function finished processing."""
        task_id = task.task_id
        worker_obj = self.active_tasks.get(task_id, None)  # remove from threads
        if worker_obj:
            logger.trace(f"Task '{worker_obj.summary()}' encountered an error")
            error_info = worker_obj.process.readAllStandardOutput().data().decode()
            self.evt_part_errored.emit(task, error_info)  # type: ignore[unused-ignore]

    def _on_finished(self, task_id: str, error_code: int) -> None:
        """Process finished."""
        if error_code == 0:
            with suppress(KeyError):
                worker_obj = self.active_tasks[task_id]
                self.task_finished(worker_obj.task)
        else:
            with suppress(KeyError):
                worker_obj = self.active_tasks[task_id]
                self.task_errored(worker_obj.task)

    def _on_error_change(self, task_id: str, state: QProcess.ProcessError) -> None:
        """Process change of process state."""
        if state == QProcess.ProcessError.FailedToStart:
            logger.error("Task failed to start")
        self._on_finished(task_id, -1)

    def _kill(self, task: Task) -> None:
        """Kill process."""
        try:
            worker_obj = self.active_tasks[task.task_id]
            worker_obj.cancel()
        except KeyError:
            logger.warning(f"Failed to cancel '{task.task_id}'")

    def add_complete_task(self, task: Task) -> None:
        """Emit the 'evt_task_queued' event WITHOUT adding task to the queue."""
        if task.state != TaskState.FINISHED:
            raise ValueError(f"Task '{task.summary()}' is not finished.")
        self.evt_queued.emit(task)  # type: ignore[unused-ignore]

    def add_task(
        self,
        task: Task,
        func_error: ty.Optional[Callback] = None,
        func_start: ty.Optional[Callback] = None,
        func_end: ty.Optional[Callback] = None,
        func_post: ty.Optional[Callback] = None,
        add_delayed: bool = True,
        emit_queued: bool = True,
    ) -> ty.Optional[str]:
        """Adds a task to the queue handler.

        The `Call` handler works by executing consecutive actions.
        1. First, it executes the `func_pre` with No parameters,
        2. Second, it executes the `func` with args and kwargs
            - if action was successful, it will run the `func_result` function with the returned values of the `func`
            - if action was unsuccessful, it will run the `func_error` with error information
        3. Third, it executes the `func_post` with `func_post_args` and `func_post_kwargs` arguments

        The `func_result`, `func_error` and `func_post` are called using the `wx.CallAfter` mechanism to ensure thread
        safety.
        """
        if self.queue_closed:
            self.evt_queue_closed.emit()  # type: ignore[unused-ignore]
            return None
        if task.task_id in self.active_tasks:
            logger.warning(f"Task '{task.summary()}' is already in the queue.")
            return None

        worker_obj = self.make_process(
            task=task,
            func_error=func_error,
            func_start=func_start,
            func_end=func_end,
            func_post=func_post,
        )
        self.add_worker(worker_obj, add_delayed=add_delayed, emit_queued=emit_queued)
        return task.task_id

    def add_worker(self, worker_obj: QProcessWrapper, add_delayed: bool = True, emit_queued: bool = True) -> None:
        """Add call object to the queue.

        Parameters
        ----------
        worker_obj : QProcessWrapper
            QRunnable object
        add_delayed : bool
            Flag to indicate whether the task should be run immediately (if possible) or if it should be added to the
            queue and the request for run is made later.
        emit_queued : bool
            Flag to indicate whether the `evt_queued` event should be emitted.
        """
        if not isinstance(worker_obj, QProcessWrapper):
            raise ValueError("You can only add 'QProcessWrapper' objects to the queue")
        logger.trace(f"Added task='{worker_obj.task_id}' to the queue (queue size {self.count()})")

        # cancel task
        task_id = worker_obj.task_id
        self.active_tasks[task_id] = worker_obj
        if task_id not in self.pending_queue:
            self.pending_queue.append(task_id)
        if emit_queued:
            self.evt_queued.emit(worker_obj.task)  # type: ignore[unused-ignore]

        # Immediately run task if in pytest environment
        if running_under_pytest():
            worker_obj.run()
            logger.trace(f"Running task '{worker_obj.task_id}' in pytest environment")
        else:
            # don't start next task
            if add_delayed or not self.is_available():
                logger.trace("Added task to queue without running it.")
                return
            worker_obj.run()
            logger.trace(f"Running task '{worker_obj.task_id}' immediately.")

    def make_process(
        self,
        task: Task,
        # task_kind: TaskKind = TaskKind.NONE,
        func_error: ty.Optional[Callback] = None,
        func_start: ty.Optional[Callback] = None,
        func_end: ty.Optional[Callback] = None,
        func_post: ty.Optional[Callback] = None,
    ) -> QProcessWrapper:
        """Make QProcess."""
        worker_obj = QProcessWrapper(self, task, func_start, func_error, func_end, func_post)
        worker_obj.evt_started.connect(self.task_started)
        worker_obj.evt_finished.connect(self.task_finished)
        worker_obj.evt_next.connect(self.evt_next.emit)  # type: ignore[unused-ignore]
        worker_obj.evt_errored.connect(self.task_errored)
        worker_obj.evt_part_errored.connect(self.task_part_errored)
        worker_obj.evt_progress.connect(self.evt_progress.emit)  # type: ignore[unused-ignore]
        worker_obj.evt_paused.connect(self.evt_paused.emit)  # type: ignore[unused-ignore]
        worker_obj.evt_cancelled.connect(self.task_cancelled)  # type: ignore[unused-ignore]
        return worker_obj

    def run_queued(self) -> None:
        """Run another object."""
        if self.queue_closed and len(self.running_queue) == 0:
            self.evt_finished_all.emit()  # type: ignore[unused-ignore]
            return

        # start another task
        if self.auto_run and self.is_available() and self.pending_queue:
            task_id = self.pending_queue.pop(0)  # get the first item
            worker_obj = self.active_tasks[task_id]  # get another worker that was queued previously
            worker_obj.run()

        if not self.pending_queue and not self.running_queue:
            self.evt_empty.emit()

    def run_force(self, task: Task) -> None:
        """Run specific task."""
        try:
            logger.trace(f"Manually starting '{task.summary()}'")
            task_id = task.task_id
            worker_obj = self.active_tasks[task_id]  # get another worker that was queued previously
            try:
                worker_obj.run()
            except Exception as e:
                logger.exception(f"Could not forcefully start specified task - '{task.summary()}'")
                self.evt_errored.emit(task, e)
        except (IndexError, KeyError, AttributeError):
            logger.exception(f"Could not forcefully start specified task - '{task.summary()}'")

    @staticmethod
    def can_cancel(_task: Task) -> ty.Tuple[bool, bool]:
        """Get information about thread."""
        return True, True

    @staticmethod
    def can_pause(_task: Task) -> bool:
        """Get information about thread."""
        return False

    def requeue(self, task: Task, remove: bool = False) -> None:
        """Add task to the queue again."""
        if remove:
            self.remove(task)
        if task.task_id in self.active_tasks:
            logger.trace(f"Task '{task.summary()}' is already in the active tasks.")
            self.evt_queued.emit(task)  # type: ignore[unused-ignore]
            return
        if task.task_id in self.pending_queue:
            logger.trace(f"Task '{task.summary()}' is already in the pending queue.")
            return
        self.add_task(task)

    def check_if_in_active(self, task: Task) -> bool:
        """Check whether task is in the active queue."""
        return task.task_id in self.active_tasks

    def check(self, task: Task) -> None:
        """Check whether task is in the pending tasks."""
        if task.task_id in self.active_tasks:
            logger.trace(f"Task '{task.summary()}' is in the active tasks.")
            return
        self.add_task(task, emit_queued=False)
        logger.trace(f"Task '{task.summary()}' is not in the queue.")

    def remove(self, task: str | Task) -> None:
        """Remove a task from the queue."""
        task_id = task if isinstance(task, str) else task.task_id
        if task_id in self.active_tasks:
            self.active_tasks.pop(task_id)
            logger.trace(f"Removed '{task_id}' from active tasks (removed).")
        if task_id in self.pending_queue:
            self.pending_queue.remove(task_id)
            logger.trace(f"Removed '{task_id}' from pending tasks (removed).")

    def cancel(self, task: Task) -> None:
        """Cancel scheduled task."""
        self._evt_cancel.emit(task)  # type: ignore[unused-ignore]

    def pause(self, task: Task, state: bool) -> None:
        """Pause task."""
        try:
            worker_obj = self.active_tasks[task.task_id]
            worker_obj.pause(state)
        except KeyError:
            logger.warning(f"Failed to pause '{task.task_id}'")
        self._evt_pause.emit(task, state)  # type: ignore[unused-ignore]

    def clear(self) -> None:
        """Safely empty queue from waiting tasks."""
        to_remove = [*self.pending_queue]
        for task_id in self.active_tasks:
            if task_id not in to_remove and task_id not in self.running_queue:
                to_remove.append(task_id)

        # cancel all scheduled tasks
        for task_id in to_remove:
            worker_obj = self.active_tasks.pop(task_id, None)
            if worker_obj:
                task = worker_obj.task
                logger.debug(f"Cancelled task '{task.summary()}'")
                with suppress(RuntimeError):
                    self._evt_cancel.emit(task)  # type: ignore[unused-ignore]
        if self.pending_queue:
            self.pending_queue.clear()
            logger.trace("Queue > Cleared queue")
        self.finished_queue.clear()

    def count(self) -> int:
        """Retrieves the count of items in the queue."""
        return len(self.pending_queue)

    def close(self) -> None:
        """Close queue."""
        self.queue_closed = True
        # cancel all scheduled tasks
        self.clear()

    def is_running(self) -> bool:
        """Indicates whether the user can close the window."""
        return len(self.running_queue) > 0

    def is_available(self) -> bool:
        """Indicates whether the queue is busy."""
        return len(self.running_queue) < self.n_parallel

    def is_queued(self, task_id: str) -> bool:
        """Check if task is queued."""
        return task_id in self.pending_queue or task_id in self.running_queue

    def is_finished(self, task_id: str) -> bool:
        """Check if task is finished."""
        return task_id in self.finished_queue

    def remove_task(self, task_id: str) -> None:
        """Remove task from queue."""

        def _remove_if_many(queue: list[str]) -> None:
            while task_id in queue:
                queue.remove(task_id)

        _remove_if_many(self.pending_queue)
        _remove_if_many(self.running_queue)
        _remove_if_many(self.finished_queue)
        with suppress(KeyError):
            worker_obj = self.active_tasks.pop(task_id)
            worker_obj.cancel()
            logger.trace(f"Removed '{task_id}' from active tasks (removed).")
        self.evt_remove_task.emit(task_id)

    def __repr__(self) -> str:
        """Representation of the queue."""
        n_running, n_queued = self.n_tasks
        return f"Queue<queued={n_queued}; running={n_running}>"
