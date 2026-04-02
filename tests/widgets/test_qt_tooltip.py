from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QWidget

from qtextra.widgets.qt_tooltip import QtToolTip, QtToolTipView, TipPosition


def test_qt_tooltip_does_not_accept_focus(qtbot):
    host = QWidget()
    qtbot.addWidget(host)

    target = QLabel("target", host)

    view = QtToolTipView("Title", "Content", tail_position=TipPosition.BOTTOM, parent=host)
    tooltip = QtToolTip(view, target, parent=host)

    assert tooltip.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating) is True
    assert tooltip.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert bool(tooltip.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)
