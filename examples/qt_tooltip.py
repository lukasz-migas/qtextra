"""QtPopout example."""

from random import choice

from qtpy.QtCore import QSize
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.helpers import make_qta_icon
from qtextra.widgets.qt_tooltip import QtToolTip, TipPosition


def create_popout():
    """Create a popout."""
    tail_position = choice(list(TipPosition))
    QtToolTip.init(
        title=f"Displaying ToolTip with {tail_position}",
        content="Here you can add custom text that will be displayed below the title.",
        parent=widget,
        tail_position=tail_position,
        target=button,
        is_closable=choice([True, False]),
        image=make_qta_icon("home").pixmap(QSize(32, 32))
        if tail_position in [TipPosition.LEFT, TipPosition.RIGHT]
        else None,
    )


app = QApplication([])

widget = QWidget()
widget.setMinimumSize(600, 300)
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

layout.addWidget(button := QPushButton("Press me to see tooltip"))
button.clicked.connect(create_popout)
widget.show()

app.exec_()
