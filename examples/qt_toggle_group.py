"""QtActiveProgressBarButton."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_toggle_group import QtToggleGroup

app = QApplication([])

widget = QWidget()
widget.setMinimumHeight(400)
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

layout.addWidget(QLabel("QtToggleGroup - single option"))
layout.addWidget(QtToggleGroup(None, [str(i) for i in range(10)], exclusive=True))

layout.addWidget(QLabel("QtToggleGroup - multi option with flow layout"))
layout.addWidget(QtToggleGroup(None, [str(i) for i in range(10)], exclusive=False, orientation="flow"))

layout.addWidget(QLabel("QtToggleGroup - multi option"))
layout.addWidget(QtToggleGroup(None, [str(i) for i in range(10)], exclusive=False, value=["1", "5"]))

layout.addStretch()
widget.show()

app.exec_()
