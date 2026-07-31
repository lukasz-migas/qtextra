"""Tests for the showcase carousel widget."""

from __future__ import annotations

from qtpy.QtCore import QPoint, Qt
from qtpy.QtGui import QPixmap

from qtextra.widgets.qt_showcase import QtShowcaseWidget, ShowcasePage


def _pages() -> list[ShowcasePage]:
    return [
        ShowcasePage(title="First", description="One", link_text="Learn", link_url="https://example.com/1"),
        ShowcasePage(title="Second", description="Two"),
        ShowcasePage(title="Third", description="Three"),
    ]


def test_showcase_navigation_wraps(qtbot) -> None:
    widget = QtShowcaseWidget(_pages())
    qtbot.addWidget(widget)

    assert widget.current_index == 0
    widget.previous_page()
    assert widget.current_index == 2
    widget.next_page()
    assert widget.current_index == 0
    assert widget._dots.count == 3
    assert widget._dots.current_index == 0


def test_showcase_dots_select_page(qtbot) -> None:
    widget = QtShowcaseWidget(_pages(), interval_ms=60_000)
    qtbot.addWidget(widget)
    widget.resize(500, 320)
    widget.show()

    second_dot = QPoint(widget._dots._first_center_x() + widget._dots._SPACING, widget._dots.height() // 2)
    qtbot.mouseClick(widget._dots, Qt.MouseButton.LeftButton, pos=second_dot)

    assert widget.current_index == 1
    assert widget._dots.current_index == 1
    assert widget._timer.isActive()


def test_showcase_replaces_pages_and_handles_empty_state(qtbot) -> None:
    widget = QtShowcaseWidget(_pages())
    qtbot.addWidget(widget)

    widget.set_pages([])
    assert widget.pages == ()
    assert widget.current_index == -1
    assert not widget._previous_btn.isVisible()
    assert not widget._next_btn.isVisible()
    assert widget._dots.count == 0
    assert widget._dots.isHidden()

    widget.set_pages([ShowcasePage(title="Only", image_path="/missing/image.png")])
    assert widget.current_index == 0
    assert widget._overlay.title_label.text() == "Only"
    assert widget._dots.count == 1
    assert widget._dots.isHidden()


def test_showcase_image_fits_without_cropping(qtbot) -> None:
    widget = QtShowcaseWidget()
    qtbot.addWidget(widget)
    widget._image.resize(200, 200)
    widget._image._pixmap = QPixmap(400, 100)

    image_rect = widget._image._scaled_image_rect()

    assert image_rect.size().width() == 200
    assert image_rect.size().height() == 50
    assert image_rect.center() == widget._image.rect().center()
    assert widget._image._CORNER_RADIUS == 10.0
    assert widget._previous_btn.width() == 40
    assert widget._next_btn.width() == 40


def test_showcase_emits_link(qtbot) -> None:
    widget = QtShowcaseWidget(_pages())
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.evt_link_activated) as blocker:
        widget._overlay.link_btn.click()
    assert blocker.args == ["https://example.com/1"]


def test_showcase_timer_tracks_visibility(qtbot) -> None:
    widget = QtShowcaseWidget(_pages(), interval_ms=25)
    qtbot.addWidget(widget)

    assert widget.interval_ms == 25
    assert not widget._timer.isActive()

    widget.show()
    qtbot.waitUntil(widget._timer.isActive)
    qtbot.waitUntil(lambda: widget.current_index != 0)

    widget.hide()
    assert not widget._timer.isActive()


def test_showcase_ignores_out_of_range_index(qtbot) -> None:
    widget = QtShowcaseWidget(_pages())
    qtbot.addWidget(widget)

    widget.set_current_index(99)
    assert widget.current_index == 0
