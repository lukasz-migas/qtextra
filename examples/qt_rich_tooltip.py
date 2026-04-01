"""QtRichToolTip example."""

from qtpy.QtCore import QSize
from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.helpers import make_qta_icon
from qtextra.widgets.qt_rich_tooltip import QtRichToolTip, RichToolTipAction


def show_tooltip() -> None:
    QtRichToolTip.show_tooltip(
        title="Quick Actions",
        content=(
            "This tooltip supports <b>rich HTML</b>, <code>inline code</code>, "
            'and <a href="https://github.com/lgmigas/qtextra">links</a>.'
        ),
        image=make_qta_icon("help").pixmap(QSize(64, 64)),
        icon="help",
        shortcut="Ctrl+K",
        actions=[
            RichToolTipAction("Primary Action", callback=lambda: status.setText("Primary action clicked")),
            RichToolTipAction("Dismiss", callback=lambda: status.setText("Tooltip dismissed")),
        ],
        target=button,
        parent=widget,
        duration=-1,
    )


app = QApplication([])

widget = QWidget()
widget.setMinimumSize(640, 320)
THEMES.apply(widget)

layout = QVBoxLayout(widget)
layout.addStretch()
layout.addWidget(button := QPushButton("Show rich tooltip"))
layout.addWidget(status := QLabel("Click the button to show the tooltip."))
layout.addStretch()

button.clicked.connect(show_tooltip)

widget.show()
show_tooltip()

app.exec_()
