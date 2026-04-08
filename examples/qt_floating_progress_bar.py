"""QtFloatingProgressBar example."""

from __future__ import annotations

from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QApplication, QDialog, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_floating_progress_bar import QtFloatingProgressBar


def build_window() -> QMainWindow:
    """Build a main-window example with a floating progress overlay."""
    window = QMainWindow()
    window.setWindowTitle("QtFloatingProgressBar Example")
    central = QWidget()
    window.setCentralWidget(central)
    layout = QVBoxLayout(central)

    editor = QTextEdit()
    editor.setPlaceholderText("Main window content")
    layout.addWidget(editor)

    overlay = QtFloatingProgressBar(
        parent=central,
        widget=editor,
        text="Preparing upload...",
        value=0,
    )

    value = {"step": 0}

    def advance() -> None:
        if value["step"] == 0:
            overlay.set_busy(True)
            overlay.set_text("Connecting to remote service...")
        elif value["step"] == 1:
            overlay.set_busy(False)
            overlay.set_range(0, 100)
            overlay.set_text("Uploading 25%")
            overlay.set_value(25)
        elif value["step"] == 2:
            overlay.set_text("Uploading 60%")
            overlay.set_value(60)
        else:
            overlay.set_text("Upload complete")
            overlay.set_value(100)
        value["step"] = min(value["step"] + 1, 3)

    btn = QPushButton("Advance progress")
    btn.clicked.connect(advance)
    layout.addWidget(btn)

    return window


def build_dialog() -> QDialog:
    """Build a dialog example with a top-level floating progress overlay."""
    dialog = QDialog()
    dialog.setWindowTitle("Progress Dialog")
    dialog.resize(420, 180)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QTextEdit("Dialog content stays interactive while progress floats above it."))

    overlay = QtFloatingProgressBar(widget=dialog, text="Downloading assets...", value=45)
    overlay.set_range(0, 100)
    overlay.show()

    timer = QTimer(dialog)
    timer.setInterval(1200)
    timer.timeout.connect(lambda: overlay.set_text("Still downloading..."))
    timer.start()

    return dialog


app = QApplication([])

main_window = build_window()
dialog = build_dialog()

THEMES.apply(main_window)
THEMES.apply(dialog)

main_window.resize(720, 360)
main_window.show()
dialog.show()

app.exec_()
