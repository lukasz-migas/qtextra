"""QtPopout example."""

from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_tutorial import Position, QtTutorial, TutorialStep


def create_popout():
    """Create a popout."""
    text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore
    et dolore magna aliqua. Vestibulum lorem sed risus ultricies tristique nulla aliquet. Malesuada nunc vel risus
     commodo viverra maecenas."""
    pop = QtTutorial(widget)
    pop.set_steps(
        [
            TutorialStep(
                title=f"{position}",
                message=text,
                widget=button,
                position=position,
            )
            for position in Position
        ]
    )
    pop.show()


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
