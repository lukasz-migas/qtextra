"""QtPopout example."""

from random import choice

from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_popout import PopoutAnimationType, QtPopout


def create_popout():
    """Create a popout."""
    animation_type = choice(list(PopoutAnimationType))
    QtPopout.init(
        title=f"Displaying using {animation_type}",
        content="Here you can add custom text that will be displayed below the title.",
        parent=widget,
        animation_type=animation_type,
        target=button,
        is_closable=choice([True, False]),
    )


app = QApplication([])

widget = QWidget()
widget.setMinimumSize(600, 300)
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

layout.addWidget(button := QPushButton("Press me to see popout"))
button.clicked.connect(create_popout)
widget.show()

app.exec_()
