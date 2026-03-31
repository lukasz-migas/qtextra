"""QtOverlay example."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_overlay import QtOverlayDismissMessage, QtOverlayLabel

app = QApplication([])

widget = QWidget()
widget.setWindowTitle("QtOverlay Example")
widget.resize(560, 320)
THEMES.apply(widget)

layout = QVBoxLayout(widget)
editor = QTextEdit()
editor.setPlaceholderText("Type here once the document is ready...")
layout.addWidget(editor)

QtOverlayLabel(
    parent=widget,
    widget=editor,
    text="Autosave is enabled",
    alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
)

overlay = QtOverlayDismissMessage(
    parent=widget,
    widget=editor,
    icon_name="info",
    text="This editor is loading remote content. You can inspect the text, but editing stays disabled until sync completes.",
    word_wrap=True,
    dismiss_btn=True,
    ok_btn=True,
    ok_text="Understood",
)
overlay.display()

widget.show()
app.exec_()
