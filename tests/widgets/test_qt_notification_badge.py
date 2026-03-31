"""Tests for notification badge widget."""

import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel, QPushButton, QWidget

from qtextra.widgets.qt_notification_badge import QtNotificationBadge


@pytest.fixture
def badge_host(qtbot):
    """Create a host widget with a child target."""

    host = QWidget()
    host.resize(200, 120)
    target = QLabel("Target", parent=host)
    target.resize(120, 40)
    target.move(20, 20)
    qtbot.addWidget(host)
    host.show()
    return host, target


def test_notification_badge_attaches_and_shows_dot(badge_host, qtbot):
    host, target = badge_host
    badge = QtNotificationBadge(parent=host, widget=target, state="warning", mode="dot", size="lg")
    qtbot.addWidget(badge)

    assert badge.widget() is target
    assert badge.isVisible() is True
    assert badge.state == "warning"
    assert badge.mode == "dot"
    assert badge.sizeHint().width() == badge.sizeHint().height()


def test_notification_badge_count_mode_uses_text_and_caps_value(badge_host, qtbot):
    host, target = badge_host
    badge = QtNotificationBadge(parent=host, widget=target, state="error", mode="count", size="xl", count=120)
    qtbot.addWidget(badge)

    assert badge.count == 120
    assert badge._display_text == "99+"
    assert badge.sizeHint().width() >= badge.sizeHint().height()


def test_notification_badge_hides_zero_count_by_default(badge_host, qtbot):
    host, target = badge_host
    badge = QtNotificationBadge(parent=host, widget=target, mode="count", count=0)
    qtbot.addWidget(badge)

    assert badge.isVisible() is False

    badge.set_visible_when_zero(True)

    assert badge.isVisible() is True
    assert badge._display_text == "0"


def test_notification_badge_attach_to_sets_parent_window(qtbot):
    host = QWidget()
    host.resize(180, 100)
    target = QLabel("Target", parent=host)
    target.resize(100, 30)
    qtbot.addWidget(host)
    host.show()

    badge = QtNotificationBadge()
    qtbot.addWidget(badge)
    badge.attach_to(target)

    assert badge.parentWidget() is host
    assert badge.widget() is target


def test_notification_badge_rejects_invalid_values(qtbot):
    badge = QtNotificationBadge()
    qtbot.addWidget(badge)

    with pytest.raises(ValueError, match="Invalid state"):
        badge.set_state("critical")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Invalid mode"):
        badge.set_mode("pill")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Invalid size"):
        badge.set_badge_size("xxl")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match=">= 0"):
        badge.set_count(-1)


def test_notification_badge_can_be_cleared(badge_host, qtbot):
    host, target = badge_host
    badge = QtNotificationBadge(parent=host, widget=target, state="info", mode="dot")
    qtbot.addWidget(badge)

    badge.clear()

    assert badge.state == ""
    assert badge.isVisible() is False


def test_notification_badge_auto_clears_on_click(qtbot):
    host = QWidget()
    host.resize(200, 120)
    target = QPushButton("Target", parent=host)
    target.resize(120, 40)
    qtbot.addWidget(host)
    host.show()

    badge = QtNotificationBadge(parent=host, widget=target, state="warning", auto_clear_on_click=True)
    qtbot.addWidget(badge)

    qtbot.mouseClick(target, Qt.MouseButton.LeftButton)

    assert badge.state == ""
    assert badge.isVisible() is False
