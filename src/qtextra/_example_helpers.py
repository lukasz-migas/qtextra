"""Helper functions for the UI."""

from qtpy.QtGui import QFont
from qtpy.QtWidgets import QFrame, QLabel


def section(title):
    """Helper function for the UI."""
    lbl = QLabel(title)

    f = QFont()
    f.setPixelSize(11)
    f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet("color: #aaa; letter-spacing: 1px;")
    return lbl


def divider():
    """Helper function for the UI."""
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: #eee;")
    return f
