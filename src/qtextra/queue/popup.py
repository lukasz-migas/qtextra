"""Popup window for Queue module."""

from __future__ import annotations

from qtpy.QtWidgets import QFormLayout, QWidget

import qtextra.helpers as hp
from qtextra.queue.queue_widget import QUEUE, QueueList
from qtextra.widgets.qt_dialog import QtFramelessTool


class QueuePopup(QtFramelessTool):
    """Popup queue."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.setMinimumSize(700, 600)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QFormLayout:
        """Make panel."""
        self.queue_list = QueueList(self)
        self.queue_list.AUTO_EXPAND = True

        self.clear_btn = hp.make_btn(self, "Clear", func=self.queue_list.on_clear_queue, tooltip="Clear all tasks")
        self.n_tasks = hp.make_labelled_slider(
            self,
            minimum=1,
            maximum=max(QUEUE.n_parallel, 6),
            value=QUEUE.n_parallel,
            tooltip="Maximum number of tasks to run simultaneously.",
            func=QUEUE.set_max_parallel,
        )

        layout = hp.make_form_layout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addRow(self._make_hide_handle("Task queue")[1])
        layout.addRow("Number of parallel tasks", self.n_tasks)
        layout.addRow(self.clear_btn)
        layout.addRow(hp.make_h_line(self))
        layout.addRow(self.queue_list)
        return layout


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.config import THEMES
        from qtextra.queue.task import Task
        from qtextra.utils.dev import qapplication

        _ = qapplication()  # analysis:ignore
        dlg = QueuePopup(None)
        THEMES.set_theme_stylesheet(dlg)

        for i in range(3):
            task = Task(f"Task {i}", [["echo", "Task", f"{i}"], ["sleep", "3"], ["sleep", "3"], ["sleep", "3"]])
            QUEUE.add_task(task)

        dlg.show()
        sys.exit(dlg.exec_())

    _main()  # type: ignore[no-untyped-call]
