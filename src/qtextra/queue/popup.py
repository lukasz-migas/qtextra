"""Popup window for Queue module."""

from __future__ import annotations

from qtpy.QtWidgets import QVBoxLayout, QWidget

from qtextra.queue.queue_widget import QueueList
from qtextra.widgets.qt_dialog import QtFramelessTool


class QueuePopup(QtFramelessTool):
    """Popup queue."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.queue_list = None
        self.setMinimumSize(600, 600)

    # noinspection PyAttributeOutsideInit
    def make_panel(self) -> QVBoxLayout:
        """Make panel."""
        self.queue_list = QueueList(self)
        # self.queue_list.evt_console.connect(self.on_show_console)  # type: ignore[unused-ignore]

        layout = QVBoxLayout()
        layout.setSpacing(1)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(self._make_hide_handle("Task queue")[1])
        layout.addWidget(self.queue_list, stretch=True)
        return layout


if __name__ == "__main__":  # pragma: no cover

    def _main():  # type: ignore[no-untyped-def]
        import sys

        from qtextra.config import THEMES
        from qtextra.queue.queue_widget import QUEUE
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
