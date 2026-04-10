"""QtIconButtons."""

import typing as ty

from qtpy.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from qtextra.config import THEMES
from qtextra.typing import QtaSizePreset
from qtextra.widgets.qt_button_icon import (
    QtAndOrButton,
    QtAnimationPlayButton,
    QtBoolButton,
    QtExpandButton,
    QtFullscreenButton,
    QtHorizontalDirectionButton,
    QtImageButton,
    QtImagePushButton,
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

# Label sizing
layout.addWidget(QLabel("Buttons sizes"))
row_layout = QHBoxLayout()
layout.addLayout(row_layout)
for _index, preset in enumerate(ty.get_args(QtaSizePreset)):
    btn = QtImagePushButton()
    btn.set_qta("happy")
    btn.set_qta_size_preset(preset)
    row_layout.addWidget(btn)


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
    btn.clicked.connect(lambda *, btn=btn: print(f"{btn.__class__.__name__} clicked"))
    btn.setToolTip(btn.__class__.__name__)
    btn.set_qta_size_preset("large")
    row_layout.addWidget(btn)

# multi-state buttons can only swap between multiple states by selection from a list
layout.addWidget(QLabel("Multi-state buttons"))
row_layout = QHBoxLayout()
layout.addLayout(row_layout)
for klass in [QtStateButton, QtPriorityButton]:
    # crate an instance of the class, auto_connect will ensure that the icon changes upon clicking
    btn = klass(widget, auto_connect=True)
    btn.evt_changed.connect(lambda state, *, btn=btn: print(f"{btn.__class__.__name__} clicked {state}"))
    btn.setToolTip(btn.__class__.__name__)
    btn.set_qta_size_preset("large")
    row_layout.addWidget(btn)
row_layout.addStretch()

widget.show()
app.exec_()
