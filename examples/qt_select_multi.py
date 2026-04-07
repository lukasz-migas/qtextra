"""Examples for the multi-select widgets."""

from qtpy.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_select_multi import QtMultiIconSelect, QtMultiSelect

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

layout.addWidget(QLabel("QtMultiSelect"))
text_select = QtMultiSelect(widget, allow_clear=True)
text_select.set_options(["option1", "option2", "option3"], ["option1", "option3"])
layout.addWidget(text_select)

layout.addWidget(QLabel("QtMultiIconSelect - single option"))
single_icon_select = QtMultiIconSelect(widget, allow_clear=True, allow_multiple=False, icon_size=(28, 28))
single_icon_select.set_options(
    [
        ("help", "Help"),
        ("warning", "Warning"),
        ("success", "Success"),
    ],
    ["warning"],
)
layout.addWidget(single_icon_select)

layout.addWidget(QLabel("QtMultiIconSelect - multiple options"))
multi_icon_select = QtMultiIconSelect(widget, allow_clear=True, allow_multiple=True, icon_size=(24, 24))
multi_icon_select.set_options(
    [
        ("visible_on", "Visible"),
        ("visible_off", "Hidden"),
        ("gear", "Settings"),
        ("info", "Info"),
    ],
    ["visible_on", "info"],
)
layout.addWidget(multi_icon_select)

layout.addStretch()
widget.show()

app.exec_()
