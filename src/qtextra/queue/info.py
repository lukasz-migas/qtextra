"""Info widget."""

from __future__ import annotations

import os
import typing as ty

from koyo.timer import MeasureTimer
from loguru import logger
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import create_worker, ensure_main_thread

import qtextra.helpers as hp
from qtextra.queue.task import Task
from qtextra.queue.utilities import format_command, format_interval, format_timestamp
from qtextra.typing import TaskState
from qtextra.utils.table_config import TableConfig
from qtextra.widgets.qt_dialog import QtDialog
from qtextra.widgets.qt_table_view_check import MultiColumnSingleValueProxyModel, QtCheckableTableView

logger = logger.bind(src="TaskInfo")

IS_DEV = os.environ.get("DEV_MODE", "0") == "1"

STATE_TO_ICON = {
    TaskState.QUEUED: "queue",
    TaskState.RUNNING: "run",
    TaskState.PAUSING: "pause",
    TaskState.PAUSED: "pause",
    TaskState.FINISHED: "finish",
    TaskState.LOCKED: "lock",
    TaskState.PART_FAILED: "warning",
    TaskState.FAILED: "error",
    TaskState.CANCELLING: "cross_full",
    TaskState.CANCELLED: "cross_full",
}
STATE_TO_COLOR = {
    TaskState.QUEUED: "#00C851",
    TaskState.RUNNING: "#8E24AA",
    TaskState.PAUSING: "#1DE9B6",
    TaskState.PAUSED: "#e91e63",
    TaskState.LOCKED: "#e0115f",
    TaskState.FINISHED: "#4285F4",
    TaskState.PART_FAILED: "#ff3d00",
    TaskState.FAILED: "#ff4444",
    TaskState.CANCELLING: "#546e7a",
    TaskState.CANCELLED: "#263238",
}

TABLE_CONFIG = (
    TableConfig()
    .add("", "check", "bool", 0, no_sort=True, hidden=True)
    .add("Index", "index", "int", 45, sizing="fixed")
    .add("Command", "command", "str", 150, sizing="stretch")
)
TABLE_CONFIG.text_alignment = "left"

TaskMetadata = tuple[Task, int, str, str, str, str, str, list[str]]


class TaskInfoDialog(QtDialog):
    """Task info."""

    HIDE_WHEN_CLOSE = False

    evt_update = Signal()

    def __init__(self, parent: ty.Optional[QWidget], task: Task) -> None:
        self.task = task
        super().__init__(parent)
        self.setMinimumWidth(600)
        self.setMinimumHeight(800)
        create_worker(
            self._on_get_task_choice_data,
            task,
            _start_thread=True,
            _connect={
                "returned": self._on_set_task_choice,
                "errored": self._on_set_task_choice_failed,
            },
        )

    def close(self) -> bool:
        """Close the window."""
        parent = self.parent()
        if parent and hasattr(parent, "dlg_info"):
            parent.dlg_info = None
        return super().close()

    def update_progress(self) -> None:
        """Update progress."""
        task = self.task
        self.stdout_edit.appendPlainText(task.current_std_out)
        if task.start_time:
            self.started_label.setText(format_timestamp(task.start_time))
            self.duration_label.setText(format_interval(task.current_duration))
        if task.end_time:
            self.finished_label.setText(format_timestamp(task.end_time))
        state = task.state.value.capitalize()
        if state != self.task_state.text():
            self.task_state.setText(state)
            hp.polish_widget(self.task_state)
        cmd_txt = self.command_label.text()
        if cmd_txt:
            _, total = cmd_txt.split("/")
            total = total.strip(" ")
            self.command_label.setText(f"{task.command_index + 1} / {total}")

    @staticmethod
    def _on_get_task_choice_data(task: Task) -> TaskMetadata:
        """Get task choice data."""
        with MeasureTimer() as timer:
            cmd_idx = -1
            state, start, end, dur, stdout, cmds = "", "", "", "", "", []
            if task:
                cmd_idx = task.command_index - 1
                state = task.state.value.capitalize()
                # add stdout
                stdout = task.stdout_data
                stdout = "\n".join(stdout)
                if len(stdout) > 500_000:
                    stdout = "<truncated>\n" + stdout[-500_000:]

                # add commands
                try:
                    for command in task.command_iter():
                        cmds.append(" ".join(command))
                except Exception as e:
                    logger.exception(f"Failed to retrieve commands: {e}")
                start = format_timestamp(task.start_time)  # type: ignore
                end = format_timestamp(task.end_time)  # type: ignore
                dur = format_interval(task.duration)
                cmd = f"{cmd_idx + 1} / {len(cmds)}" if cmds else "0 / 0"
        return task, cmd_idx, state, start, end, dur, cmd, stdout, cmds, timer()

    def _on_set_task_choice_failed(self, res: Exception) -> None:
        """Set task choice failed."""
        logger.exception(f"Failed to get task choice data: {res}")
        self.task_id.setText("<Failed to retrieve>")
        self.task_title.setText("<Failed to retrieve>")
        self.task_state.setText("<Failed to retrieve>")
        hp.polish_widget(self.task_state)
        self.started_label.setText("<Failed to retrieve>")
        self.finished_label.setText("<Failed to retrieve>")
        self.duration_label.setText("<Failed to retrieve>")
        self.command_label.setText("<Failed to retrieve>")
        self.stdout_edit.clear()
        self.stdout_edit.setPlainText("<Failed to retrieve>")
        self.stdout_edit.verticalScrollBar().setValue(self.stdout_edit.verticalScrollBar().maximum())
        self.command_table.reset_data()

    @ensure_main_thread
    def _on_set_task_choice(self, res: TaskMetadata) -> None:
        """Set task choice."""
        try:
            task, cmd_idx, state, start, end, dur, cmd, stdout, cmds, ret_time = res
            with MeasureTimer() as update_time:
                self.task_id.setText(task.task_id)
                self.task_title.setText(task.task_name)
                self.task_state.setText(state)
                hp.polish_widget(self.task_state)
                self.started_label.setText(start)
                self.finished_label.setText(end)
                self.duration_label.setText(dur)
                self.command_label.setText(cmd)
                self.stdout_edit.clear()
                self.stdout_edit.setPlainText(stdout or "No stdout/stderr available.")
                self.stdout_edit.verticalScrollBar().setValue(self.stdout_edit.verticalScrollBar().maximum())
                self.command_table.reset_data()
                table_data = []
                for index, cmd in enumerate(cmds):
                    table_data.append([False, index, cmd])
                self.command_table.add_data(table_data)
                self.command_table.resizeRowsToContents()
                self.command_table.resizeColumnsToContents()
            logger.trace(f"Update task '{task.task_name}' info took {update_time()}; retrieval: {ret_time}")
        except RuntimeError:
            pass

    def copy_selection_to_clipboard(self, res=None):
        """Copy items to clipboard."""
        sel_model = self.command_table.selectionModel()
        if sel_model.hasSelection():
            indices = sel_model.selectedRows()
            indices = [self.table_proxy.mapToSource(index) for index in indices]
            indices = [index.row() for index in indices]
            commands = [self.command_table.get_value(TABLE_CONFIG.command, index) for index in indices]
            hp.copy_text_to_clipboard(format_command(commands, IS_DEV))
            logger.trace(f"Copied {len(commands)} commands to clipboard.")

    def on_scroll_to_top(self) -> None:
        """Scroll to end."""
        self.stdout_edit.verticalScrollBar().setValue(self.stdout_edit.verticalScrollBar().minimum())

    def on_scroll_to_end(self) -> None:
        """Scroll to end."""
        self.stdout_edit.verticalScrollBar().setValue(self.stdout_edit.verticalScrollBar().maximum())

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Make panel."""
        self.task_title = hp.make_label(self, "")
        self.task_id = hp.make_label(self, "")
        self.task_state = hp.make_label(self, "", object_name="task_state")

        self.started_label = hp.make_label(self, "")
        self.finished_label = hp.make_label(self, "")
        self.duration_label = hp.make_label(self, "")
        self.command_label = hp.make_label(self, "")

        # commands view
        self.command_table = QtCheckableTableView(self, config=TABLE_CONFIG, enable_all_check=True, sortable=True)
        self.command_table.setWordWrap(True)
        self.command_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.command_table.setCornerButtonEnabled(False)
        self.command_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.command_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.command_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.command_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        hp.set_font(self.command_table, font_size=11)
        self.command_table.setup_model(
            TABLE_CONFIG.header, TABLE_CONFIG.no_sort_columns, TABLE_CONFIG.hidden_columns, text_alignment="left"
        )
        self.command_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.command_table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.command_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.table_proxy = MultiColumnSingleValueProxyModel(self)
        self.table_proxy.setSourceModel(self.command_table.model())
        self.command_table.model().table_proxy = self.table_proxy
        self.command_table.setModel(self.table_proxy)
        self.filter_by_command = hp.make_line_edit(
            self,
            placeholder="Search for...",
            func_changed=lambda text, col=TABLE_CONFIG.command: self.table_proxy.setFilterByColumn(text, col),
        )
        sel_model = self.command_table.selectionModel()
        sel_model.selectionChanged.connect(self.copy_selection_to_clipboard)

        command_tab = QWidget()
        command_layout = QVBoxLayout(command_tab)
        command_layout.setSpacing(2)
        command_layout.setContentsMargins(2, 2, 2, 2)
        command_layout.addWidget(self.command_table, stretch=True)
        command_layout.addWidget(hp.make_h_line(self))
        command_layout.addWidget(self.filter_by_command)

        # stdout
        self.stdout_edit = QPlainTextEdit()

        stdout_tab = QWidget()
        stdout_layout = QVBoxLayout(stdout_tab)
        stdout_layout.setSpacing(2)
        stdout_layout.setContentsMargins(2, 2, 2, 2)
        stdout_layout.addWidget(self.stdout_edit, stretch=True)
        stdout_layout.addWidget(hp.make_h_line(self))
        stdout_layout.addLayout(
            hp.make_h_layout(
                hp.make_btn(self, "Scroll to top", func=self.on_scroll_to_top),
                hp.make_btn(self, "Scroll to end", func=self.on_scroll_to_end),
                stretch_after=True,
            )
        )

        tabs = QTabWidget(self)
        tabs.addTab(stdout_tab, "Standard output (stdout/stderr)")
        tabs.addTab(command_tab, "Commands")

        layout = hp.make_form_layout()
        layout.addRow(hp.make_h_line_with_text("About task", bold=True))
        layout.addRow(hp.make_label(self, "Task title", bold=True), self.task_title)
        layout.addRow(hp.make_label(self, "Task id", bold=True), self.task_id)
        layout.addRow(hp.make_label(self, "Task state", bold=True), self.task_state)
        layout.addRow(hp.make_h_line_with_text("Statistics", bold=True))
        layout.addRow(hp.make_label(self, "Started on", bold=True), self.started_label)
        layout.addRow(hp.make_label(self, "Finished on", bold=True), self.finished_label)
        layout.addRow(hp.make_label(self, "Duration", bold=True), self.duration_label)
        layout.addRow(hp.make_label(self, "Command", bold=True), self.command_label)
        layout.addRow(tabs)

        main_layout = hp.make_v_layout()
        self.setWindowTitle(f"{self.task.task_name} :: {self.task.task_id}")
        layout2: QHBoxLayout = hp.make_h_layout()
        layout2.addLayout(layout, stretch=True)
        main_layout.addLayout(layout2)
        return main_layout
