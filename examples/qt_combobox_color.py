"""Color swatch combobox widget."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_combobox_color import QtColorSwatchComboBox

SWATCHES = [
    ("#0B84F3", "Blue"),
    ("#12B886", "Teal"),
    ("#FF922B", "Orange"),
    ("#FA5252", "Red"),
    ("#7C4DFF", "Violet"),
    ("#2B2D42", "Ink"),
]

app = QApplication([])

widget = QWidget()
widget.setMinimumWidth(420)
THEMES.apply(widget)

layout = QVBoxLayout(widget)
layout.addWidget(QLabel("QtColorSwatchComboBox"))

combo = QtColorSwatchComboBox(parent=widget)
combo.add_swatches(SWATCHES)
combo._on_select(combo._panel._cells[1]._color, "Teal")
layout.addWidget(combo)

layout.addStretch(1)
widget.show()

app.exec_()
