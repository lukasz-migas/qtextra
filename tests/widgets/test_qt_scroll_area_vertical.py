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
    qtbot.waitUntil(lambda: scroll._overlay_bar.isVisibleTo(scroll))
    assert scroll.verticalScrollBar().maximum() > 0
    # the scrollbar is drawn over the content, so the content fills the whole area
    assert scroll.viewport().width() == scroll.width()
    assert content.width() == scroll.width()

    scroll.setFixedHeight(content.minimumSizeHint().height())
    qtbot.waitUntil(lambda: not scroll._overlay_bar.isVisibleTo(scroll))
    assert content.height() == scroll.viewport().height()


def test_follows_content_layout_changes(qtbot) -> None:
    """Widening the content after construction should widen the area."""
    _, scroll, content = _make_area(qtbot, 300)
    content.layout().addWidget(QLabel("x" * 120, content))
    qtbot.waitUntil(lambda: scroll.minimumWidth() >= content.minimumSizeHint().width())
    assert scroll.minimumWidth() > 300


def test_splitter_pane_shrinks_back_with_content(qtbot) -> None:
    """A splitter pane widened by temporary content should not stay wider than the area's maximum."""
    from qtpy.QtWidgets import QSplitter

    content = QWidget()
    layout = QVBoxLayout(content)
    layout.addWidget(QLabel("short", content))
    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.addWidget(QLabel("left"))
    scroll = QtVerticalScrollArea(content, min_width=200, max_width=250)
    splitter.addWidget(scroll)
    qtbot.addWidget(splitter)
    splitter.resize(1000, 400)
    splitter.show()
    qtbot.waitExposed(splitter)

    wide = QLabel("x" * 90, content)
    layout.addWidget(wide)
    qtbot.waitUntil(lambda: splitter.sizes()[1] > 250)
    wide.deleteLater()
    qtbot.waitUntil(lambda: splitter.sizes()[1] <= 250)
    assert scroll.width() == splitter.sizes()[1]
