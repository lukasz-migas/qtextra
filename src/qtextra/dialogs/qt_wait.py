"""Wait dialog."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QVBoxLayout,
)

import qtextra.helpers as hp
from qtextra.widgets.qt_dialog import QtFramelessTool


class QtWaitPopup(QtFramelessTool):
    """Dialog to indicate to user that they need to wait."""

    def __init__(self, parent, msg: str = "Please wait..."):
        self.msg = msg
        super().__init__(parent)

    def make_panel(self) -> QVBoxLayout:
        """Make panel."""
        label = hp.make_label(self, self.msg)
        spinner, _ = hp.make_loading_gif(self, size=(64, 64))

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        return layout
