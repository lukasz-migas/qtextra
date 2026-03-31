"""QtNotificationBadge."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFrame, QWidget

import qtextra.helpers as hp
from qtextra.config import THEMES

app = QApplication([])

widget = QWidget()
widget.setWindowTitle("QtNotificationBadge Example")
widget.setMinimumWidth(900)
THEMES.apply(widget)

layout = hp.make_grid_layout(parent=widget, spacing=18)
widget.setLayout(layout)

layout.addWidget(hp.make_label(widget, "Different widget types", bold=True), 0, 0, 1, 5)

button = hp.make_btn(widget, "Uploads")
button.setMinimumWidth(150)
layout.addWidget(hp.make_label(widget, "QtPushButton"), 1, 0)
layout.addWidget(button, 1, 1)
hp.make_notification_badge(
    parent=widget,
    widget=button,
    state="success",
    mode="count",
    size="md",
    count=3,
    auto_clear_on_click=True,
)

text_label = hp.make_label(widget, "Notifications", alignment=Qt.AlignmentFlag.AlignCenter)
text_label.setMinimumSize(150, 40)
text_label.setFrameShape(QFrame.Shape.Panel)
text_label.setFrameShadow(QFrame.Shadow.Sunken)
layout.addWidget(hp.make_label(widget, "QtClickLabel"), 2, 0)
layout.addWidget(text_label, 2, 1)
hp.make_notification_badge(parent=widget, widget=text_label, state="warning", mode="count", size="lg", count=12)

icon_label = hp.make_qta_label(widget, "info", large=True)
icon_label.setToolTip("Information icon")
layout.addWidget(hp.make_label(widget, "QtQtaLabel"), 3, 0)
layout.addWidget(icon_label, 3, 1)
hp.make_notification_badge(parent=widget, widget=icon_label, state="info", mode="dot", size="sm")

image_button = hp.make_qta_btn(widget, "warning", tooltip="Warnings", large=True)
layout.addWidget(hp.make_label(widget, "QtImagePushButton"), 4, 0)
layout.addWidget(image_button, 4, 1)
hp.make_notification_badge(
    parent=widget,
    widget=image_button,
    state="error",
    mode="count",
    size="md",
    count=12,
    auto_clear_on_click=True,
)

hint = hp.make_label(widget, "Click the button or image button to clear those badges")
layout.addWidget(hint, 5, 0, 1, 5)
layout.addWidget(hp.make_h_line(widget), 6, 0, 1, 5)

layout.addWidget(hp.make_label(widget, "Dot sizes", bold=True), 7, 0, 1, 5)

size_demo = hp.make_label(widget, "Sizes", alignment=Qt.AlignmentFlag.AlignCenter)
size_demo.setMinimumSize(140, 42)
layout.addWidget(size_demo, 8, 0)

for column, size in enumerate(("xs", "sm", "md", "lg", "xl"), start=1):
    anchor = hp.make_label(widget, size.upper(), alignment=Qt.AlignmentFlag.AlignCenter)
    anchor.setMinimumSize(60, 42)
    layout.addWidget(anchor, 8, column)
    hp.make_notification_badge(parent=widget, widget=anchor, state="error", mode="dot", size=size)

widget.show()
app.exec_()
