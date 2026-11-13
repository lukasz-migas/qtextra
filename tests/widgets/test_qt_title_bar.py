"""Tests for the unified title bar."""

import pytest
from qtpy.QtCore import QPoint, Qt
from qtpy.QtWidgets import QPushButton, QVBoxLayout, QWidget

import qtextra.widgets.qt_title_bar as tb
from qtextra.widgets.qt_title_bar import QtTitleBar, enable_unified_title_bar, is_unified_title_bar


def _make_window(qtbot, unified: bool) -> tuple[QWidget, QtTitleBar]:
    window = QWidget()
    qtbot.addWidget(window)
    if unified:
        window.setWindowFlag(tb._EXPANDED_HINT, True)
    bar = QtTitleBar(window, height=40, button_inset=70, margin=5)
    layout = QVBoxLayout(window)
    layout.addWidget(bar)
    return window, bar


def test_supports_unified_title_bar_is_bool():
    assert isinstance(tb.supports_unified_title_bar(), bool)


def test_enable_unified_title_bar_unsupported(qtbot, monkeypatch):
    monkeypatch.setattr(tb, "supports_unified_title_bar", lambda: False)
    window = QWidget()
    qtbot.addWidget(window)
    flags = window.windowFlags()
    assert enable_unified_title_bar(window) is False
    assert window.windowFlags() == flags
    assert is_unified_title_bar(window) is False


@pytest.mark.skipif(tb._EXPANDED_HINT is None, reason="requires Qt >= 6.9")
def test_title_bar_inset_unified(qtbot):
    window, bar = _make_window(qtbot, unified=True)
    window.show()
    qtbot.waitExposed(window)
    assert bar.height() == 40
    assert bar.left_inset == 70
    assert bar._layout.contentsMargins().left() == 75


@pytest.mark.skipif(tb._RESPECTS_SAFE_AREA is None, reason="requires Qt >= 6.9")
def test_title_bar_ignores_safe_area_unified(qtbot):
    window, bar = _make_window(qtbot, unified=True)
    window.show()
    qtbot.waitExposed(window)
    assert not bar.testAttribute(tb._RESPECTS_SAFE_AREA)
    assert not window.testAttribute(tb._RESPECTS_SAFE_AREA)


def test_title_bar_inset_normal(qtbot):
    window, bar = _make_window(qtbot, unified=False)
    window.show()
    qtbot.waitExposed(window)
    assert bar.height() == 40
    assert bar.left_inset == 0
    assert bar._layout.contentsMargins().left() == 5


def test_title_bar_press_starts_move(qtbot, monkeypatch):
    window, bar = _make_window(qtbot, unified=False)
    button = bar.add_widget(QPushButton("btn", bar))
    bar.add_stretch()
    window.show()
    qtbot.waitExposed(window)

    calls = []
    handle = window.windowHandle()
    monkeypatch.setattr(handle, "startSystemMove", lambda: calls.append(1) or True)

    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert calls == []

    empty = QPoint(bar.width() - 5, bar.height() // 2)
    qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=empty)
    assert calls == [1]
