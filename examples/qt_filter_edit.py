"""QtActiveProgressBarButton."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_filter_edit import QtFilterEdit

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

layout.addWidget(QLabel("QtFilterEdit"))
layout.addWidget(filter_edit := QtFilterEdit())
[filter_edit.add_filter(f"Filter {i}") for i in range(5)]

layout.addWidget(QLabel("QtFilterEdit with options above the text edit"))
layout.addWidget(filter_edit := QtFilterEdit(above=True))
[filter_edit.add_filter(f"Filter {i}") for i in range(5)]

layout.addWidget(QLabel("QtFilterEdit with flow layout"))
layout.addWidget(filter_edit := QtFilterEdit(flow=True))
[filter_edit.add_filter(f"Filter {i}") for i in range(10)]

layout.addWidget(QLabel("QtFilterEdit with AND / OR switch"))
layout.addWidget(filter_edit := QtFilterEdit(enable_switch=True))
[filter_edit.add_filter(f"Filter {i}") for i in range(5)]
layout.addStretch()
widget.show()

app.exec_()
