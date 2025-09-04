"""Message widget."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QVBoxLayout, QWidget

from qtextra import helpers as hp
from qtextra.widgets.qt_label import QtWelcomeLabel


class MessageWidget(QWidget):
    """Widget that displays a message at the center of the page."""

    def __init__(self, message: str, parent: QWidget | None = None, icon: str = ""):
        super().__init__(parent)

        self.icon = hp.make_qta_label(self, icon, hide=icon == "")
        self.label = hp.make_label(
            self,
            message,
            wrap=True,
            alignment=Qt.AlignmentFlag.AlignCenter,
            enable_url=True,
            object_name="overlay_label",
        )

        layout = QVBoxLayout(self)
        layout.addStretch(True)
        layout.addWidget(self.icon)
        layout.addWidget(self.label)
        layout.addStretch(True)

    @property
    def message(self) -> str:
        """Return current message."""
        return self.label.text()

    @message.setter
    def message(self, value: str) -> None:
        """Set message."""
        self.label.setText(value)
