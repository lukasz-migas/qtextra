"""QtActiveProgressBarButton."""

from qtpy.QtWidgets import QApplication, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_button_progress import QtActiveProgressBarButton

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

active_btn = QtActiveProgressBarButton(widget, "Click me")
active_btn.setRange(0, 100)
active_btn.setValue(10)
active_btn.active = True
layout.addWidget(active_btn)


def activate():
    active_btn.active = not active_btn.active
    print(f"Active: {active_btn.active}")


def cancel():
    active_btn.active = False
    print("Cancelled")


active_btn = QtActiveProgressBarButton(widget, "Click me", which="dots")
active_btn.setRange(0, 100)
active_btn.setValue(10)
active_btn.evt_clicked.connect(activate)
active_btn.evt_cancel.connect(cancel)
layout.addWidget(active_btn)
widget.show()

app.exec_()
