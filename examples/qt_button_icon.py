"""QtIconButtons."""

from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.widgets.qt_button_icon import (
    QtAndOrButton,
    QtAnimationPlayButton,
    QtBoolButton,
    QtExpandButton,
    QtFullscreenButton,
    QtHorizontalDirectionButton,
    QtImageButton,
    QtLockButton,
    QtMinimizeButton,
    QtPauseButton,
    QtPinButton,
    QtPriorityButton,
    QtSortButton,
    QtStateButton,
    QtThemeButton,
    QtToggleButton,
    QtVerticalDirectionButton,
    QtVisibleButton,
)

app = QApplication([])

widget = QWidget()
THEMES.apply(widget)

layout = QVBoxLayout()
widget.setLayout(layout)

# single-state buttons can only swap between two states
layout.addWidget(QLabel("Single-state buttons"))
row_layout = QHBoxLayout()
layout.addLayout(row_layout)
for klass in [
    QtAnimationPlayButton,
    QtPauseButton,
    QtBoolButton,
    QtAndOrButton,
    QtExpandButton,
    QtSortButton,
    QtHorizontalDirectionButton,
    QtVerticalDirectionButton,
    QtMinimizeButton,
    QtFullscreenButton,
    QtPinButton,
    QtVisibleButton,
    QtLockButton,
    QtToggleButton,
    QtThemeButton,
    QtImageButton,
]:
    # crate an instance of the class, auto_connect will ensure that the icon changes upon clicking
    btn = klass(widget, auto_connect=True)
    btn.clicked.connect(lambda: print(f"{btn.__class__.__name__} clicked"))
    btn.setToolTip(btn.__class__.__name__)
    btn.set_large()
    row_layout.addWidget(btn)

# multi-state buttons can only swap between multiple states by selection from a list
layout.addWidget(QLabel("Multi-state buttons"))
row_layout = QHBoxLayout()
layout.addLayout(row_layout)
for klass in [QtStateButton, QtPriorityButton]:
    # crate an instance of the class, auto_connect will ensure that the icon changes upon clicking
    btn = klass(widget, auto_connect=True)
    btn.evt_changed.connect(lambda state: print(f"{btn.__class__.__name__} clicked {state}"))
    btn.setToolTip(btn.__class__.__name__)
    btn.set_large()
    row_layout.addWidget(btn)
row_layout.addStretch()

widget.show()
app.exec_()
