"""QtTagEditor."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_tag_editor import QtTagEditor

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

layout.addWidget(QLabel("QtTagEditor"))
tag_editor = QtTagEditor()
tag_editor.add_tags(["alpha", "beta", "release"])
layout.addWidget(tag_editor)

layout.addWidget(QLabel("Scrollable QtTagEditor"))
scroll_editor = QtTagEditor(flow=False, placeholder="Type a tag and press Enter")
scroll_editor.add_tags(["project", "desktop", "qt", "widgets", "search", "tags"])
layout.addWidget(scroll_editor)

layout.addStretch()
widget.show()

app.exec_()
