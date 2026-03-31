"""Tests for dialog positioning helpers."""

from __future__ import annotations

from qtpy.QtCore import QPoint, QRect, QSize
from qtpy.QtWidgets import QApplication, QWidget

import qtextra.helpers as hp


class _FakeScreen:
    def __init__(self, rect: QRect) -> None:
        self._rect = rect

    def availableGeometry(self) -> QRect:
        return self._rect


class _Popup(QWidget):
    def __init__(self, size: QSize) -> None:
        super().__init__()
        self._size = size
        self.resize(size)

    def sizeHint(self) -> QSize:
        return self._size


def _mock_widget_screen(monkeypatch, screen_rect: QRect) -> None:
    monkeypatch.setattr(QWidget, "window", lambda self: None)
    monkeypatch.setattr(QApplication, "primaryScreen", lambda: _FakeScreen(screen_rect))


def _mock_mouse_screen(monkeypatch, cursor_pos: QPoint, screen_rect: QRect) -> None:
    monkeypatch.setattr(hp.QCursor, "pos", lambda *args, **kwargs: cursor_pos)
    monkeypatch.setattr(
        QApplication, "screenAt", lambda point: _FakeScreen(screen_rect) if point == cursor_pos else None
    )
    monkeypatch.setattr(QApplication, "primaryScreen", lambda: _FakeScreen(screen_rect))


def _global_rect(widget: QWidget) -> QRect:
    return QRect(widget.mapToGlobal(widget.rect().topLeft()), widget.rect().size())


def _assert_vertically_centered(popup: QWidget, anchor_rect: QRect) -> None:
    assert abs(popup.pos().y() + popup.height() / 2 - anchor_rect.center().y()) <= 1


def _assert_horizontally_centered(popup: QWidget, anchor_rect: QRect) -> None:
    assert abs(popup.pos().x() + popup.width() / 2 - anchor_rect.center().x()) <= 1


def test_show_right_of_widget_centers_and_stays_to_the_right(qtbot, monkeypatch):
    screen_rect = QRect(0, 0, 500, 300)
    _mock_widget_screen(monkeypatch, screen_rect)

    parent = QWidget()
    parent.setGeometry(100, 80, 80, 40)
    parent.show()
    qtbot.addWidget(parent)

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_right_of_widget(popup, parent, show=False)

    parent_rect = _global_rect(parent)
    assert popup.pos().x() == parent_rect.right() + 1
    _assert_vertically_centered(popup, parent_rect)


def test_show_right_of_widget_flips_left_when_right_side_would_overflow(qtbot, monkeypatch):
    screen_rect = QRect(0, 0, 300, 300)
    _mock_widget_screen(monkeypatch, screen_rect)

    parent = QWidget()
    parent.setGeometry(240, 80, 50, 40)
    parent.show()
    qtbot.addWidget(parent)

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_right_of_widget(popup, parent, show=False)

    parent_rect = _global_rect(parent)
    assert popup.pos().x() + popup.width() - 1 == parent_rect.left() - 1
    _assert_vertically_centered(popup, parent_rect)


def test_show_left_of_widget_centers_and_stays_to_the_left(qtbot, monkeypatch):
    screen_rect = QRect(0, 0, 500, 300)
    _mock_widget_screen(monkeypatch, screen_rect)

    parent = QWidget()
    parent.setGeometry(200, 80, 80, 40)
    parent.show()
    qtbot.addWidget(parent)

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_left_of_widget(popup, parent, show=False)

    parent_rect = _global_rect(parent)
    assert popup.pos().x() + popup.width() - 1 == parent_rect.left() - 1
    _assert_vertically_centered(popup, parent_rect)


def test_show_above_widget_flips_below_when_top_would_overflow(qtbot, monkeypatch):
    screen_rect = QRect(0, 0, 500, 300)
    _mock_widget_screen(monkeypatch, screen_rect)

    parent = QWidget()
    parent.setGeometry(200, 10, 80, 40)
    parent.show()
    qtbot.addWidget(parent)

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_above_widget(popup, parent, show=False)

    parent_rect = _global_rect(parent)
    assert popup.pos().y() == parent_rect.bottom() + 1
    _assert_horizontally_centered(popup, parent_rect)


def test_show_below_widget_flips_above_when_bottom_would_overflow(qtbot, monkeypatch):
    screen_rect = QRect(0, 0, 500, 200)
    _mock_widget_screen(monkeypatch, screen_rect)

    parent = QWidget()
    parent.setGeometry(200, 150, 80, 40)
    parent.show()
    qtbot.addWidget(parent)

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_below_widget(popup, parent, show=False)

    parent_rect = _global_rect(parent)
    assert popup.pos().y() + popup.height() - 1 == parent_rect.top() - 1
    _assert_horizontally_centered(popup, parent_rect)


def test_show_right_of_mouse_centers_on_cursor(qtbot, monkeypatch):
    _mock_mouse_screen(monkeypatch, QPoint(200, 150), QRect(0, 0, 500, 300))

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_right_of_mouse(popup, show=False)

    assert popup.pos() == QPoint(201, 120)


def test_show_left_of_mouse_flips_right_when_left_would_overflow(qtbot, monkeypatch):
    _mock_mouse_screen(monkeypatch, QPoint(20, 150), QRect(0, 0, 300, 300))

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_left_of_mouse(popup, show=False)

    assert popup.pos() == QPoint(21, 120)


def test_show_above_mouse_flips_below_when_top_would_overflow(qtbot, monkeypatch):
    _mock_mouse_screen(monkeypatch, QPoint(200, 20), QRect(0, 0, 500, 300))

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_above_mouse(popup, show=False)

    assert popup.pos() == QPoint(140, 21)


def test_show_below_mouse_flips_above_when_bottom_would_overflow(qtbot, monkeypatch):
    _mock_mouse_screen(monkeypatch, QPoint(200, 190), QRect(0, 0, 500, 200))

    popup = _Popup(QSize(120, 60))
    popup.show()
    qtbot.addWidget(popup)

    hp.show_below_mouse(popup, show=False)

    assert popup.pos() == QPoint(140, 130)
