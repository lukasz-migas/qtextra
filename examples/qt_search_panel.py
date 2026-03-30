"""QtSearchPanel."""

from qtpy.QtWidgets import QApplication, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_search_panel import QtSearchPanel

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

editor = QPlainTextEdit()
editor.setPlainText(
    "QtSearchPanel is useful for common desktop workflows.\n"
    "Search, navigate, and replace text from a shared reusable panel.\n"
    "This example wires the panel to a text area in a minimal way.",
)

status = QLabel("Type into the search box to search the editor.")
search_panel = QtSearchPanel()
search_panel.set_target_editor(editor)
search_panel.evt_search_changed.connect(lambda text: status.setText(f"Searching for: {text or '<empty>'}"))

layout.addWidget(search_panel)
layout.addWidget(editor)
layout.addWidget(status)

widget.resize(720, 320)
widget.show()

app.exec_()
