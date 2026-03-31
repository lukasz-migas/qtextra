"""QtDictTagViewer."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_dict_tag_viewer import QtDictTagViewer

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

layout.addWidget(QLabel("QtDictTagViewer"))
viewer = QtDictTagViewer()
viewer.set_items(
    {
        "name": "qtextra",
        "retries": 3,
        "threshold": 0.75,
        "notes": None,
    },
)
viewer.search_edit.setText("th")
layout.addWidget(viewer)

layout.addWidget(QLabel("Read-only searchable table"))
secondary_viewer = QtDictTagViewer()
secondary_viewer.set_items(
    {
        "host": "localhost",
        "port": 5432,
        "timeout": 1.5,
        "cache": None,
    },
)
layout.addWidget(secondary_viewer)

layout.addStretch()
widget.show()

app.exec_()
