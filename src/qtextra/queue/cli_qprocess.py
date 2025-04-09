"""QProcess wrapper."""

from __future__ import annotations

import typing as ty
from contextlib import suppress
from queue import Empty, SimpleQueue
from time import time as time_

from koyo.system import IS_WIN
from loguru import logger as logger_
from qtpy.QtCore import QObject, QProcess, QTimer, Signal  # type: ignore[attr-defined]

from qtextra.queue.task import Task
from qtextra.queue.utilities import _safe_call, escape_ansi, iterable_callbacks
from qtextra.typing import Callback, TaskState


def run_command(command: list[str]) -> None:
    """Execute command using the QProcess wrapper."""
    from qtextra.helpers import get_main_window

    program, args = command[0], command[1:]
    logger_.trace(f"Running command: {program} {' '.join(args)}")

    process = QProcess(get_main_window())
    process.finished.connect(process.deleteLater)
    process.finished.connect(lambda exit_code, exit_status: logger_.trace(f"Command finished with {exit_code}"))
    process.setProgram(program)
    # Under Windows, the `setArguments` arguments are wrapped in a string which renders the arguments
    # incorrect. It's safer to simply join the arguments  together and set them as one long string. The
    # assumption is that the arguments were properly setup in the first place!
    if IS_WIN and hasattr(process, "setNativeArguments"):
        process.setNativeArguments(" ".join(args))
    else:
        process.setArguments(args)
    process.start()


def decode(text: bytes) -> str:
    """Decode text."""
    try:
        return text.decode("utf-8-sig")
    except UnicodeDecodeError:
        return text.decode("latin1")


class Queue(SimpleQueue):
    """Queue class with few missing methods."""

    def clear(self) -> None:
        """Clear queue."""
        while not self.empty():
            try:
                self.get_nowait()
            except Empty:
                break


class QueueCommand:
    """Command."""

    def __init__(self, task_id: str, command_index: int, command_args: list[str]) -> None:
        """Initialize."""
        self.task_id = task_id
        self.command_index = command_index
        self.command_args = command_args


class QueueTask:
    """Task."""

    def __init__(self, index: int, task: Task) -> None:
        """Initialize."""
        self.index = index
        self.task = task


class QProcessWrapper(QObject):
    """Wrapper around QProcess that handles multiple tasks."""

    # signals
    evt_started = Signal(Task)
    evt_next = Signal(Task)
    evt_finished = Signal(Task)
    evt_errored = Signal(Task)
    evt_part_errored = Signal(Task)
    evt_progress = Signal(Task)
    evt_paused = Signal(Task, bool)
    evt_cancelled = Signal(Task)

    # properties
    _paused: bool = False
    _cancelled: bool = False
    _master_started: bool = False
    _master_finished: bool = False
    _task_queue_populated: bool = False
    _cancel_emitted: bool = False
    n_running: int = 0

    def __init__(
        self,
        parent: QObject,
        task: Task,
        func_start: ty.Optional[Callback] = None,
        func_error: ty.Optional[Callback] = None,
        func_end: ty.Optional[Callback] = None,
        func_post: ty.Optional[Callback] = None,
    ):
        """Initialize."""
        super().__init__(parent=parent)
        self.logger = logger_.bind(src=task.task_id)
        self.task = task

        # setup process
        self.process = QProcess(parent=self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.started.connect(self.on_started)
        self.process.finished.connect(self.on_finished)
        self.process.errorOccurred.connect(self.on_error)
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        # self.process.readyReadStandardError.connect(self.on_stderr)

        self.finished_tasks: ty.Set[str] = set()
        self.command_queue: SimpleQueue = Queue()
        self.current_task_id: ty.Optional[str] = None

        # setup functions
        self.func_start = iterable_callbacks(func_start)
        self.func_error = iterable_callbacks(func_error)
        self.func_end = iterable_callbacks(func_end)
        self.func_post = iterable_callbacks(func_post)

    def on_stdout(self) -> None:
        """Record stdout emitted by the process."""
        with suppress(KeyError, RuntimeError):
            if self.task:
                text = self.process.readAllStandardOutput().data()
                try:
                    text = decode(text)  # type: ignore[assignment]
                    if text:
                        self.task.append_output(escape_ansi(text))  # type: ignore[arg-type]
                        self.evt_progress.emit(self.task)  # type: ignore[unused-ignore]
                except UnicodeDecodeError as e:
                    self.logger.trace(f"Could not decode stdout. {e} - {text}")  # type: ignore[str-bytes-safe]
                    return

    def on_stderr(self) -> None:
        """Record stderr emitted by the process."""
        with suppress(KeyError, RuntimeError):
            if self.task:
                text = self.process.readAllStandardError().data()
                text = decode(text)  # type: ignore[assignment]
                if text:
                    self.task.append_output(escape_ansi(text))  # type: ignore[arg-type]
                    self.evt_progress.emit(self.task)  # type: ignore[unused-ignore]

    @property
    def master_started(self) -> bool:
        """Return bool if a task had started."""
        return self._master_started

    @master_started.setter
    def master_started(self, value: bool) -> None:
        """Set task had started."""
        self._master_started = value
        self._master_finished = not value

    @property
    def master_finished(self) -> bool:
        """Return bool if a task had started."""
        return self._master_finished

    @property
    def task_id(self) -> str:
        """Return task id."""
        return self.task.task_id

    def is_running(self) -> bool:
        """Flag to indicate whether the task is running."""
        return bool(self.process.state() == QProcess.ProcessState.Running)

    def summary(self) -> str:
        """Return task summary."""
        return self.task.task_name

    def on_started(self) -> None:
        """The process has started."""
        self.task.state = TaskState.RUNNING
        _safe_call(self.func_start, self.task, "task_started")
        self.master_started = True
        self.evt_started.emit(self.task)  # type: ignore[unused-ignore]

    def populate_command_queue(self) -> ty.Optional[str]:
        """Add commands to queue."""
        if not self._task_queue_populated:
            self._task_queue_populated = True
            self.logger.trace(f"Populating CommandQueue for '{self.task.task_name}'...")
            # check whether the task was finished and locked
            if self.task.state == TaskState.FINISHED:
                self.logger.trace(f"Task '{self.task.task_name}' was locked and already finished. Moving on...")
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            # check whether the task was cancelled
            elif self.task.state == TaskState.CANCELLED:
                self.logger.trace(f"Task '{self.task.task_name}' was cancelled. Moving to the next task...")
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            # check whether task is running or queued
            elif self.task.state in [TaskState.RUNNING, TaskState.QUEUED]:
                # iterate over each command and execute it
                for index, command_args in enumerate(self.task.command_args()):
                    cmd = QueueCommand(self.task.task_id, index, command_args)
                    self.command_queue.put(cmd)
                self.logger.trace(f"Added {self.command_queue.qsize()} commands to CommandQueue.")
                # all sub-commands have been previously executed so can move to the next task.
                if self.command_queue.qsize() == 0:
                    self.task.state = TaskState.FINISHED
                    self.logger.trace(
                        f"Changed state of '{self.task.task_name}' to '{self.task.state.value}' (populate)"
                    )
                    return self.populate_command_queue()
                self.current_task_id = self.task.task_id
                return self.current_task_id
        else:
            self.logger.trace(f"CommandQueue for '{self.task.task_id}' was empty. Nothing else to do...")
        return None

    def on_setup_task(self) -> None:
        """Execute next task."""
        # check whether the queue is empty
        # if it's not, execute the next available command
        if not self.command_queue.empty():
            self.on_execute_task()
        # if it is, populate it with more commands from the next available task
        else:
            # populate the queue
            current_task_id = self.populate_command_queue()
            # if there were no more  tasks, the `current_task_id` will be None
            if current_task_id is None:
                self.logger.trace("There are no more tasks to execute. Finishing up...")
                self.master_started = False
                self.task.state = TaskState.FINISHED
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
                self.evt_finished.emit(self.task)  # type: ignore[unused-ignore]
                self.logger.debug("All tasks finished.")
            # otherwise, a new task was retrieved and more commands were added to the queue
            else:
                # execute the next command
                self.on_execute_task()

    def on_execute_task(self) -> None:
        """Execute tasks in the queue."""
        try:
            cmd: QueueCommand = self.command_queue.get_nowait()
            command_args = cmd.command_args
            command_index = cmd.command_index
            command = " ".join(command_args)
            if not self.task:
                raise ValueError("Task not found.")
            # set start time
            if command_index == 0:
                self.task.start_time = time_()
            # activate master task
            # activate the current task
            if not self.task.is_active():
                self.task.activate()
            # update state so that it's running
            if self.task.state != TaskState.RUNNING:
                self.task.state = TaskState.RUNNING
                self.logger.trace(f"Changed state of '{self.task.task_name}' to '{self.task.state.value}' (execute)")

            # get program and commands
            program, args = command_args[0], command_args[1:]
            self.process.setProgram(program)
            # Under Windows, the `setArguments` arguments are wrapped in a string which renders the arguments
            # incorrect. It's safer to simply join the arguments  together and set them as one long string. The
            # assumption is that the arguments were properly setup in the first place!
            if IS_WIN:
                if hasattr(self.process, "setNativeArguments"):
                    self.process.setNativeArguments(" ".join(args))  # type: ignore[attr-defined]
                else:
                    self.logger.error("QProcess does not support setNativeArguments. Using setArguments instead.")
                    self.process.setArguments(args)
            else:
                self.process.setArguments(args)
            # update task info
            self.task.set_command_index(command_index)
            self.logger.trace(f"Executing: {self.task.task_name} / {command_index} : {command}")
            # start the next task
            self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            self.start()
        except Empty:
            self.logger.trace("The queue was empty. Going to try to get next task...")

    def on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """The process has finished."""
        # handle non-zero exit code
        if exit_code != 0:
            self.logger.error(f"Task exited with non-zero exit code. ({exit_code}; {exit_status!s})")
            self.on_error(self.process.error())
            return

        # the task has finished
        task = self.task
        if task and self.master_started:
            # check if there are any other tasks in the queue
            if self.command_queue.empty():
                if task.state == TaskState.RUNNING:
                    task.state = TaskState.FINISHED
                    self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (finished)")
                task.lock()  # lock task
                self.finished_tasks.add(task.task_id)
                # self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            self.logger.trace(f"Task finished successfully: '{task.task_name}' (finished)")
            self.on_setup_task()

        # all tasks have finished
        if self.master_finished:
            if task:
                # update stats
                if task.state == TaskState.RUNNING:
                    task.state = TaskState.FINISHED
                    self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (all-finished)")
                task.end_time = time_()
                task.lock()  # lock task
                self.finished_tasks.add(task.task_id)
                self.logger.trace(f"Added '{task.task_name}' to finished tasks (all-finished).")
                self.logger.debug("Task finished successfully.")

    def on_error(self, _error: ty.Any) -> None:
        """Process has errored."""
        self.process.setProgram(None)  # type: ignore[arg-type]
        self.task.state = TaskState.FAILED
        if self.task.state != TaskState.FINISHED:
            self.task.state = TaskState.FAILED
            self.logger.trace(f"Changed state of '{self.task.task_name}' to '{self.task.state.value}' (error)")
            self.task.lock()  # lock task
        self.command_queue.clear()
        self.task.end_time = time_()
        self.master_started = False
        if self._cancelled:
            self.task.state = TaskState.CANCELLED
            self._emit_cancel()
        else:
            self.evt_errored.emit(self.task)  # type: ignore[unused-ignore]
        _safe_call(self.func_error, self.task, "task_errored")

    def run(self) -> None:
        """Execute task."""
        if self.master_started:
            self.logger.debug("Task has already started.")
            return
        self.master_started = True
        self.start()

    def start(self) -> None:
        """Start the process."""
        # if the task state has not been changed to started, let's don't do anything
        if not self.master_started:
            self.logger.debug("Task could not start as 'master_started' is not set.")
            return
        # this is the first process
        if not self.process.program():
            self.logger.debug("Setting-up task (start)...")
            self.on_setup_task()

        process_state = self.process.state()
        process_id = self.process.processId()
        if process_state == QProcess.ProcessState.NotRunning or process_id == 0:
            if self._paused:
                self.task.state = TaskState.PAUSED
                self.evt_paused.emit(self.task, self._paused)  # type: ignore[unused-ignore]
                self.logger.trace(f"Task '{self.task.task_name}' was successfully paused")
            elif self._cancelled:
                self.task.state = TaskState.CANCELLED
                self._emit_cancel()
            else:
                self.logger.trace(
                    f"Starting task. state={process_state!s}; process_id={process_id!s}; paused={self._paused!s};"
                    f" cancelled={self._cancelled!s}"
                )
                self.process.start()

    def pause(self, paused: bool) -> None:
        """Pause process."""
        self._paused = paused
        self.task.state = TaskState.PAUSING if paused else TaskState.RUNNING
        self.start()
        self.logger.debug(f"{'Pausing' if paused else 'Resuming'} '{self.task.task_name}'")

    def cancel(self) -> None:
        """Cancel process."""
        self._cancelled = True
        self.task.state = TaskState.CANCELLING if self.is_running() else TaskState.CANCELLED
        try:
            while self.command_queue.qsize() > 0:
                self.command_queue.get_nowait()
            self.logger.trace(f"Changed state of '{self.task.task_name}' to '{self.task.state.value}' (cancel)")
        except Empty:
            pass
        if self.is_running():
            kill_timer = QTimer(self.process)
            kill_timer.singleShot(3000, self.process.kill)  # wait 3 second for process to be killed
            self.process.terminate()
        else:
            self._emit_cancel()
        self.master_started = False
        self.logger.debug(f"Cancelling '{self.task.task_name}'")

    def _emit_cancel(self) -> None:
        if not self._cancel_emitted:
            self._cancel_emitted = True
            self.evt_cancelled.emit(self.task)
