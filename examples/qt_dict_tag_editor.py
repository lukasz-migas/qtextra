"""QtDictTagEditor."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_dict_tag_editor import QtDictTagEditor

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout(widget)

layout.addWidget(QLabel("QtDictTagEditor"))
dict_editor = QtDictTagEditor()
dict_editor.set_items(
    {
        "name": "qtextra",
        "retries": 3,
        "threshold": 0.75,
        "notes": None,
    },
)
dict_editor.search_edit.setText("th")
layout.addWidget(dict_editor)

layout.addWidget(QLabel("Searchable table with typed values"))
secondary_editor = QtDictTagEditor()
secondary_editor.set_items(
    {
        "host": "localhost",
        "port": 5432,
        "timeout": 1.5,
        "cache": None,
    },
)
layout.addWidget(secondary_editor)

layout.addStretch()
widget.show()

app.exec_()
