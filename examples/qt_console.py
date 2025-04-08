"""QtPopout example."""

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.dialogs.qt_console import QtConsole

app = QApplication([])

widget = QWidget()
widget.setMinimumSize(600, 300)
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)
layout.addWidget(QtConsole())

widget.show()

app.exec_()
