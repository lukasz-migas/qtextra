"""Tests for the vertical-only scroll area."""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from qtextra.widgets.qt_scroll_area_vertical import QtVerticalScrollArea


def _make_area(qtbot, height: int) -> tuple[QWidget, QtVerticalScrollArea, QWidget]:
    content = QWidget()
    layout = QVBoxLayout(content)
    wide = QWidget(content)
    wide.setMinimumSize(350, 400)
    layout.addWidget(wide)
    label = QLabel("A long wrapped label " * 20, content)
    label.setWordWrap(True)
    layout.addWidget(label)

    host = QWidget()
    host_layout = QVBoxLayout(host)
    scroll = QtVerticalScrollArea(content, host, min_width=300, max_width=300)
    host_layout.addWidget(scroll)
    host_layout.addStretch(1)
    qtbot.addWidget(host)
    host.resize(600, height)
    host.show()
    qtbot.waitExposed(host)
    return host, scroll, content


def test_never_clips_width(qtbot) -> None:
    """The area should grow to the content width and never scroll horizontally."""
    _, scroll, content = _make_area(qtbot, 300)
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    content_width = content.minimumSizeHint().width()
    assert content_width > 300
    assert scroll.viewport().width() >= content_width
    assert content.width() == scroll.viewport().width()


def test_scrolls_only_below_minimum_height(qtbot) -> None:
    """The vertical scrollbar should appear only when the content cannot shrink any further."""
    _, scroll, content = _make_area(qtbot, 300)
    qtbot.waitUntil(lambda: scroll.verticalScrollBar().isVisibleTo(scroll))
    assert scroll.verticalScrollBar().maximum() > 0
    # the scrollbar is added next to the content, not taken from it
    assert scroll.viewport().width() >= content.minimumSizeHint().width()

    scroll.setFixedHeight(content.minimumSizeHint().height())
    qtbot.waitUntil(lambda: not scroll.verticalScrollBar().isVisibleTo(scroll))
    assert content.height() == scroll.viewport().height()
