"""Queue widget."""

from __future__ import annotations

import typing as ty
from contextlib import suppress

from loguru import logger
from qtpy.QtCore import Qt, Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QScrollArea, QSizePolicy, QVBoxLayout, QWidget

import qtextra.helpers as hp
from qtextra.queue.cli_queue import CLIQueueHandler
from qtextra.queue.item import TaskWidget
from qtextra.queue.task import Task
from qtextra.typing import TaskState

logger = logger.bind(src="QueueWidget")


QUEUE = CLIQueueHandler()


class QueueList(QScrollArea):
    """Manager object."""

    MAX_TASKS: int = 500
    AUTO_EXPAND: bool = False

    evt_console = Signal(object)

    _hidden = False

    def __init__(self, parent: ty.Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.widgets: dict[str, TaskWidget] = {}
        self.finished_widgets: list[TaskWidget] = []
        self.cancelled_widgets: list[TaskWidget] = []
        self.failed_widgets: list[TaskWidget] = []

        # states
        self.selected: ty.Sequence[str] = ["running", "queued", "paused", "finished", "failed", "cancelled"]

        # connect signals
        QUEUE.evt_queued.connect(self.on_task_queued)
        QUEUE.evt_started.connect(self.on_task_started)
        QUEUE.evt_paused.connect(self.on_task_paused)
        QUEUE.evt_next.connect(self.on_task_next)
        QUEUE.evt_finished.connect(self.on_task_finished)
        QUEUE.evt_errored.connect(self.on_task_failed)
        QUEUE.evt_part_errored.connect(self.on_task_part_failed)
        QUEUE.evt_cancelled.connect(self.on_task_cancelled)
        QUEUE.evt_progress.connect(self.on_task_progress)
        QUEUE.evt_remove_task.connect(self.on_remove_task)

        # setup UI
        scroll_widget = QWidget()  # type: ignore[unused-ignore]
        self.setWidget(scroll_widget)

        main_layout = QVBoxLayout(scroll_widget)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.addStretch(1)
        self._layout = main_layout

    def __repr__(self) -> str:
        """Repr."""
        return (
            f"{self.__class__.__name__}<{len(self.widgets)} widgets; {len(self.finished_widgets)} finished;"
            f" {len(self.cancelled_widgets)} cancelled; {len(self.failed_widgets)} failed>"
        )

    def widget_iter(self) -> ty.Iterable[TaskWidget]:
        """Iterate over widgets."""
        yield from self.widgets.values()
        yield from self.finished_widgets
        yield from self.cancelled_widgets
        yield from self.failed_widgets

    def task_iter(self) -> ty.Iterable[Task]:
        """Iterate over all tasks."""
        for widget in self.widget_iter():
            if widget.task:
                yield widget.task

    def validate(self, selected: ty.Optional[ty.Sequence[str]] = None) -> None:
        """Validate."""
        if selected is not None:
            self.selected = selected
        for widget in self.widgets.values():
            if widget.task:
                widget.setVisible(widget.task.state in self.selected)
        for widget in self.widget_iter():
            if widget.task:
                widget.setVisible(widget.task.state in self.selected)

    def purge_finished(self, max_tasks: ty.Optional[ty.Optional[int]] = None) -> None:
        """Purge tasks that are no longer necessary."""
        if max_tasks is None:
            max_tasks = self.MAX_TASKS
        if len(self.finished_widgets) > max_tasks:
            logger.trace(f"Purging finished tasks ({len(self.finished_widgets)}>{max_tasks}...")
            widgets = self.finished_widgets[max_tasks::]
            for widget in widgets:
                self._layout.removeWidget(widget)
                widget.deleteLater()
                del self.finished_widgets[self.finished_widgets.index(widget)]
                if widget.task:
                    logger.trace(f"Removed widget for '{widget.task.summary()}'")
        self.validate()

    def purge_all(self) -> None:
        """Remove all tasks."""
        logger.trace("Purging all tasks...")
        for widget in self.widget_iter():
            with suppress(RuntimeError):
                self._layout.removeWidget(widget)
            with suppress(RuntimeError):
                widget.deleteLater()
            with suppress(RuntimeError):
                if widget.task:
                    logger.trace(f"Removed widget for '{widget.task.summary()}'")
        self.widgets.clear()
        self.finished_widgets.clear()
        self.cancelled_widgets.clear()
        self.failed_widgets.clear()
        QUEUE.clear()
        self.validate()

    # # @Slot(Task)
    @staticmethod
    def on_start_task(task: Task) -> None:
        """Cancel task."""
        QUEUE.run_force(task)

    def on_requeue_task(self, task: Task) -> None:
        """Re-add task to the queue."""
        self._remove_widget(task)
        task.state = TaskState.QUEUED
        QUEUE.requeue(task, remove=True)

    def on_remove_task(self, task: str | Task) -> None:
        """Remove task from the queue."""
        self._remove_widget(task)
        QUEUE.remove(task)

    @staticmethod
    def on_check_task(task: Task) -> None:
        """Check whether task is in the queue."""
        QUEUE.check(task)

    @staticmethod
    def on_cancel_task(task: Task) -> None:
        """Cancel task."""
        QUEUE.cancel(task)

    @staticmethod
    def on_pause_task(task: Task, state: bool) -> None:
        """Cancel task."""
        QUEUE.pause(task, state)

    def _remove_widget(self, task: str | Task) -> None:
        # remove widget from the UI
        task_id = task.task_id if isinstance(task, Task) else task
        widget = self._find_widget(task)
        if widget:
            self._layout.removeWidget(widget)
            widget.deleteLater()
            widget.setParent(None)  # type: ignore[call-overload]
            if widget in self.finished_widgets:
                del self.finished_widgets[self.finished_widgets.index(widget)]
            if widget in self.failed_widgets:
                del self.failed_widgets[self.failed_widgets.index(widget)]
            if widget in self.cancelled_widgets:
                del self.cancelled_widgets[self.cancelled_widgets.index(widget)]
            self.widgets.pop(task_id, None)
            del widget
            logger.trace(f"Removed widget for '{task_id}'")

    def _find_widget(self, task: str | Task) -> ty.Optional[TaskWidget]:
        """Find widget by its task ID."""
        task_id = task.task_id if isinstance(task, Task) else task
        if task_id in self.widgets:
            return self.widgets[task_id]
        for widget in self.finished_widgets:
            if widget.task and widget.task.task_id == task_id:
                return widget
        for widget in self.cancelled_widgets:
            if widget.task and widget.task.task_id == task_id:
                return widget
        for widget in self.failed_widgets:
            if widget.task and widget.task.task_id == task_id:
                return widget
        return None

    def check_if_exists(self, task: Task) -> bool:
        """Check if task exists."""
        for task_ in self.task_iter():
            if task.task_id == task_.task_id:
                return True
        return False

    def on_task_queued(self, task: Task) -> None:
        """Task started."""
        if self.check_if_exists(task):
            logger.debug("Task already exists in the queue, skipping...")
            return

        task_id = task.task_id
        can_cancel, can_cancel_when_started = QUEUE.can_cancel(task)
        can_pause = QUEUE.can_pause(task)

        widget = TaskWidget()
        widget.set_task(
            task,
            can_cancel=can_cancel,
            can_pause=can_pause,
            can_cancel_when_started=can_cancel_when_started,
            can_force_start=QUEUE.CAN_FORCE_START,
            auto_expand=self.AUTO_EXPAND,
        )
        widget.evt_start_task.connect(self.on_start_task)
        widget.evt_cancel_task.connect(self.on_cancel_task)
        widget.evt_pause_task.connect(self.on_pause_task)
        widget.evt_requeue_task.connect(self.on_requeue_task)
        widget.evt_console.connect(self.evt_console.emit)  # type: ignore[unused-ignore]
        self._layout.insertWidget(0, widget)
        # if the task is already finished, add it to the finished list
        if task.state == TaskState.FINISHED:
            self.finished_widgets.append(widget)
        else:
            self.widgets[task_id] = widget
        self.purge_finished()

    def on_clear_queue(self, force: bool = False) -> None:
        """Clear the table, but first ask for confirmation."""
        if force or hp.confirm(
            self, "Are you sure you wish to remove <b>all</b> tasks from the list?", "Clear queue..."
        ):
            self.purge_all()

    def on_requeue_failed(self) -> None:
        """Requeue all failed tasks."""
        tasks = [task.task for task in self.failed_widgets if task.task]
        for task in tasks:
            self.on_requeue_task(task)

    def on_requeue_cancelled(self) -> None:
        """Requeue all cancelled tasks."""
        tasks = [task.task for task in self.cancelled_widgets if task.task]
        for task in tasks:
            self.on_requeue_task(task)

    def on_task_started(self, task: Task) -> None:
        """Task finished."""
        widget = self._find_widget(task)
        if widget:
            widget.started()
            self.validate()
        else:
            logger.warning(f"Could not find widget for task '{task.task_id}' (start)")

    def on_task_paused(self, task: Task, paused: bool) -> None:
        """Task finished."""
        widget = self._find_widget(task)
        if widget:
            widget.paused(paused)
            self.validate()
        else:
            logger.warning(f"Could not find widget for task '{task.task_id}' (paused)")

    def on_task_next(self, task: Task) -> None:
        """Task finished."""
        widget = self._find_widget(task)
        if widget:
            widget.next()
            self.validate()
        else:
            logger.warning(f"Could not find widget for task '{task.task_id}' (next)")

    def on_task_finished(self, task: Task) -> None:
        """Task finished."""
        widget = self.widgets.pop(task.task_id, None)
        if widget:
            widget.stop()
            self.finished_widgets.insert(1, widget)
        else:
            widget = self._find_widget(task)
            if widget:
                widget.stop()
            logger.warning(f"Could not find widget for task '{task.task_id}' (finished)")
        self.purge_finished()

    def on_task_failed(self, task: Task, _exc_info: ty.Tuple) -> None:
        """Task failed."""
        widget = self.widgets.pop(task.task_id, None)
        if widget:
            widget.stop()
            self.failed_widgets.insert(1, widget)
        else:
            widget = self._find_widget(task)
            if widget:
                widget.stop()
            logger.warning(f"Could not find widget for task '{task.task_id}' (failed)")
        self.purge_finished()

    # @Slot(Task, tuple)
    def on_task_part_failed(self, task: Task, _exc_info: ty.Tuple) -> None:
        """Task failed."""
        widget = self._find_widget(task)
        if widget:
            widget.part_failed()

    # @Slot(Task)
    def on_task_cancelled(self, task: Task) -> None:
        """Task was cancelled."""
        widget = self.widgets.pop(task.task_id, None)
        if widget:
            widget.cancelled()
            self.cancelled_widgets.insert(1, widget)
        else:
            widget = self._find_widget(task)
            if widget:
                widget.cancelled()
            logger.warning(f"Could not find widget for task '{task.task_id}' (cancelled)")
        self.purge_finished()

    def on_task_progress(self, task: Task) -> None:
        """Task progressed."""
        widget = self._find_widget(task)
        if widget:
            widget.update_progress()
