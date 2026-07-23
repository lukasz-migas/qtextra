"""QtAttributeTagManager."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_button_attribute import QtAttributeTagManager

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)
widget.setMinimumWidth(460)
layout = QVBoxLayout(widget)

layout.addWidget(QLabel("Flow layout (with options)"))
flow_editor = QtAttributeTagManager(
    flow=True,
    key_options=["name", "version", "retries", "threshold", "notes", "license"],
)
flow_editor.set_items(
    {
        "name": "qtextra",
        "retries": 3,
        "threshold": 0.75,
        "notes": None,
    },
)
layout.addWidget(flow_editor)

layout.addWidget(QLabel("Flow layout (without options)"))
flow_editor = QtAttributeTagManager(
    flow=True,
)
flow_editor.set_items(
    {
        "name": "qtextra",
        "retries": 3,
        "threshold": 0.75,
        "notes": None,
    },
)
layout.addWidget(flow_editor)

layout.addWidget(QLabel("Horizontal scroll layout"))
scroll_editor = QtAttributeTagManager(flow=False)
scroll_editor.set_key_options(["host", "port", "timeout", "cache", "retries"])
scroll_editor.set_items(
    {
        "host": "localhost",
        "port": 5432,
        "timeout": 1.5,
        "cache": None,
    },
)
layout.addWidget(scroll_editor)

layout.addStretch()
widget.show()

app.exec_()
