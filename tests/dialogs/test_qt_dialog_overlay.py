"""Tests for the floating settings card."""

from __future__ import annotations

import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from qtextra.dialogs.qt_dialog_overlay import QtOverlayWidget


def _make_page(n_rows: int) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    for index in range(n_rows):
        layout.addWidget(QLabel(f"Row {index}", page))
    return page


@pytest.fixture
def setup(qtbot):
    """Shown parent with an overlay holding a short and a tall page."""
    parent = QWidget()
    parent.resize(900, 700)
    qtbot.addWidget(parent)
    overlay = QtOverlayWidget(parent)
    short_tab, tall_tab, other_tab = QWidget(parent), QWidget(parent), QWidget(parent)
    overlay.add_page(short_tab, "Short", _make_page(1))
    overlay.add_page(tall_tab, "Tall", _make_page(12))
    parent.show()
    qtbot.waitExposed(parent)
    return parent, overlay, short_tab, tall_tab, other_tab


def test_overlay_hidden_until_page_is_available(setup):
    _parent, overlay, short_tab, _tall_tab, other_tab = setup
    assert not overlay.isVisible()
    assert overlay.is_open

    overlay.set_current(short_tab)
    assert overlay.isVisible()
    assert overlay.current_tab() is short_tab
    assert overlay.title_label.text() == "Short"

    overlay.set_current(short_tab, available=False)
    assert not overlay.isVisible()

    overlay.set_current(other_tab)
    assert not overlay.isVisible()


def test_overlay_pages(setup):
    _parent, overlay, short_tab, tall_tab, other_tab = setup
    assert overlay.has_page(short_tab)
    assert overlay.has_page(tall_tab)
    assert not overlay.has_page(other_tab)
    assert not overlay.has_page(None)

    overlay.set_current(tall_tab)
    assert overlay.current_tab() is tall_tab
    assert overlay.title_label.text() == "Tall"


def test_overlay_height_follows_current_page(setup):
    _parent, overlay, short_tab, tall_tab, _other_tab = setup
    overlay.set_current(tall_tab)
    tall_height = overlay.height()
    overlay.set_current(short_tab)
    assert overlay.height() < tall_height
    assert overlay.width() == overlay.WIDTH


def test_overlay_open_close(setup, qtbot):
    _parent, overlay, short_tab, _tall_tab, _other_tab = setup
    overlay.set_current(short_tab)

    with qtbot.waitSignal(overlay.evt_closed):
        assert overlay.close()
    assert not overlay.is_open
    assert not overlay.isVisible()

    # switching tabs keeps it closed
    overlay.set_current(short_tab)
    assert not overlay.isVisible()

    overlay.set_open(True)
    assert overlay.isVisible()


def test_overlay_minimize(setup):
    _parent, overlay, _short_tab, tall_tab, _other_tab = setup
    overlay.set_current(tall_tab)
    full_height = overlay.height()

    overlay.minimize_btn.click()
    assert overlay.is_minimized
    assert overlay.minimize_btn.isChecked()
    assert overlay.height() < full_height

    overlay.set_minimized(False)
    assert not overlay.is_minimized
    assert not overlay.minimize_btn.isChecked()
    assert overlay.height() == full_height


def test_overlay_default_position_until_moved(setup, qtbot):
    _parent, overlay, short_tab, tall_tab, _other_tab = setup
    overlay.set_default_position(lambda: QPoint(100, 50))
    overlay.set_current(short_tab)
    assert overlay.pos() == QPoint(100, 50)

    header = overlay.header.mapTo(overlay, QPoint(5, 5))
    target = header + QPoint(40, 30)
    qtbot.mousePress(overlay, Qt.MouseButton.LeftButton, pos=header)
    qtbot.mouseMove(overlay, target)
    qtbot.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=target)
    moved = overlay.pos()
    assert moved != QPoint(100, 50)

    # after a drag, refitting keeps the user's position
    overlay.set_current(tall_tab)
    assert overlay.pos() == moved


def test_overlay_right_drag_anywhere(setup, qtbot):
    _parent, overlay, _short_tab, tall_tab, _other_tab = setup
    overlay.set_default_position(lambda: QPoint(100, 50))
    overlay.set_current(tall_tab)

    body = overlay.body.mapTo(overlay, QPoint(10, 10))
    qtbot.mousePress(overlay, Qt.MouseButton.RightButton, pos=body)
    qtbot.mouseMove(overlay, body + QPoint(30, 20))
    qtbot.mouseRelease(overlay, Qt.MouseButton.RightButton, pos=body + QPoint(30, 20))
    assert overlay.pos() != QPoint(100, 50)


def test_overlay_left_click_on_body_does_not_drag(setup, qtbot):
    _parent, overlay, _short_tab, tall_tab, _other_tab = setup
    overlay.set_default_position(lambda: QPoint(100, 50))
    overlay.set_current(tall_tab)

    body = overlay.body.mapTo(overlay, QPoint(10, 10))
    qtbot.mousePress(overlay, Qt.MouseButton.LeftButton, pos=body)
    qtbot.mouseMove(overlay, body + QPoint(30, 20))
    qtbot.mouseRelease(overlay, Qt.MouseButton.LeftButton, pos=body + QPoint(30, 20))
    assert overlay.pos() == QPoint(100, 50)


def test_overlay_stays_inside_parent(setup, qtbot):
    parent, overlay, short_tab, _tall_tab, _other_tab = setup
    overlay.set_default_position(lambda: QPoint(10_000, 10_000))
    overlay.set_current(short_tab)
    assert overlay.x() == parent.width() - overlay.width()
    assert overlay.y() == parent.height() - overlay.height()

    parent.resize(700, 500)
    qtbot.waitUntil(lambda: overlay.x() == parent.width() - overlay.width())
    assert overlay.y() == parent.height() - overlay.height()


def test_overlay_make_section(setup):
    _parent, overlay, _short_tab, _tall_tab, _other_tab = setup
    section = overlay.make_section(overlay.stack, "Display")
    assert isinstance(section, QWidget)
