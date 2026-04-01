"""Multi-select combobox widget."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_combobox_multi import QtMultiSelectComboBox

app = QApplication([])

widget = QWidget()
widget.setMinimumWidth(520)
THEMES.apply(widget)

layout = QVBoxLayout(widget)
layout.addWidget(QLabel("QtMultiSelectComboBox"))

combo = QtMultiSelectComboBox(
    items=["UI", "Backend", "Docs", "Tests", "Release", "Design"],
    parent=widget,
)
combo.set_selected(["UI", "Docs", "Release"])
layout.addWidget(combo)

layout.addWidget(QLabel("Dense selection"))
combo_dense = QtMultiSelectComboBox(
    items=["Apple", "Apricot", "Banana", "Blueberry", "Cherry", "Grape", "Pear", "Strawberry"],
    parent=widget,
)
combo_dense.set_selected(["Apple", "Banana", "Cherry", "Pear"])
layout.addWidget(combo_dense)

layout.addStretch(1)
widget.show()

app.exec_()
