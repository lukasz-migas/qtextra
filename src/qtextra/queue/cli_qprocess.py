"""QProcess wrapper."""

from __future__ import annotations

import time
import typing as ty
from contextlib import suppress
from queue import Empty, SimpleQueue

import psutil
from koyo.system import IS_WIN
from loguru import logger as logger_
from qtpy.QtCore import QObject, QProcess, QTimer, Signal  # type: ignore[attr-defined]
from superqt.utils import create_worker

from qtextra.queue.task import MasterTask, Task
from qtextra.queue.utilities import _safe_call, escape_ansi, iterable_callbacks
from qtextra.typing import Callback, TaskState, WorkerState


def decode(text: bytes) -> str:
    """Decode text."""
    try:
        return text.decode("utf-8-sig")
    except UnicodeDecodeError:
        return text.decode("latin1")


def take_snapshot(process_id: int) -> ty.Tuple[ty.Optional[float], ty.Optional[float]]:
    """Take CPU and memory snapshot."""
    with suppress(psutil.NoSuchProcess):
        proc = psutil.Process(process_id)
        with proc.oneshot():
            _ = proc.cpu_percent()  # need to call once before calling `cpu_percent` again
            cpu = proc.cpu_percent(0.1)
            mem = proc.memory_percent()
        # also get info about the children
        for child in proc.children(recursive=True):
            with child.oneshot():
                _ = child.cpu_percent()  # need to call once before calling `cpu_percent` again
                cpu += child.cpu_percent(0.1)
                mem += child.memory_percent()
        return cpu, mem
    return None, None


def save_snapshot(process_id: int, task: Task):
    """Save snapshot."""
    cpu, mem = take_snapshot(process_id)
    if cpu is not None and mem is not None:
        task.stats.append(time.time(), cpu, mem)


def save_output(task: Task, stdout: bytes) -> WorkerState:
    """Save stdout."""
    try:
        task.save_output(decode(stdout))
    except OSError as e:
        if e.errno == 28:
            return WorkerState.NOT_ENOUGH_SPACE
    return WorkerState.FINISHED


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

    def __init__(self, task_id: str, task_index: int, command_index: int, command_args: ty.List[str]) -> None:
        """Initialize."""
        self.task_id = task_id
        self.task_index = task_index
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
    evt_started = Signal(MasterTask)
    evt_next = Signal(MasterTask)
    evt_ended = Signal(MasterTask)
    evt_errored = Signal(MasterTask)
    evt_part_errored = Signal(MasterTask)
    evt_progress = Signal(MasterTask)
    evt_paused = Signal(MasterTask, bool)
    evt_cancelled = Signal(MasterTask)

    # properties
    _paused: bool = False
    _cancelled: bool = False
    _master_started: bool = False
    _master_finished: bool = False
    _task_queue_populated: bool = False
    n_running: int = 0

    def __init__(
        self,
        parent: QObject,
        task: MasterTask,
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
        self.process.readyReadStandardError.connect(self.on_stderr)

        self.finished_tasks: ty.Set[str] = set()
        self.task_queue: SimpleQueue[QueueTask] = Queue()
        self.command_queue: SimpleQueue[QueueCommand] = Queue()
        self.current_task_id: ty.Optional[str] = None

        # setup functions
        self.func_start = iterable_callbacks(func_start)
        self.func_error = iterable_callbacks(func_error)
        self.func_end = iterable_callbacks(func_end)
        self.func_post = iterable_callbacks(func_post)

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
        return bool(self.process.state() == QProcess.Running)  # type: ignore[attr-defined]

    def on_stdout(self) -> None:
        """Record stdout emitted by the process."""
        with suppress(KeyError, RuntimeError):
            task = self.task.get_task_for_id(self.current_task_id)
            if task:
                text = self.process.readAllStandardOutput().data().decode()
                if text:
                    task.append_output(escape_ansi(text))
                    self.evt_progress.emit(self.task)  # type: ignore[unused-ignore]

    def on_stderr(self) -> None:
        """Record stderr emitted by the process."""
        with suppress(KeyError, RuntimeError):
            task = self.task.get_task_for_id(self.current_task_id)
            if task:
                text = self.process.readAllStandardError().data().decode()
                if text:
                    task.append_output(escape_ansi(text))
                    self.evt_progress.emit(self.task)  # type: ignore[unused-ignore]

    def summary(self) -> str:
        """Return task summary."""
        return self.task.summary()

    def on_started(self) -> None:
        """The process has started."""
        self.task.state = TaskState.RUNNING
        _safe_call(self.func_start, self.task, "task_started")
        self.master_started = True
        self.evt_started.emit(self.task)  # type: ignore[unused-ignore]

    def populate_task_queue(self) -> None:
        """Add tasks to queue."""
        if self._task_queue_populated:
            self.logger.trace("Task queue was already populated. Moving on...")
            return

        # iterate over each task
        for index, task in enumerate(self.task.tasks):
            # task is locked, so we don't need to execute it
            if task.state == TaskState.FINISHED:
                self.logger.trace(f"Task '{task.task_name}' was locked and already finished. Moving on...")
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
                continue
            # check whether task was cancelled
            elif task.state == TaskState.CANCELLED:
                self.logger.trace(f"Task '{task.task_name}' was previously cancelled. Moving to the next task...")
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
                continue
            # check whether task is running
            elif task.state == TaskState.QUEUED:
                tsk = QueueTask(index, task)
                self.task_queue.put(tsk)
                self.logger.trace(f"Added '{task.task_name}' task to TaskQueue.")
        self._task_queue_populated = False
        self.logger.trace(f"Added {self.task_queue.qsize()} commands to TaskQueue.")

    def populate_command_queue(self) -> ty.Optional[str]:
        """Add commands to queue."""
        try:
            # get the next available task
            tsk: QueueTask = self.task_queue.get_nowait()
            task = tsk.task
            task_index = tsk.index
            self.logger.trace(f"Populating CommandQueue for '{task.task_name}'...")
            # check whether the task was finished and locked
            if task.state == TaskState.FINISHED:
                self.logger.trace(f"Task '{task.task_name}' was locked and already finished. Moving on...")
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            # check whether the task was cancelled
            elif task.state == TaskState.CANCELLED:
                self.logger.trace(f"Task '{task.task_name}' was cancelled. Moving to the next task...")
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            # check whether task is running or queued
            elif task.state in [TaskState.RUNNING, TaskState.QUEUED]:
                # iterate over each command and execute it
                for index, command_args in enumerate(task.command_args()):
                    cmd = QueueCommand(task.task_id, task_index, index, command_args)
                    self.command_queue.put(cmd)
                self.logger.trace(f"Added {self.command_queue.qsize()} commands to CommandQueue.")
                # all sub-commands have been previously executed so can move to the next task.
                if self.command_queue.qsize() == 0:
                    task.state = TaskState.FINISHED
                    self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (populate)")
                    return self.populate_command_queue()
                self.current_task_id = task.task_id
                return self.current_task_id
        except Empty:
            self.logger.trace(f"CommandQueue for '{self.task.task_id}' was empty. Nothing else to do...")
        return None

    def on_next_task(self) -> None:
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

                prev_task = self.task.get_task_for_id(self.current_task_id)
                if prev_task:
                    self.logger.trace(f"Retrieved '{prev_task.task_name}' as previous task (next).")
                    if prev_task.state == TaskState.RUNNING:
                        prev_task.set_state(TaskState.FINISHED)
                        self.logger.trace(
                            f"Changed state of '{prev_task.task_name}' to '{prev_task.state.value}' (next)"
                        )
                    prev_task.stats.end_time = time.time()
                    prev_task.deactivate()
                    prev_task.lock()
                    task_index = self.task.get_index_for_task_id(prev_task.task_id)
                    # if task_index is not None:
                    #     self.task.set_task_index(task_index)
                    self.finished_tasks.add(prev_task.task_id)
                    self.logger.trace(f"Added '{prev_task.task_name}' to finished tasks (next).")
                    self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
                self.task.state = TaskState.FINISHED
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
                self.evt_ended.emit(self.task)  # type: ignore[unused-ignore]
                self.logger.debug("All tasks finished.")
            # otherwise, a new task was retrieved and more commands were added to the queue
            else:
                # first, let's check if everything was finished for previous task
                prev_task = None
                if self.finished_tasks:
                    prev_task = self.task.get_task_for_id(list(self.finished_tasks)[-1])
                # else:
                #     prev_task = self.task.get_previous_task_for_id(current_task_id)
                if prev_task:
                    self.logger.trace(f"Retrieved '{prev_task.task_name}' as previous task (finished).")
                    if prev_task.state == TaskState.RUNNING:
                        prev_task.set_state(TaskState.FINISHED)
                        self.logger.trace(
                            f"Changed state of '{prev_task.task_name}' to '{prev_task.state.value}' (finished)"
                        )
                    if prev_task.stats.end_time is None:
                        prev_task.stats.end_time = time.time()
                    # self.save_stdout(prev_task)
                    # self.save_stats(prev_task)
                    prev_task.deactivate()
                    prev_task.lock()
                    self.finished_tasks.add(prev_task.task_id)
                    self.logger.trace(f"Added '{prev_task.task_name}' to finished tasks (finished).")
                    self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
                # execute the next command
                self.on_execute_task()

    def on_execute_task(self) -> None:
        """Execute tasks in the queue."""
        try:
            cmd = self.command_queue.get_nowait()
            task = self.task.get_task_for_id(cmd.task_id)
            command_args = cmd.command_args
            command_index = cmd.command_index
            command = " ".join(command_args)
            if not task:
                raise ValueError("Task not found.")
            # set start time
            if command_index == 0:
                task.stats.start_time = time.time()
            # activate master task
            # activate the current task
            if not task.is_active():
                task.activate()
            # update state so that it's running
            if task.state != TaskState.RUNNING:
                task.set_state(TaskState.RUNNING)
                self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (execute)")

            # get program and commands
            program, args = command_args[0], command_args[1:]
            self.process.setProgram(program)
            # Under Windows, the `setArguments` arguments are wrapped in a string which renders the arguments
            # incorrect. It's safer to simply join the arguments  together and set them as one long string. The
            # assumption is that the arguments were properly setup in the first place!
            if IS_WIN:
                self.process.setNativeArguments(" ".join(args))  # type: ignore[attr-defined]
            else:
                self.process.setArguments(args)
            # self.process.setStandardOutputFile(task.) # TODO: should we do this?
            # update task info
            task.set_command_index(command_index)
            self.logger.trace(f"Executing: {task.task_name} / {command_index} : {command}")
            # start the next task
            self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            self.start()
        except Empty:
            self.logger.trace("The queue was empty. Going to try to get next task...")
            self.on_next_task()

    def on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """The process has finished."""
        # handle non-zero exit code
        if exit_code != 0:
            self.logger.error(f"Task exited with non-zero exit code. ({exit_code}; {exit_status!s})")
            self.on_error(self.process.error())
            return

        # the task has finished
        task = self.task.get_task_for_id(self.current_task_id)
        if task and self.master_started:
            # check if there are any other tasks in the queue
            if self.command_queue.empty():
                if task.state == TaskState.RUNNING:
                    task.set_state(TaskState.FINISHED)
                    self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (finished)")
                # lock task
                task.lock()
                self.finished_tasks.add(task.task_id)
                self.evt_next.emit(self.task)  # type: ignore[unused-ignore]
            # update stats
            # self.save_stdout(task)
            # self.save_stats(task)
            self.logger.trace(f"Task finished successfully: '{task.task_name}' (finished)")

        # all tasks have finished
        if self.master_finished:
            if task:
                # update stats
                if task.state == TaskState.RUNNING:
                    task.set_state(TaskState.FINISHED)
                    self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (all-finished)")
                # self.save_stdout(task)
                # self.save_stats(task)
                # lock task
                task.lock()
                self.finished_tasks.add(task.task_id)
                self.logger.trace(f"Added '{task.task_name}' to finished tasks (all-finished).")
                self.logger.debug("Task finished successfully.")
        self.on_next_task()

    def on_error(self, _error: ty.Any) -> None:
        """Process has errored."""
        self.process.setProgram(None)  # type: ignore[arg-type]
        self.task.state = TaskState.FAILED
        # update stdout
        task = self.task.get_task_for_id(self.current_task_id)
        if task:
            if task.state != TaskState.FINISHED:
                task.set_state(TaskState.FAILED)
                self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (error)")
                # self.save_stdout(task)
                # self.save_stats(task)
                # lock task
                task.lock()
                # if task was optional, move to the next ste[
                if task.config.optional:
                    self.command_queue.clear()  # type: ignore[attr-defined]
                    self.task.state = TaskState.RUNNING  # optional tasks should not result in failed states...
                    self.logger.warning(f"Task '{task.task_name}' failed but was optional. Moving to the next task...")
                    self.evt_part_errored.emit(self.task)  # type: ignore[unused-ignore]
                    return self.on_next_task()
        # previous task was not optional
        self.master_started = False
        if self._cancelled:
            self.task.state = TaskState.CANCELLED
            self.evt_cancelled.emit(self.task)  # type: ignore[unused-ignore]
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
            self.on_next_task()

        process_state = self.process.state()
        process_id = self.process.processId()
        if (process_state == QProcess.NotRunning) and process_id == 0:  # type: ignore[unused-ignore, attr-defined]
            if self._paused:
                self.task.state = TaskState.PAUSED
                self.evt_paused.emit(self.task, self._paused)  # type: ignore[unused-ignore]
                self.logger.trace(f"Task '{self.task.summary()}' was successfully paused")
            elif self._cancelled:
                self.task.state = TaskState.CANCELLED
                self.evt_cancelled.emit(self.task)  # type: ignore[unused-ignore]
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
        self.logger.debug(f"{'Pausing' if paused else 'Resuming'} '{self.task.summary()}'")

    def cancel(self) -> None:
        """Cancel process."""
        self._cancelled = True
        self.task.state = TaskState.CANCELLING if self.is_running() else TaskState.CANCELLED
        try:
            while self.task_queue.qsize() > 0:
                task = self.task_queue.get_nowait().task
                # task.set_state(TaskState.CANCELLED)
                self.logger.trace(f"Changed state of '{task.task_name}' to '{task.state.value}' (cancel)")
        except Empty:
            pass
        if self.is_running():
            kill_timer = QTimer(self.process)
            kill_timer.singleShot(3000, self.process.kill)  # wait 3 second for process to be killed
            self.process.terminate()
        else:
            self.evt_cancelled.emit(self.task)  # type: ignore[unused-ignore]
        self.master_started = False
        self.logger.debug(f"Cancelling '{self.task.summary()}'")
