"""QtNotificationBadge."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_notification_badge import QtNotificationBadge

app = QApplication([])

widget = QWidget()
widget.setWindowTitle("QtNotificationBadge Example")
THEMES.apply(widget)

layout = QGridLayout()
layout.setSpacing(18)
widget.setLayout(layout)

examples = [
    ("Info dot", QPushButton("Inbox"), dict(state="info", mode="dot", size="sm")),
    (
        "Success count",
        QPushButton("Uploads"),
        dict(state="success", mode="count", size="md", count=3, auto_clear_on_click=True),
    ),
    (
        "Warning count",
        QPushButton("Tasks"),
        dict(state="warning", mode="count", size="lg", count=12, auto_clear_on_click=True),
    ),
    (
        "Error count",
        QPushButton("Alerts"),
        dict(state="error", mode="count", size="xl", count=128, auto_clear_on_click=True),
    ),
]

for row, (label, target, badge_kwargs) in enumerate(examples):
    target.setMinimumWidth(140)
    layout.addWidget(QLabel(label), row, 0)
    layout.addWidget(target, row, 1)
    QtNotificationBadge(parent=widget, widget=target, **badge_kwargs)

hint = QLabel("Click Uploads, Tasks, or Alerts to clear their badge")
layout.addWidget(hint, len(examples), 0, 1, 2)

size_demo = QLabel("Sizes")
size_demo.setAlignment(Qt.AlignmentFlag.AlignCenter)
size_demo.setMinimumSize(140, 42)
layout.addWidget(size_demo, len(examples) + 1, 1)
layout.addWidget(QLabel("Dot sizes"), len(examples) + 1, 0)

for column, size in enumerate(("xs", "sm", "md", "lg", "xl"), start=2):
    anchor = QLabel(size.upper())
    anchor.setAlignment(Qt.AlignmentFlag.AlignCenter)
    anchor.setMinimumSize(60, 42)
    layout.addWidget(anchor, len(examples) + 1, column)
    QtNotificationBadge(parent=widget, widget=anchor, state="error", mode="dot", size=size)

widget.show()
app.exec_()
