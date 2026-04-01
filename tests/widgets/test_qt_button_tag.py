"""Tests for tag button widgets."""

from __future__ import annotations

from qtextra.widgets.qt_button_tag import QtTagManager
from qtextra.widgets.qt_layout_scroll import QtScrollableHLayoutWidget


def test_qt_tag_manager_scroll_layout_fits_tag_height(qtbot):
    widget = QtTagManager(allow_action=True, flow=False)
    qtbot.addWidget(widget)

    for index in range(10):
        widget.add_tag(f"Option {index}", active=index == 1, allow_action=index % 2 == 0)
    widget.add_filter()
    widget.add_plus()

    widget.resize(520, 120)
    widget.show()
    qtbot.waitExposed(widget)

    scroll_layout = widget._layout
    assert isinstance(scroll_layout, QtScrollableHLayoutWidget)

    assert widget.widgets
    assert scroll_layout.widget().sizeHint().height() <= scroll_layout.viewport().height()
    assert scroll_layout.verticalScrollBar().maximum() == 0
