"""Task widget."""

from __future__ import annotations

import os
import typing as ty

from koyo.timer import MeasureTimer
from loguru import logger
from qtpy.QtCore import Qt, QTimer, Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFrame, QGridLayout, QWidget

import qtextra.helpers as hp
from qtextra.queue.task import Task
from qtextra.queue.utilities import format_command, format_interval
from qtextra.typing import TaskState
from qtextra.widgets.qt_button_icon import QtPauseButton

if ty.TYPE_CHECKING:
    from qtextra.queue.info import TaskInfoDialog

logger = logger.bind(src="TaskWidget")

IS_DEV = os.environ.get("DEV_MODE", "0") == "1"


class TaskWidget(QFrame):
    """Widget controlling and displaying task information."""

    evt_start_task = Signal(Task)
    evt_requeue_task = Signal(Task)
    evt_cancel_task = Signal(Task)
    evt_pause_task = Signal(Task, bool)
    evt_console = Signal(object)

    task: Task | None
    can_cancel: bool
    can_pause: bool
    can_cancel_when_started: bool
    can_force_start: bool

    dlg_info: TaskInfoDialog | None = None

    def __init__(self, parent: QWidget | None = None, toggled: bool = True):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self.on_update_timer)

        self.task_name = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            enable_url=True,
            func_clicked=self.on_toggle_visibility,
            elide_mode=Qt.TextElideMode.ElideRight,
        )
        self.task_state = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignCenter,
            object_name="task_state",
        )
        self.task_state.setMaximumWidth(90)

        self.task_info = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            enable_url=True,
        )
        self.time_info = hp.make_label(self, "", alignment=Qt.AlignmentFlag.AlignCenter)

        self.options_btn = hp.make_qta_btn(
            self,
            "settings",
            tooltip="Show extra actions.",
            normal=True,
            func=self.on_open_menu,
        )
        self.options_btn.hide()  # disable for now

        self.clipboard_btn = hp.make_qta_btn(
            self,
            "clipboard",
            tooltip="Copy CLI commands to the clipboard.",
            normal=True,
            func=self.on_copy_to_clipboard,
        )
        self.info_btn = hp.make_qta_btn(
            self,
            "info",
            tooltip="Show information about the task.",
            normal=True,
            func=self.on_task_info,
        )

        self.start_btn = hp.make_qta_btn(
            self,
            "run",
            tooltip="Start task if the task has not started yet. This will override any built-in restrictions on number"
            " of simultaneous tasks and can cause your system to freeze.",
            normal=True,
            func=self.on_start_task,
        )
        self.retry_btn = hp.make_qta_btn(
            self, "retry", tooltip="Retry running task if the task has failed.", normal=True, func=self._on_retry_task
        )
        self.pause_btn = QtPauseButton(self)
        self.pause_btn.set_normal()
        self.pause_btn.setToolTip("Pause running task.")
        self.pause_btn.clicked.connect(self._on_pause_task)  # type: ignore[unused-ignore]
        self.cancel_btn = hp.make_qta_btn(
            self,
            "cross_full",
            tooltip="Cancel task. If a task has started, this is not guaranteed to work!",
            normal=True,
            func=self._on_cancel_task,
        )
        self.task_id = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            object_name="task_id",
        )

        layout = QGridLayout(self)
        # widget, row, column, rowspan, colspan
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.setColumnStretch(0, 1)
        # row 0
        layout.addWidget(self.task_name, 0, 0, 1, 1)
        layout.addWidget(self.time_info, 0, 1, 1, 1)
        layout.addWidget(self.task_state, 0, 2, 1, 1)
        # row 1
        layout.addWidget(self.task_info, 1, 0, 1, 3)
        # row 2
        layout.addLayout(
            hp.make_h_layout(
                self.options_btn,
                self.clipboard_btn,
                self.info_btn,
                self.start_btn,
                self.retry_btn,
                self.pause_btn,
                self.cancel_btn,
                stretch_before=True,
                spacing=2,
            ),
            1,
            1,
            1,
            2,
        )
        # row 3
        layout.addWidget(self.task_id, 3, 0, 1, 1)

        # setup buttons
        hp.disable_widgets(self.retry_btn, self.pause_btn, disabled=True)
        self.toggled = toggled

    @property
    def toggled(self) -> bool:
        """Return state of toggled."""
        return self._toggled

    @toggled.setter
    def toggled(self, value: bool) -> None:
        self._toggled = value
        self.toggle_visibility()

    def on_toggle_visibility(self) -> None:
        """Toggle visibility."""
        self.toggled = not self.toggled

    def toggle_visibility(self) -> None:
        """Hide certain widgets."""
        hp.hide_widgets(
            self.task_info,
            self.start_btn,
            self.retry_btn,
            self.pause_btn,
            self.cancel_btn,
            # self.options_btn,
            self.info_btn,
            self.clipboard_btn,
            hidden=self.toggled,
        )

    def set_task(
        self,
        task: Task,
        can_cancel: bool = False,
        can_pause: bool = False,
        can_cancel_when_started: bool = False,
        can_force_start: bool = False,
        auto_expand: bool = True,
    ) -> None:
        """Setup UI for task."""
        with MeasureTimer() as timer:
            self.task = task
            self.can_cancel = can_cancel
            self.can_cancel_when_started = can_cancel_when_started
            self.can_pause = can_pause
            self.can_force_start = can_force_start

            # update ui
            self.task_name.setText(task.task_name_repr or hp.hyper(task.task_name))
            self.task_name.setToolTip(task.task_name_tooltip or task.task_name)
            self.task_info.setText(task.pretty_info)
            self.task_id.setText(f"Task ID: {task.task_id}")
            if task.state == TaskState.FINISHED:
                self.stop()
            else:
                hp.disable_widgets(self.start_btn, self.cancel_btn, disabled=False)
            self._update_state()
            self._update_warnings()
            self.toggled = not auto_expand
        logger.trace(f"Added task '{self.task.summary()}' in {timer()}")

    def _update_warnings(self) -> None:
        """Generate warnings for task."""
        # errors: list[str] = []
        # if self.task:
        #     errors = self.task.config_errors()
        # tooltip = "<br>".join(errors)
        # state, color = get_icon_state(errors)
        # self.errors_btn.setIcon(hp.make_qta_icon(state, color=color))  # type: ignore[no-untyped-call]
        # self.errors_btn.setToolTip(tooltip)

    def on_copy_to_clipboard(self) -> None:
        """Copy commands to clipboard."""
        if self.task:
            commands = list(self.task.command_iter())
            commands = [" ".join(cmd) for cmd in commands]
            hp.copy_text_to_clipboard(format_command(commands, IS_DEV))
            hp.add_flash_animation(self, duration=1000)

    def on_task_info(self) -> None:
        """Show widget with information about the task."""
        if self.task:
            from qtextra.queue.info import TaskInfoDialog

            try:
                if self.dlg_info is None:
                    self.dlg_info = TaskInfoDialog(self, self.task)
                    self.dlg_info.evt_update.connect(self.on_update_timer)
                self.dlg_info.show()
                self.dlg_info.raise_()
            except RuntimeError:
                self.dlg_info = None
                logger.error("Failed to show task info dialog.")
                self.on_task_info()

    def update_progress(self) -> None:
        """Update progress."""
        try:
            if self.dlg_info:
                self.dlg_info.update_progress()
        except (AttributeError, RuntimeError, Exception):
            self.dlg_info = None

    def on_open_menu(self) -> None:
        """Open folder menu."""

    def _on_retry_task(self) -> None:
        """Try task again."""
        task = self.task
        if task:
            task.state = TaskState.QUEUED
            self.evt_requeue_task.emit(task)  # type: ignore[unused-ignore]

    def on_start_task(self) -> None:
        """Triggered when user clicked on the run task button."""
        if self.task:
            self.evt_start_task.emit(self.task)  # type: ignore[unused-ignore]
            self.started()

    def _update_state(self) -> None:
        """Update state."""
        if self.task:
            self.task_info.setText(self.task.pretty_info)
            self.task_state.setText(self.task.state.capitalize())
            hp.polish_widget(self.task_state)
            self.update_progress()
            logger.trace(f"Updating task '{self.task.summary()}'...")

    def started(self) -> None:
        """Start task."""
        self.poll_timer.start()
        hp.disable_widgets(self.pause_btn, disabled=self.can_pause)
        hp.disable_widgets(self.start_btn, disabled=True)
        self._update_state()

    def _on_pause_task(self) -> None:
        """Triggered when user clicked to pause task."""
        if self.task:
            self.pause_btn.paused = not self.pause_btn.paused
            self.evt_pause_task.emit(self.task, self.pause_btn.paused)  # type: ignore[unused-ignore]
        self._update_state()

    def paused(self, paused: bool) -> None:
        """The task was paused."""
        if self.task:
            self.pause_btn.paused = paused
            if self.pause_btn.paused:
                self.poll_timer.stop()
                logger.trace(f"Pausing task '{self.task.summary()}'...")
            else:
                self.poll_timer.start()
                logger.trace(f"Restarting task '{self.task.summary()}'...")
            self._update_state()

    def _on_cancel_task(self, force: bool = False) -> None:
        """Triggered when user clicked to pause the task."""
        if self.task:
            if force or hp.confirm(self, "Are you sure you wish to cancel this task?", "Cancel task?"):
                self.evt_cancel_task.emit(self.task)  # type: ignore[unused-ignore]
        self._update_state()

    def cancel(self) -> None:
        """Triggered when user clicked to cancel task."""
        self._on_cancel_task()

    def cancelled(self) -> None:
        """The task was canceled."""
        if self.task:
            try:
                self.poll_timer.stop()
            except RuntimeError:
                return
            hp.disable_widgets(self.start_btn, self.pause_btn, self.cancel_btn, disabled=True)
            hp.disable_widgets(self.retry_btn, disabled=False)
            duration = self.task.duration
            self.time_info.setText(format_interval(duration))
            logger.trace(f"Cancelled task '{self.task.summary()}'...")
        self._update_state()

    def next(self) -> None:
        """Update task."""
        self._update_state()

    def part_failed(self) -> None:
        """Update task."""
        self._update_state()

    def stop(self) -> None:
        """Stop task."""
        try:
            self.poll_timer.stop()
        except RuntimeError:
            return
        if self.task:
            self.time_info.setText(format_interval(self.task.duration))
        hp.disable_widgets(self.start_btn, self.pause_btn, self.cancel_btn, disabled=True)
        hp.disable_widgets(self.retry_btn, disabled=False)
        self._update_state()

    def close(self) -> bool:
        """Close method."""
        self.poll_timer.timeout.disconnect(self.on_update_timer)
        self.poll_timer.stop()
        return super().close()

    def on_update_timer(self) -> None:
        """Update stats about the process."""
        if self.task:
            self.time_info.setText(format_interval(self.task.current_duration))

    def mousePressEvent(self, event: ty.Any) -> None:
        """Mouse press event."""
        self.toggled = not self.toggled
        return QFrame.mousePressEvent(self, event)
