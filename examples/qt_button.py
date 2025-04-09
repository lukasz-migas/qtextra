"""QtActiveProgressBarButton."""

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_button import QtActivePushButton, QtRichTextButton

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

active_btn = QtActivePushButton(widget)
active_btn.setText("Click me to show activity")
active_btn.click()
layout.addWidget(active_btn)

rich_btn = QtRichTextButton(widget)
rich_btn.setText("<span style='color:#ff00ff;'>Colored text</span> <i>CAN BE IN ITALICS</i> <b>or bold</b>")
layout.addWidget(rich_btn)
widget.show()

app.exec_()
