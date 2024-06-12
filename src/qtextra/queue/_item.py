"""Task Widget."""

from __future__ import annotations

import typing as ty
from functools import partial

from loguru import logger
from qtpy.QtCore import Qt, QTimer, Signal  # type: ignore[attr-defined]
from qtpy.QtWidgets import QFrame, QGridLayout, QWidget

import qtextra.helpers as hp
from qtextra.helpers import hyper
from qtextra.queue.cli_queue import CLIQueueHandler
from qtextra.queue.task import Task
from qtextra.queue.utilities import format_interval, get_icon_state
from qtextra.typing import TaskState
from qtextra.widgets.qt_image_button import QtPauseButton

logger = logger.bind(src="TaskWidget")


QUEUE = CLIQueueHandler()


class TaskWidget(QFrame):
    """Widget controlling and displaying task information."""

    evt_start_task = Signal(Task)
    evt_requeue_task = Signal(Task)
    evt_cancel_task = Signal(Task)
    evt_pause_task = Signal(Task, bool)
    evt_remove_task = Signal(Task)
    evt_check_task = Signal(Task)
    evt_console = Signal(object)

    task: Task | None
    can_cancel: bool
    can_pause: bool
    can_cancel_when_started: bool
    can_force_start: bool

    # caches
    dlg_info = None

    def __init__(self, parent: QWidget | None = None, toggled: bool = True):
        super().__init__(parent)
        self.setFrameShape(QFrame.Box)  # type: ignore[attr-defined]
        self.setLineWidth(1)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(5000)
        self.poll_timer.timeout.connect(self.on_update_timer)  # type: ignore[attr-defined]

        self.task_name = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            enable_url=True,
        )
        self.lock_btn = hp.make_qta_btn(self, "unlocked", small=True, flat=True, func=self.on_open_lock_menu)
        self.notified_btn = hp.make_qta_btn(self, "check", small=True, flat=True, func=self.on_open_notify_menu)
        self.errors_btn = hp.make_qta_btn(self, "check", small=True, flat=True, func=self.on_open_config_menu)
        self.task_state = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignCenter,
            object_name="task_info",
        )
        self.task_state.setMaximumWidth(90)
        self.hide_btn = hp.make_qta_btn(
            self,
            "hide",
            tooltip="Hide task from the view.",
            small=True,
            flat=True,
            func=lambda x: self.setVisible(not self.isVisible()),
        )
        hp.set_retain_hidden_size_policy(self.hide_btn)

        self.task_info = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            enable_url=True,  # type: ignore[attr-defined]
        )
        self.progress_info = hp.make_label(self, "", alignment=Qt.AlignmentFlag.AlignCenter)

        self.options_btn = hp.make_qta_btn(
            self,
            "settings",
            tooltip="Show extra actions.",
            medium=True,
            func=self.on_open_menu,
        )
        self.reload_btn = hp.make_qta_btn(
            self,
            "reload",
            tooltip="Reload configuration file.",
            medium=True,
            func=self.on_reload_config,
        )
        self.info_btn = hp.make_qta_btn(
            self,
            "info",
            tooltip="Show information about the task.",
            medium=True,
            func=self.on_task_info,
        )
        self.start_btn = hp.make_qta_btn(
            self,
            "run",
            tooltip="Start task if the task has not started yet. This will override any built-in restrictions on number"
            " of simultaneous tasks and can cause your system to freeze.",
            medium=True,
            func=self.on_start_task,
        )

        self.retry_btn = hp.make_qta_btn(
            self, "retry", tooltip="Retry running task if the task has failed.", medium=True, func=self._on_retry_task
        )

        self.pause_btn = QtPauseButton(self)  # type: ignore
        self.pause_btn.set_medium()
        self.pause_btn.setToolTip("Pause running task.")
        self.pause_btn.clicked.connect(self._on_pause_task)  # type: ignore[unused-ignore]

        self.cancel_btn = hp.make_qta_btn(
            self,
            "cross_full",
            tooltip="Cancel task. If a task has started, this is not guaranteed to work!",
            medium=True,
            func=self._on_cancel_task,
        )
        self.task_id = hp.make_label(
            self,
            "",
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            object_name="task_id",  # type: ignore[attr-defined]
        )

        layout = QGridLayout(self)
        # widget, row, column, rowspan, colspan
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        # row 0
        layout.addWidget(self.task_name, 0, 0, 1, 3)
        layout.addWidget(self.progress_info, 0, 3, 1, 1)
        layout.addWidget(self.errors_btn, 0, 4, 1, 1)
        layout.addWidget(self.notified_btn, 0, 5, 1, 1)
        layout.addWidget(self.lock_btn, 0, 6, 1, 1)
        layout.addWidget(self.hide_btn, 0, 7, 1, 1)
        layout.addWidget(self.task_state, 0, 8, 1, 1)
        # row 1
        layout.addWidget(self.task_info, 1, 0, 1, 9)
        # row 2
        layout.addLayout(hp.make_h_layout(self.options_btn, self.reload_btn, stretch_after=True), 2, 0, 1, 3)
        layout.addLayout(
            hp.make_h_layout(
                self.info_btn, self.start_btn, self.retry_btn, self.pause_btn, self.cancel_btn, stretch_before=True
            ),
            2,
            5,
            1,
            4,
        )
        # row 3
        layout.addWidget(self.task_id, 3, 0, 1, 9)

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

    def on_open_menu(self) -> None:
        """Open folder menu."""
        # from autoims_run.templates.template import get_available_templates
        #
        # menu = hp.make_menu(self)
        # if self.task:
        #     hp.make_menu_item(
        #         self,
        #         "Open 'project' directory...",
        #         menu=menu,
        #         func=partial(self.open_folder, ""),
        #         disabled=not self.task.base_dir.exists(),
        #     )
        #     for directory in ["extras", "ims-processed", "ims-raw", "logs", "progress", "raw", "results"]:
        #         hp.make_menu_item(
        #             self,
        #             f"Open '{directory}' directory...",
        #             menu=menu,
        #             func=partial(self.open_folder, directory),
        #             disabled=not (self.task.base_dir / directory).exists(),
        #         )
        #
        #     menu.addSeparator()
        #
        #     new_notebook_menu = hp.make_menu(self, "Open new notebook")
        #     menu.addMenu(new_notebook_menu)
        #     for template in get_available_templates():
        #         hp.make_menu_item(
        #             self,
        #             f"Open '{template}' notebook",
        #             menu=new_notebook_menu,
        #             func=partial(self.on_copy_notebook_template, template),
        #         )
        #
        #     open_notebook_menu = hp.make_menu(self, "Open existing notebook")
        #     menu.addMenu(open_notebook_menu)
        #     for notebook in self.task.directory_wrapper.get_notebooks():
        #         hp.make_menu_item(
        #             self,
        #             f"Open '{notebook}' notebook",
        #             menu=open_notebook_menu,
        #             func=partial(self.on_open_notebook, notebook),
        #         )
        #
        #     menu.addSeparator()
        #     hp.make_menu_item(self, "Open in IPython console", menu=menu, func=self.on_open_console)
        #     menu.addSeparator()
        #     hp.make_menu_item(self, "Clear directory", menu=menu, func=self.on_clear_directory)
        #     hp.make_menu_item(self, "Remove from list", menu=menu, func=self.on_remove)
        #     hp.show_below_widget(menu, self.options_btn, y_offset=20, x_offset=40)

    def on_open_lock_menu(self) -> None:
        """Open lock menu."""
        menu = hp.make_menu(self)
        if self.task:
            hp.make_menu_item(self, "Mark as finished", menu=menu, func=self.on_mark_as_finished)
            hp.make_menu_item(self, "Mark as hidden", menu=menu, func=self.on_mark_as_hidden)
            menu.addSeparator()
            hp.make_menu_item(self, "Mark as locked", menu=menu, func=self.on_mark_as_locked)
            hp.show_below_widget(menu, self.lock_btn, y_offset=20, x_offset=40)

    def on_open_notify_menu(self) -> None:
        """Open notification menu."""
        menu = hp.make_menu(self)
        if self.task:
            hp.make_menu_item(self, "Show summary", menu=menu, func=self.on_show_summary)
            hp.make_menu_item(self, "Copy Slack message", menu=menu, func=self.on_copy_slack)
            hp.make_menu_item(self, "Send Slack message", menu=menu, func=self.on_send_slack)
            menu.addSeparator()
            hp.make_menu_item(self, "Mark as notified", menu=menu, func=self.on_mark_as_notified)
            hp.show_below_widget(menu, self.notified_btn, y_offset=20, x_offset=40)

    def on_open_config_menu(self) -> None:
        """Open config menu."""
        menu = hp.make_menu(self)
        if self.task:
            hp.make_menu_item(self, "Edit config in AutoIMS", menu=menu, func=self.on_open_config_in_autoims)
            hp.make_menu_item(self, "Merge configs...", menu=menu, func=self.on_merge_configs)
            menu.addSeparator()
            hp.make_menu_item(self, "Show config in viewer", menu=menu, func=self.on_open_config_in_viewer)
            hp.make_menu_item(
                self, "Edit config in VSCode (if available)", menu=menu, func=self.on_open_config_in_vscode
            )
            menu.addSeparator()
            hp.make_menu_item(self, "Show errors", menu=menu, func=self.on_open_errors_in_viewer)
            hp.make_menu_item(self, "Validate configs", menu=menu, func=self._update_warnings)
            hp.show_below_widget(menu, self.errors_btn, y_offset=20, x_offset=40)

    def open_folder(self, which: str) -> None:
        """Open directory."""
        from koyo.path import open_directory_alt

        if self.task:
            open_directory_alt(self.task.base_dir / which)

    def on_remove(self) -> None:
        """Remove task from list."""
        if self.task:
            if self.task.state == TaskState.RUNNING:
                hp.toast(self, "Cannot remove task.", "Cannot remove task while it is running.")
                return
            if hp.confirm_with_text(self, request="remove"):
                # cancel task
                self._on_cancel_task(force=True)
                self.evt_remove_task.emit(self.task)  # type: ignore[unused-ignore]

    def on_clear_directory(self) -> None:
        """Clear directory."""
        from autoims.utils.utilities import empty_dir

        if self.task:
            if self.task.state == TaskState.RUNNING:
                hp.toast(self, "Cannot remove task.", "Cannot remove task while it is running.")
                return
            if hp.confirm_with_text(self, request="clear-directory"):
                empty_dir(self.task.base_dir)
                self.task.reset()
                self.evt_requeue_task.emit(self.task)  # type: ignore[unused-ignore]

    def on_open_config_in_viewer(self) -> None:
        """Display configuration in a new window."""
        if self.task:
            from autoims_run.qt._viewer import QtTextDialog
            from autoims_run.utils.utilities import json_dumps

            # generate config
            config = json_dumps(self.task.config_parser.to_dict(), indent=4)
            dlg = QtTextDialog(self, "json", config, "JSON Configuration Viewer")
            dlg.show()

    def on_open_config_in_autoims(self) -> None:
        """Open Config app and edit the config."""
        if self.task:
            from autoims.qt.config import CONFIG
            from autoims.qt.window_config import ConfigWindow

            from qtextra.config import THEMES

            CONFIG.load()
            CONFIG.last_dir = self.task.base_dir

            dlg = ConfigWindow(None)  # type: ignore[arg-type]
            THEMES.set_theme_stylesheet(dlg)
            dlg.setMinimumWidth(1000)
            dlg.show()

    def on_merge_configs(self) -> None:
        """Merge the configs."""

    def on_open_config_in_vscode(self) -> None:
        """Open configuration in VSCode."""
        if self.task:
            from autoims_run.utils.utilities import open_in_vscode

            open_in_vscode(self.task.config_parser.path)

    def on_reload_config(self) -> None:
        """Reload configuration."""
        if self.task:
            QUEUE.remove(self.task)
            self.task.reload_config()
            self.set_task(self.task)
            self.evt_check_task.emit(self.task)  # type: ignore[unused-ignore]
            try:
                if self.dlg_info:
                    self.dlg_info.populate()
            except RuntimeError:
                self.dlg_info = None

    def on_open_console(self) -> None:
        """Open console."""
        if self.task:
            self.evt_console.emit({"task": self.task, "widget": self})  # type: ignore[unused-ignore]

    def on_copy_notebook_template(self, which: str) -> None:
        """Opem template."""
        from autoims_run.templates.template import copy_template
        from qtpy.QtGui import QDesktopServices

        if self.task:
            # copy from template
            file = copy_template(which, self.task.base_dir)

            # open in native app
            QDesktopServices.openUrl(file.as_uri())  # type: ignore[attr-defined]

    def on_open_notebook(self, which: str) -> None:
        """Open notebook."""
        from qtpy.QtGui import QDesktopServices

        if self.task:
            # copy from template
            file = self.task.directory_wrapper.extras_dir / "notebooks" / which

            # open in native app
            QDesktopServices.openUrl(file.as_uri())  # type: ignore[attr-defined]

    def on_show_summary(self) -> None:
        """Display configuration in a new window."""
        text = self.to_markdown_summary()
        if text:
            from autoims_run.qt._viewer import QtTextDialog

            # generate config
            dlg = QtTextDialog(self, "markdown", text, "Task Summary Viewer")
            dlg.show()

    def to_markdown_summary(self) -> str:
        """Return task summary."""
        if self.task:
            from autoims_run.utils._slack import craft_message

            return craft_message(self.task)
        return ""

    def on_copy_slack(self) -> None:
        """Copy slack message."""
        if self.task:
            from autoims_run.utils._slack import craft_message

            hp.copy_text_to_clipboard(craft_message(self.task))

    def on_send_slack(self) -> None:
        """Send email to user once task has finished."""
        if self.task:
            if not self.task.user:
                hp.toast(self, "No user found.", "No user found for this task.")
                return

            from autoims_run.utils._slack import send_slack
            from notifiers.exceptions import NotificationError

            if self.task.is_notified():
                if not hp.confirm(self, "The user has been previously notified. Are you sure you want to continue?"):
                    return
            if hp.confirm(self, "Send slack notification?", "Send slack notification?"):
                try:
                    send_slack(self.task)
                    self.task.notify()
                except NotificationError:
                    logger.warning("Failed to send slack notification.")
                    hp.toast(
                        self,
                        "Failed to send slack notification.",
                        f"Failed to send slack notification to <b>{self.task.user.name}</b>.",
                    )
                except ImportError:
                    logger.error("Failed to send notification because 'notifiers' is not installed!")
            self._update_state()

    def on_mark_as_finished(self) -> None:
        """Mark the task as finished."""
        if self.task and hp.confirm(self, "Mark task as finished?", "Mark task as finished?"):
            self.task.state = TaskState.FINISHED
            self.task.finish()
            self._update_state()

    def on_mark_as_locked(self) -> None:
        """Mark the task as finished."""
        if self.task and hp.confirm(self, "Mark task as blocked?", "Mark task as blocked?"):
            self.task.state = TaskState.LOCKED
            self.task.lock()
            self._update_state()

    def on_mark_as_hidden(self) -> None:
        """Mark the task as finished."""
        if self.task and hp.confirm(self, "Mark task as hidden?", "Mark task as hidden?"):
            self.task.state = TaskState.FINISHED
            self.task.hide()
            self._update_state()

    def on_mark_as_notified(self) -> None:
        """Mark the task as finished."""
        if self.task and hp.confirm(self, "Mark task as notified?", "Mark task as notified?"):
            self.task.notify()
            self._update_state()

    # noinspection PyBroadException
    def on_send_email(self) -> None:
        """Send email to user once task has finished."""
        if self.task and self.task.user:
            from autoims_run.utils._email import write_email

            if hp.confirm(self, "Send email notification?", "Send email notification?"):
                try:
                    write_email(self.task)
                except ConnectionRefusedError:
                    logger.warning("Failed to send notification.")
                except Exception:
                    logger.warning("Failed to send email notification.")
                    hp.toast(
                        self,
                        "Failed to send email notification.",
                        f"Failed to send email notification to <b>{self.task.user.name}</b>.",
                    )
            self._update_state()

    def mousePressEvent(self, event: ty.Any) -> None:
        """Mouse press event."""
        self.toggled = not self.toggled
        return QFrame.mousePressEvent(self, event)

    def toggle_visibility(self) -> None:
        """Hide certain widgets."""
        hp.hide_widgets(
            self.task_info,
            self.options_btn,
            self.start_btn,
            self.retry_btn,
            self.pause_btn,
            self.cancel_btn,
            self.info_btn,
            self.reload_btn,
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
        self.task = task
        self.can_cancel = can_cancel
        self.can_cancel_when_started = can_cancel_when_started
        self.can_pause = can_pause
        self.can_force_start = can_force_start

        # update ui
        self.task_name.setText(hyper(task.base_dir, task.pretty_name))
        self.task_name.setToolTip(str(task.base_dir))
        self.task_info.setText(task.pretty_info)
        self.task_id.setText(task.task_id)
        if task.state == TaskState.FINISHED:
            self.stop()
        else:
            hp.disable_widgets(self.start_btn, self.cancel_btn, disabled=False)
        self._update_state()
        self._update_warnings()
        self.toggled = not auto_expand
        logger.trace(f"Added task '{self.task.summary()}'")

    def _update_warnings(self) -> None:
        """Generate warnings for task."""
        errors: list[str] = []
        if self.task:
            errors = self.task.config_errors()
        tooltip = "<br>".join(errors)
        state, color = get_icon_state(errors)
        self.errors_btn.setIcon(hp.make_qta_icon(state, color=color))  # type: ignore[no-untyped-call]
        self.errors_btn.setToolTip(tooltip)

    def on_open_errors_in_viewer(self) -> None:
        """Open errors in viewer."""
        from autoims.qt._info import InfoDialog

        errors: list[str] = []
        if self.task:
            errors = self.task.config_errors()
        if errors:
            message = "<br>".join(errors)

            dlg = InfoDialog(self, message, "Errors", min_width=600, min_height=300)
            dlg.show_right_of_mouse()

    def update_progress(self) -> None:
        """Update progress."""
        try:
            if self.dlg_info:
                self.dlg_info.update_progress()
        except RuntimeError:
            self.dlg_info = None

    def on_update_timer(self) -> None:
        """Update stats about the process."""
        if self.task:
            task = self.task.current_task
            if task:
                self.progress_info.setText(format_interval(task.stats.current_duration))

    def on_task_info(self) -> None:
        """Show widget with information about the task."""
        if self.task:
            from autoims_run.qt.info_widget import TaskInfoDialog

            try:
                if self.dlg_info is None:
                    self.dlg_info = TaskInfoDialog(self, self.task)
                    self.dlg_info.evt_update.connect(self.on_update_timer)
                self.dlg_info.show()
            except RuntimeError:
                self.dlg_info = None
                self.on_task_info()

    def on_start_task(self) -> None:
        """Triggered when user clicked on the run task button."""
        if self.task:
            self.evt_start_task.emit(self.task)  # type: ignore[unused-ignore]
            self.started()

    def _on_retry_task(self) -> None:
        """Try task again."""
        task = self.task
        if task:
            task.state = TaskState.QUEUED
            for task_ in task.tasks:
                if task_.state != TaskState.FINISHED:
                    task_.reset()
            task.unfinish()
            self.evt_requeue_task.emit(task)  # type: ignore[unused-ignore]

    def _update_state(self) -> None:
        """Update state."""
        if self.task:
            self.task_info.setText(self.task.pretty_info)
            self.task_state.setText(self.task.state.capitalize())
            hp.polish_widget(self.task_state)
            self.lock_btn.set_qta("locked" if self.task.is_finished() else "unlocked")
            self.notified_btn.set_qta("notified" if self.task.is_notified() else "not_notified")
            hp.hide_widgets(self.hide_btn, hidden=not self.task.is_finished())
            try:
                self.dlg_info.on_task_choice()  # type: ignore[union-attr]
            except (AttributeError, RuntimeError, Exception):
                self.dlg_info = None

    def started(self) -> None:
        """Start task."""
        self.poll_timer.start()
        hp.disable_widgets(self.pause_btn, disabled=self.can_pause)
        hp.disable_widgets(self.start_btn, self.reload_btn, disabled=True)
        self._update_state()

    def _on_pause_task(self) -> None:
        """Triggered when user clicked to pause task."""
        if self.task:
            self.pause_btn.paused = not self.pause_btn.paused
            self.evt_pause_task.emit(self.task, self.pause_btn.paused)  # type: ignore[unused-ignore]
        self._update_state()

    def paused(self, paused: bool) -> None:
        """Task was paused."""
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
        """Triggered when user clicked to pause task."""
        if self.task:
            if force or hp.confirm(self, "Are you sure you wish to cancel this task?", "Cancel task?"):
                self.evt_cancel_task.emit(self.task)  # type: ignore[unused-ignore]
        self._update_state()

    def cancel(self) -> None:
        """Triggered when user clicked to cancel task."""
        self._on_cancel_task()

    def cancelled(self) -> None:
        """Task was cancelled."""
        if self.task:
            try:
                self.poll_timer.stop()
            except RuntimeError:
                return
            hp.disable_widgets(self.start_btn, self.pause_btn, self.cancel_btn, disabled=True)
            hp.disable_widgets(self.retry_btn, self.reload_btn, disabled=False)
            duration = self.task.stats.duration
            self.progress_info.setText(format_interval(duration))
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
            self.progress_info.setText(format_interval(self.task.duration))
        hp.disable_widgets(self.start_btn, self.pause_btn, self.cancel_btn, disabled=True)
        hp.disable_widgets(self.retry_btn, self.reload_btn, disabled=False)
        self._update_state()

    def close(self) -> bool:
        """Close method."""
        self.poll_timer.timeout.disconnect(self.on_update_timer)
        self.poll_timer.stop()
        return super().close()
