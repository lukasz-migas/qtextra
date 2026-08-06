"""QtSideOverlay example."""

from __future__ import annotations

from pathlib import Path

from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication, QPushButton, QTextEdit, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_side_overlay import (
    QtSideOverlay,
    SideOverlayImage,
    SideOverlaySeparator,
    SideOverlaySubtitle,
    SideOverlayText,
    SideOverlayTitle,
)


def build_window() -> QWidget:
    """Build a host window with a button that opens a reader panel."""
    window = QWidget()
    window.setWindowTitle("QtSideOverlay Example")
    window.resize(760, 520)
    THEMES.apply(window)
    layout = QVBoxLayout(window)
    layout.addWidget(QTextEdit("The side overlay covers this content while it is open."))

    local_image = Path(__file__).resolve().parents[1] / "tests" / "_test_data" / "qtextra.png"
    overlay = QtSideOverlay(
        window,
        header_title="July 14",
        blocks=[
            SideOverlayTitle("Introducing Tabs"),
            SideOverlayText("Start a new session in a tab, or open an existing session from any project."),
            SideOverlayImage(local_image),
            SideOverlaySeparator(),
            SideOverlaySubtitle("Keep work organized"),
            SideOverlayText("Rename long-lived tabs so they are easier to find when you reopen the application."),
            SideOverlayImage("https://picsum.photos/seed/qtextra/640/320"),
        ],
    )
    button = QPushButton("Show release notes")
    button.clicked.connect(overlay.open)
    layout.addWidget(button)
    return window


app = QApplication([])
widget = build_window()
widget.show()
QTimer.singleShot(150, lambda: widget.findChild(QtSideOverlay).open())
app.exec_()
